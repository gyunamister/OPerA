import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import sleep
from typing import Dict, Any, List, Union, Tuple, Callable
import sys

import numpy
from random import randint

import sim.enums
import sim.case
import sim.model_configuration
from sim import time_utils, utils, sim_graph as sgraph, model_parameters as params, event_system as ev_sys, \
    sim_model as smodel, managers as smanagers, sim_data as sdata, parameter_implementations as pimpls, \
    model_configuration as mconfig
from sim.enums import AvailableLifecycles, ExecutionParameters

from ocpa.objects.log.exporter.ocel import factory as export_factory


def default_execution_parameters():
    execution_parameters = {ExecutionParameters.CasesToGenerate: 1000,
                            ExecutionParameters.GenerationCutoffDate: None,
                            ExecutionParameters.SimStartDate: None,
                            ExecutionParameters.SimCutoffDate: None,
                            ExecutionParameters.RealtimeLimit: timedelta(seconds=30)}
    return execution_parameters


class SimulationContext:

    def __init__(self):
        self._total_started_cases = 0
        self._total_completed_cases = 0

    def register_case_creation(self, case=None):
        self._total_started_cases += 1

    def register_case_completion(self, case=None):
        self._total_completed_cases += 1

    def get_case_number(self) -> int:
        return self.total_started_cases

    @property
    def total_started_cases(self) -> int:
        return self._total_started_cases

    @property
    def total_completed_cases(self) -> int:
        return self._total_completed_cases


class OCSimulationContext:

    def __init__(self, object_config):
        self.object_config = object_config
        self._total_started_cases = 0
        self._total_completed_cases = 0
        self._total_objects = {k: 0 for k in self.object_config.specs.keys()}

    def register_case_creation(self, case=None):
        self._total_started_cases += 1

    def register_case_completion(self, case=None):
        self._total_completed_cases += 1

    def get_case_number(self) -> int:
        return self.total_started_cases

    def create_objects(self) -> List[sim.case.OCObject]:
        obj_list = []
        for k in self.object_config.specs.keys():
            lower = self.object_config.specs[k][0]
            upper = self.object_config.specs[k][1]
            temp_obj_list = []
            num_obj = randint(lower, upper)
            for i in range(0, num_obj):
                obj = sim.case.OCObject(k, k+str(self._total_objects[k]))
                temp_obj_list.append(obj)
                self._total_objects[k] += 1
            obj_list += temp_obj_list
        return obj_list

    @property
    def total_started_cases(self) -> int:
        return self._total_started_cases

    @property
    def total_completed_cases(self) -> int:
        return self._total_completed_cases

    @property
    def ongoing_cases(self) -> int:
        return self._ongoing_cases


@dataclass
class Schedulables:
    arrival_model: smodel.ArrivalModel
    activity_datas: Dict[str, sdata.OCActivityData]
    resource_datas: Dict[str, sdata.ResourceData]


