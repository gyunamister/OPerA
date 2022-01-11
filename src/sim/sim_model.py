from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Set, Tuple, List
from typing import TYPE_CHECKING

import sim.case
import sim.event_system as ev_sys
from sim import time_utils

if TYPE_CHECKING:
    import sim.model_parameters as params
    import sim.sim_data as sdata
    import sim.sim_graph as sgraph
    from sim.simulation import SimulationContext, OCSimulationContext


@dataclass(unsafe_hash=True)
class Assignment:
    activity: ActivityModel
    case: sim.case.OCCase
    # timestamp: datetime


class SimulationNodeModel:

    def __init__(self, node: sgraph.WithModel = None, **kwargs) -> None:
        super(SimulationNodeModel, self).__init__(**kwargs)
        self.__node = node

    @property
    def node(self) -> sgraph.WithModel:
        return self.__node

    @node.setter
    def node(self, value: sgraph.WithModel):
        assert value is not None
        self.__node = value

    def accept(self, case: sim.case.OCCase):
        pass

    def forward(self, case: sim.case.OCCase):
        self.node.accept_from_model(case)


class ResourceModel:

    def __init__(self, label: str, event_system: ev_sys.EventQueue) -> None:
        self.label = label
        self.event_queue = event_system
        self.current_assignments: Set[Assignment] = set()
        self.__data = None

    @property
    def data(self) -> sdata.ResourceData:
        return self.__data

    @data.setter
    def data(self, value: sdata.ResourceData):
        assert value is not None
        self.__data = value

    @property
    def event_queue(self) -> ev_sys.EventQueue:
        return self.__event_queue

    @event_queue.setter
    def event_queue(self, value) -> None:
        assert value is not None
        self.__event_queue = value

    def cooldown(self, delta: timedelta):
        # TODO not happy with this
        logging.info(f'{self.label} is cooling down for {delta}')
        self.event_queue.offer_delayed(delta, ev_sys.Callback(self.data.receive_event,
                                                              ev_sys.DictUpdateEvent('on_cooldown', False)))

    def assign(self, activity: ActivityModel, case: sim.case.OCCase) -> None:
        self.current_assignments.add(Assignment(activity, case))
        self.data.assignment_changed(released=False)

    def release(self, activity: ActivityModel, case: sim.case.OCCase) -> None:
        self.current_assignments.remove(Assignment(activity, case))
        self.data.assignment_changed(released=True)

    def __str__(self) -> str:
        return self.label


class ActivityModel(SimulationNodeModel):

    def __init__(self, activity_node: sgraph.ActivityNode, event_queue: ev_sys.EventQueue,
                 data: sdata.OCActivityData = None, **kwargs) -> None:
        super(ActivityModel, self).__init__(node=activity_node, **kwargs)
        self.label = activity_node.label
        self.waiting_queue: List[Tuple[datetime, sim.case.OCCase]] = []
        self.event_queue = event_queue
        self.__data = data

    @property
    def data(self) -> sdata.OCActivityData:
        return self.__data

    @data.setter
    def data(self, value: sdata.OCActivityData):
        assert value is not None
        self.__data = value

    @property
    def event_queue(self) -> ev_sys.EventQueue:
        return self.__event_queue

    @event_queue.setter
    def event_queue(self, value) -> None:
        assert value is not None
        self.__event_queue = value

    def use_resource(self, resource: ResourceModel):
        case = self.data.dequeue(self.waiting_queue)
        self.process(case, resource)

    def accept(self, case: sim.case.OCCase):
        self.delay(case)

    def delay(self, case: sim.case.OCCase):
        delay = self.data.sample_delay(case)
        if delay is None:
            self.schedule(case)
        else:
            self.event_queue.offer_delayed(delay, ev_sys.Callback(
                self.after_delay, ev_sys.CaseDelayedEvent(case)))

    def after_delay(self, delay_event: ev_sys.CaseDelayedEvent):
        self.schedule(delay_event.case)

    def schedule(self, case: sim.case.OCCase):
        global_time = self.event_queue.global_time
        case.add_event(sim.case.OCCaseEvent(
            self.label, 'n/a', global_time, lifecycle='schedule'))
        logging.info(f'{self.label} enqueued case {case.case_id}')
        self.waiting_queue.append((global_time, case))
        self.data.queue_changed()

    def process(self, case: sim.case.OCCase, resource: ResourceModel):
        global_time = self.event_queue.global_time
        processing_time = self.data.sample_processing_time(case, resource)
        event_object_mapping = self.data.get_event_object_mapping(case)
        event_value_mapping = self.data.get_value_mapping(case)
        case.update_object_value_mapping(event_value_mapping)
        completion_time = time_utils.add(global_time, processing_time)
        start = sim.case.OCCaseEvent(
            self.label, resource.label, global_time, lifecycle='start', duration=processing_time, event_value_mapping={}, event_object_mapping=event_object_mapping)
        case.add_event(start)
        logging.info(
            f'{self.label} started processing of case {case.case_id} with {resource} for {processing_time} (@{completion_time})')
        complete = sim.case.OCCaseEvent(
            self.label, resource.label, completion_time, lifecycle='complete')
        timed_callback = ev_sys.TimedCallback(completion_time, self.after_processing,
                                              ev_sys.ProcessingCompletionEvent(case, resource, complete))
        resource.assign(self, case)
        self.event_queue.offer(timed_callback)
        self.data.queue_changed()

    def after_processing(self, completion_event: ev_sys.ProcessingCompletionEvent):
        self.complete(completion_event.case,
                      completion_event.resource, completion_event.case_event)

    def complete(self, case: sim.case.OCCase, resource: ResourceModel, case_event: sim.case.OCCaseEvent):
        case.add_event(case_event)
        logging.info(
            f'{self.label} completed processing of case {case.case_id} with {resource}')
        resource.release(self, case)
        self.forward(case)

    def __str__(self) -> str:
        return self.label