class SchedulingManager:

    def __init__(self, event_queue: ev_sys.EventQueue, schedulables: Schedulables,
                 simulation_context: SimulationContext,
                 execution_parameters: Dict[ExecutionParameters, Any]) -> None:
        self.event_queue = event_queue
        self.arrival_model = schedulables.arrival_model
        self.arrival_processes: Dict[str, Tuple[mconfig.ArrivalProcessConfig,
                                                ev_sys.ArrivalProcessScheduler]] = {}
        self.activity_datas: Dict[str,
                                  sdata.OCActivityData] = schedulables.activity_datas
        self.resource_datas: Dict[str,
                                  sdata.ResourceData] = schedulables.resource_datas
        self.simulation_context = simulation_context
        self.execution_parameters = execution_parameters

        self._client_scheduler_map: Dict[ev_sys.Updatable,
                                         ev_sys.BusinessHoursScheduler] = {}
        self._bh_schedulers: Dict[params.BusinessHours,
                                  ev_sys.BusinessHoursScheduler] = {}
        self._unstarted_schedulers: List[Tuple[int,
                                               ev_sys.BusinessHoursScheduler]] = []

    def _schedule_business_hours(self, client: ev_sys.Updatable,
                                 business_hours: params.BusinessHours = pimpls.AlwaysInBusiness, priority=1,
                                 when: datetime = None) -> ev_sys.BusinessHoursScheduler:
        if business_hours is None:
            business_hours = pimpls.AlwaysInBusiness
        if client in self._client_scheduler_map:
            #  duplicated in the case of arrival process as it removes itself from its scheduler
            self._client_scheduler_map[client].remove_client(client)
        scheduler: ev_sys.BusinessHoursScheduler
        if business_hours not in self._bh_schedulers:
            scheduler = ev_sys.BusinessHoursScheduler(
                self.event_queue, business_hours, intended_start=when)
            self._unstarted_schedulers.append((priority, scheduler))
            self._bh_schedulers[business_hours] = scheduler
        else:
            scheduler = self._bh_schedulers[business_hours]
        scheduler.add_client(client)
        self._client_scheduler_map[client] = scheduler
        return scheduler

    def start_schedulers(self):
        # start according to highest priority
        for _, scheduler in sorted(self._unstarted_schedulers, key=lambda t: t[0], reverse=True):
            scheduler.start()
        self._unstarted_schedulers.clear()

    def cleanup_schedulers(self):
        to_remove = set()
        for bh, scheduler in self._bh_schedulers.items():
            if not scheduler.has_clients:
                scheduler.force_terminate()
            if scheduler.has_terminated:
                to_remove.add(bh)
        for bh in to_remove:
            del self._bh_schedulers[bh]

    def add_arrival_process(self, arrival_label: str, arrival_config: mconfig.ArrivalProcessConfig):
        limit = self.execution_parameters[ExecutionParameters.CasesToGenerate] if self.execution_parameters.get(
            ExecutionParameters.CasesToGenerate) else numpy.inf

        def external_termination_check():
            return self.simulation_context.total_started_cases >= limit

        arrival_process = ev_sys.ScheduledArrivalProcessScheduler(self.event_queue, arrival_config.inter_arrivals,
                                                                  current_creation_count=self.simulation_context.total_started_cases,
                                                                  creation_count_limit=self.execution_parameters.get(
                                                                      ExecutionParameters.CasesToGenerate),
                                                                  date_limit=self.execution_parameters.get(
                                                                      ExecutionParameters.GenerationCutoffDate,
                                                                      arrival_config.last_arrival),
                                                                  label=arrival_label,
                                                                  external_termination_check=external_termination_check)

        arrival_process.add_client(self.arrival_model)
        arrival_process_scheduler = self._schedule_business_hours(arrival_process, arrival_config.business_hours,
                                                                  priority=2, when=arrival_config.first_arrival)
        arrival_process.scheduler = arrival_process_scheduler
        self.arrival_processes[arrival_label] = (
            arrival_config, arrival_process)

    def remove_arrival_process(self, arrival_label: str = None):
        if arrival_label is None:  # last added arrival process
            arrival_config, arrival_process = self.arrival_processes.popitem()[
                1]
        else:
            arrival_config, arrival_process = self.arrival_processes[arrival_label]
            del self.arrival_processes[arrival_label]
        arrival_process.force_terminate()

    def set_activity_business_hours(self, activity: str, business_hours: params.BusinessHours):
        self._schedule_business_hours(
            self.activity_datas[activity], business_hours)

    def set_resource_business_hours(self, resource: str, business_hours: params.BusinessHours):
        self._schedule_business_hours(
            self.resource_datas[resource], business_hours)

    def start(self):
        self.start_schedulers()

    def perform_hot_change(self, change: Callable[..., None]):
        self.cleanup_schedulers()
        change()
        self.start_schedulers()


@dataclass(unsafe_hash=True)
class SimulationModel:
    graph: sgraph.SimulationGraph
    event_queue: ev_sys.EventQueue
    scheduling_manager: SchedulingManager
    activity_manager: smanagers.ActivityManager
    resource_manager: smanagers.ResourceManager
    simulation_context: SimulationContext
    execution_parameters: Dict[ExecutionParameters, Any]


class Simulator:
    time_check_interval = 10

    def __init__(self, simulation_model: SimulationModel) -> None:
        self.simulation_model = simulation_model
        self.scheduling_manager = simulation_model.scheduling_manager
        self.terminal = self.simulation_model.graph.terminal.model
        self.arrival = self.simulation_model.graph.arrival.model
        self.event_queue = simulation_model.event_queue
        self.exp = simulation_model.execution_parameters

        self.termination_checks = []

        self.simulation_start: datetime
        self.simulation_end: datetime

    def setup(self):
        self.simulation_start = time_utils.now()
        self.iteration = 0

        self.termination_checks = [(lambda: not self.event_queue.empty(
        ), 'Terminated due to event queue being empty.')]

        if self.exp.get(ExecutionParameters.CasesToGenerate) is not None:
            case_limit = self.exp[ExecutionParameters.CasesToGenerate]

            def casesToGenerate():
                return self.simulation_model.simulation_context.total_completed_cases < case_limit

            self.termination_checks.append(
                (casesToGenerate, 'Terminated due to CasesToGenerate being reached.'))

        if self.exp.get(ExecutionParameters.SimCutoffDate) is not None:
            sim_limit = time_utils.make_timezone_aware(
                self.exp[ExecutionParameters.SimCutoffDate])

            def simCutoffDate():
                return self.event_queue.global_time < sim_limit

            self.termination_checks.append(
                (simCutoffDate, 'Terminated due to simulation stopping date being reached'))

        if self.exp.get(ExecutionParameters.RealtimeLimit) is not None:
            rl_limit = time_utils.add(
                self.simulation_start, self.exp[ExecutionParameters.RealtimeLimit])

            def realtimeCutoffDate():
                return self.iteration % self.time_check_interval != 0 or time_utils.now() < rl_limit

            self.termination_checks.append(
                (realtimeCutoffDate, 'Terminated due to execution time limit being reached.'))

        if self.exp.get(ExecutionParameters.Pause) is not None:
            self.event_queue.pause_step = self.exp[ExecutionParameters.Pause]["step"]
            self.event_queue.pause_length = self.exp[ExecutionParameters.Pause]["length"]
            self.event_queue.pause = time_utils.add(
                self.simulation_start, self.event_queue.pause_step)

    def run(self, simulation_log_filename=None):
        self.setup()

        if simulation_log_filename is not None:
            logging.basicConfig(
                filename=os.path.join(
                    utils.PathConstants.base_simulation_log_path, simulation_log_filename),
                filemode='w', level=logging.INFO, force=True)
            logging.info(
                f'Started Simulation @{self.simulation_start} with the following execution parameters')
            logging.info(str(self.exp))

        self.scheduling_manager.start()
        while all(c() for c, desc in self.termination_checks):
            self.event_queue.step()
            self.iteration += 1

        for c, desc in self.termination_checks:
            if not c():
                logging.info(desc)

        self.simulation_end = time_utils.now()

    def pause(self, streaming_output_log):
        if self.event_queue.pause is not None:
            if self.event_queue.global_time > self.event_queue.pause:
                print(
                    f'Pause at {self.event_queue.pause} (global time: {self.event_queue.global_time})')
                # time.sleep(self.pause_length)
                print(f'Export logs')
                if streaming_output_log is not None:
                    print(streaming_output_log)
                    oc_log = self.get_oc_log(AvailableLifecycles.StartOnly)
                    export = export_factory.apply(
                        oc_log, streaming_output_log)
                for message in iter(sys.stdin.readline, ''):
                    message = message[:-1]
                    print(f'input: {message}')
                    if message == "resume":
                        break
                self.event_queue.pause = time_utils.add(
                    self.event_queue.pause, self.event_queue.pause_step)

    def control_run(self, simulation_log_filename=None, streaming_output_log=None):
        print(f'Start simulation')
        self.setup()

        if simulation_log_filename is not None:
            logging.basicConfig(
                filename=os.path.join(
                    utils.PathConstants.base_simulation_log_path, simulation_log_filename),
                filemode='w', level=logging.INFO, force=True)
            logging.info(
                f'Started Simulation @{self.simulation_start} with the following execution parameters')
            logging.info(str(self.exp))

        self.scheduling_manager.start()
        while all(c() for c, desc in self.termination_checks):
            if streaming_output_log is not None:
                self.pause(streaming_output_log)
            else:
                self.pause()
            self.event_queue.step()
            self.iteration += 1

            for c, desc in self.termination_checks:
                if not c():
                    logging.info(desc)

            self.simulation_end = time_utils.now()

    @property
    def generated_cases(self):
        return self.terminal.arrived_cases

    @property
    def ongoing_cases(self):
        return self.arrival.arrived_cases

    @property
    def duration(self):
        return self.simulation_end - self.simulation_start

    def get_oc_log(self, allowed_lifecycles: Union[Dict[str, AvailableLifecycles], AvailableLifecycles] = None):

        filter_method = None

        if isinstance(allowed_lifecycles, dict):
            def filter_method(e):
                return e.activity in allowed_lifecycles and e.lifecycle in allowed_lifecycles[e.activity].vals
        elif isinstance(allowed_lifecycles, AvailableLifecycles):
            def filter_method(e):
                return e.lifecycle in allowed_lifecycles.vals
        # iterable = (c.filter(filter_method) for c in
        #             self.generated_cases) if filter_method is not None else self.generated_cases

        iterable = (c.filter(filter_method) for c in
                    self.ongoing_cases) if filter_method is not None else self.ongoing_cases

        return utils.create_oc_log(iterable)