class DelayModel(SimulationNodeModel):

    def __init__(self, event_queue: ev_sys.EventQueue, delay_sampler: params.DelaySampler, **kwargs) -> None:
        super(DelayModel, self).__init__(**kwargs)
        self.event_queue = event_queue
        self.delay_sampler = delay_sampler

    @property
    def event_queue(self) -> ev_sys.EventQueue:
        return self.__event_system

    @event_queue.setter
    def event_queue(self, value) -> None:
        self.__event_system = value

    @property
    def delay_sampler(self) -> params.DelaySampler:
        return self._delay_sampler

    @delay_sampler.setter
    def delay_sampler(self, value: params.DelaySampler) -> None:
        self._delay_sampler = value

    def accept(self, case: sim.case.OCCase):
        self.delay(case)

    def delay(self, case: sim.case.OCCase) -> None:
        global_time = self.event_queue.global_time
        delta = self.delay_sampler.sample(global_time)
        self.event_queue.offer_delayed(delta, ev_sys.Callback(
            self.after_delay, ev_sys.CaseDelayedEvent(case)))

    def after_delay(self, case_delayed_event: ev_sys.CaseDelayedEvent) -> None:
        self.forward(case_delayed_event.case)


class WithSimulationContext:

    def __init__(self, simulation_context: SimulationContext, **kwargs) -> None:
        super(WithSimulationContext, self).__init__(**kwargs)
        self.simulation_context = simulation_context


class WithOCSimulationContext:

    def __init__(self, simulation_context: OCSimulationContext, **kwargs) -> None:
        super(WithOCSimulationContext, self).__init__(**kwargs)
        self.simulation_context = simulation_context


class TerminalModel(WithSimulationContext, SimulationNodeModel):

    def __init__(self, **kwargs) -> None:
        super(TerminalModel, self).__init__(**kwargs)
        self.__arrived_cases = []
        self.observed_case_ids = set()

    @property
    def case_count(self):
        return len(self.arrived_cases)

    @property
    def arrived_cases(self) -> List[sim.case.OCCase]:
        return self.__arrived_cases

    def accept(self, case: sim.case.OCCase):
        self.simulation_context.register_case_completion()
        self.arrived_cases.append(case)
        assert case.case_id not in self.observed_case_ids
        self.observed_case_ids.add(case.case_id)
        logging.info(
            f'TerminalNode received case {case.case_id} (total: {self.case_count})')


class ArrivalModel(WithSimulationContext, ev_sys.Updatable, SimulationNodeModel):

    def receive_event(self, event: ev_sys.CaseArrivalEvent):
        case = sim.case.OCCase(case_id=event.source + '_case_' +
                               str(self.simulation_context.get_case_number()))
        self.simulation_context.register_case_creation()
        logging.info(f'ArrivalModel created case {case.case_id}')
        self.node.accept_from_model(case)


class OCArrivalModel(WithOCSimulationContext, ev_sys.Updatable, SimulationNodeModel):
    def __init__(self, **kwargs) -> None:
        super(OCArrivalModel, self).__init__(**kwargs)
        self.__arrived_cases = []

    @property
    def arrived_cases(self) -> List[sim.case.OCCase]:
        return self.__arrived_cases

    def receive_event(self, event: ev_sys.CaseArrivalEvent):
        objects = self.simulation_context.create_objects()
        case = sim.case.OCCase(case_id=event.source + '_case_' +
                               str(self.simulation_context.get_case_number()), objects=objects)
        self.simulation_context.register_case_creation()
        self.arrived_cases.append(case)

        logging.info(f'ArrivalModel created case {case.case_id}')
        self.node.accept_from_model(case)