def simulate(configured_simulation_model: SimulationModel, logging=True, simulation_log_filename=None) -> Simulator:
    simulator = Simulator(configured_simulation_model)
    if logging and simulation_log_filename is None:
        simulation_log_filename = f'{time_utils.filenameable_timestamp()}.log'
    simulator.run(simulation_log_filename=simulation_log_filename)
    return simulator


def control_simulate(configured_simulation_model: SimulationModel, logging=True, simulation_log_filename=None, streaming_output_log=None) -> Simulator:
    simulator = Simulator(configured_simulation_model)
    if logging and simulation_log_filename is None:
        simulation_log_filename = f'{time_utils.filenameable_timestamp()}.log'
    simulator.control_run(
        simulation_log_filename=simulation_log_filename, streaming_output_log=streaming_output_log)
    return simulator


def create_simulation_model(simulation_graph: sgraph.SimulationGraph,
                            model_configuration: sim.model_configuration.ModelConfiguration,
                            execution_parameters: Dict[ExecutionParameters, Any] = None) -> SimulationModel:
    assert simulation_graph.activity_map.keys() <= model_configuration.activities.keys()
    assert simulation_graph.decision_map.keys() <= model_configuration.decisions.keys()
    if execution_parameters is None:
        execution_parameters = default_execution_parameters()

    sc = SimulationContext()

    simulation_graph.arrival.model = smodel.ArrivalModel(
        node=simulation_graph.arrival, simulation_context=sc)
    simulation_graph.terminal.model = smodel.TerminalModel(
        node=simulation_graph.terminal, simulation_context=sc)

    event_queue = ev_sys.EventQueue()

    earliest = min(
        ac.first_arrival for ac in model_configuration.arrivals.values())
    earliest = time_utils.make_timezone_aware(earliest)
    if execution_parameters.get(ExecutionParameters.SimStartDate) is not None:
        earliest = max(earliest, time_utils.make_timezone_aware(
            execution_parameters[ExecutionParameters.SimStartDate]))
    event_queue.global_time = earliest

    for decision_label, node in simulation_graph.decision_map.items():
        node.classifier = model_configuration.decisions[decision_label].classifier

    rm = smanagers.ResourceManager(event_queue)
    am = smanagers.ActivityManager(event_queue)
    am.resource_manager = rm
    rm.activity_manager = am

    activities = simulation_graph.activity_map
    for activity_label, activity_configuration in model_configuration.activities.items():
        if activity_label not in activities:
            continue
        a_model = smodel.ActivityModel(activities[activity_label], event_queue)
        a_data = sdata.OCActivityData(a_model, activity_manager=am)
        a_data.properties[sim.enums.ActivityProperty.QueueingDiscipline] = activity_configuration.queueing_discipline
        a_data.properties[
            sim.enums.ActivityProperty.ProcessingTimeSampler] = activity_configuration.processing_time_sampler
        if activity_configuration.delay_sampler is not None:
            a_data.properties[sim.enums.ActivityProperty.DelaySampler] = activity_configuration.delay_sampler
        activities[activity_label].model = a_model
        a_model.data = a_data

    resources = {}
    for resource_label, resource_config in model_configuration.resources.items():
        resource = smodel.ResourceModel(resource_label, event_queue)
        r_data = sdata.ResourceData(resource, resource_manager=rm)
        r_data.properties[sim.enums.ResourceProperty.Capacity] = resource_config.capacity
        if resource_config.performance is not None:
            r_data.properties[sim.enums.ResourceProperty.Performance] = resource_config.performance
        resource.data = r_data
        resources[resource_label] = resource

    ar_mapping = {activities[activity_label].model: {resources[resource_label] for resource_label in
                                                     assignable_resources} for activity_label, assignable_resources in
                  model_configuration.mapping.assignable_resources.items()}
    ar_propensities = None
    if model_configuration.mapping.propensities is not None:
        ar_propensities = {activities[activity_label].model: {resources[resource_label]: p for resource_label, p in
                                                              resource_propensities.items()} for
                           activity_label, resource_propensities in model_configuration.mapping.propensities.items()}
    arc = smanagers.ActivityResourceCorrespondence(ar_mapping, ar_propensities)

    rm.ar_correspondence = arc
    am.ar_correspondence = arc

    activity_datas = {activity_label: activity_node.model.data for activity_label,
                      activity_node in activities.items()}
    resource_datas = {resource_label: resource_model.data for resource_label,
                      resource_model in resources.items()}

    scheduling_manager = SchedulingManager(event_queue,
                                           Schedulables(
                                               simulation_graph.arrival.model, activity_datas, resource_datas),
                                           sc, execution_parameters)

    for arrival_label, arrival_config in model_configuration.arrivals.items():
        scheduling_manager.add_arrival_process(arrival_label, arrival_config)
    for activity_label, activity_configuration in model_configuration.activities.items():
        scheduling_manager.set_activity_business_hours(
            activity_label, activity_configuration.business_hours)
    for resource_label, resource_config in model_configuration.resources.items():
        scheduling_manager.set_resource_business_hours(
            resource_label, resource_config.business_hours)

    return SimulationModel(graph=simulation_graph, event_queue=event_queue, scheduling_manager=scheduling_manager,
                           activity_manager=am, resource_manager=rm, simulation_context=sc,
                           execution_parameters=execution_parameters)


def create_oc_simulation_model(simulation_graph: sgraph.SimulationGraph,
                               model_configuration: sim.model_configuration.ModelConfiguration,
                               execution_parameters: Dict[ExecutionParameters, Any] = None) -> SimulationModel:
    assert simulation_graph.activity_map.keys() <= model_configuration.activities.keys()
    assert simulation_graph.decision_map.keys() <= model_configuration.decisions.keys()
    if execution_parameters is None:
        execution_parameters = default_execution_parameters()

    sc = OCSimulationContext(model_configuration.objects)

    simulation_graph.arrival.model = smodel.OCArrivalModel(
        node=simulation_graph.arrival, simulation_context=sc)
    simulation_graph.terminal.model = smodel.TerminalModel(
        node=simulation_graph.terminal, simulation_context=sc)

    event_queue = ev_sys.EventQueue()

    earliest = min(
        ac.first_arrival for ac in model_configuration.arrivals.values())
    earliest = time_utils.make_timezone_aware(earliest)
    if execution_parameters.get(ExecutionParameters.SimStartDate) is not None:
        earliest = max(earliest, time_utils.make_timezone_aware(
            execution_parameters[ExecutionParameters.SimStartDate]))
    event_queue.global_time = earliest

    for decision_label, node in simulation_graph.decision_map.items():
        node.classifier = model_configuration.decisions[decision_label].classifier

    rm = smanagers.ResourceManager(event_queue)
    am = smanagers.ActivityManager(event_queue)
    am.resource_manager = rm
    rm.activity_manager = am

    activities = simulation_graph.activity_map
    for activity_label, activity_configuration in model_configuration.activities.items():
        if activity_label not in activities:
            continue
        a_model = smodel.ActivityModel(activities[activity_label], event_queue)
        a_data = sdata.OCActivityData(a_model, activity_manager=am)
        a_data.properties[sim.enums.ActivityProperty.QueueingDiscipline] = activity_configuration.queueing_discipline
        a_data.properties[
            sim.enums.ActivityProperty.ProcessingTimeSampler] = activity_configuration.processing_time_sampler
        if activity_configuration.delay_sampler is not None:
            a_data.properties[sim.enums.ActivityProperty.DelaySampler] = activity_configuration.delay_sampler
        a_data.properties[sim.enums.ActivityProperty.ObjectType] = activity_configuration.object_type
        activities[activity_label].model = a_model
        a_model.data = a_data

    resources = {}
    for resource_label, resource_config in model_configuration.resources.items():
        resource = smodel.ResourceModel(resource_label, event_queue)
        r_data = sdata.ResourceData(resource, resource_manager=rm)
        r_data.properties[sim.enums.ResourceProperty.Capacity] = resource_config.capacity
        if resource_config.performance is not None:
            r_data.properties[sim.enums.ResourceProperty.Performance] = resource_config.performance
        resource.data = r_data
        resources[resource_label] = resource

    ar_mapping = {activities[activity_label].model: {resources[resource_label] for resource_label in
                                                     assignable_resources} for activity_label, assignable_resources in
                  model_configuration.mapping.assignable_resources.items()}
    ar_propensities = None
    if model_configuration.mapping.propensities is not None:
        ar_propensities = {activities[activity_label].model: {resources[resource_label]: p for resource_label, p in
                                                              resource_propensities.items()} for
                           activity_label, resource_propensities in model_configuration.mapping.propensities.items()}
    arc = smanagers.ActivityResourceCorrespondence(ar_mapping, ar_propensities)

    rm.ar_correspondence = arc
    am.ar_correspondence = arc

    activity_datas = {activity_label: activity_node.model.data for activity_label,
                      activity_node in activities.items()}
    resource_datas = {resource_label: resource_model.data for resource_label,
                      resource_model in resources.items()}

    scheduling_manager = SchedulingManager(event_queue,
                                           Schedulables(
                                               simulation_graph.arrival.model, activity_datas, resource_datas),
                                           sc, execution_parameters)

    for arrival_label, arrival_config in model_configuration.arrivals.items():
        scheduling_manager.add_arrival_process(arrival_label, arrival_config)
    for activity_label, activity_configuration in model_configuration.activities.items():
        scheduling_manager.set_activity_business_hours(
            activity_label, activity_configuration.business_hours)
    for resource_label, resource_config in model_configuration.resources.items():
        scheduling_manager.set_resource_business_hours(
            resource_label, resource_config.business_hours)

    return SimulationModel(graph=simulation_graph, event_queue=event_queue, scheduling_manager=scheduling_manager,
                           activity_manager=am, resource_manager=rm, simulation_context=sc,
                           execution_parameters=execution_parameters)
