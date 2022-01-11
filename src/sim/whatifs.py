import datetime
from dataclasses import dataclass
from typing import Any

import sim.event_system as ev_sys
import sim.model_parameters as params
import sim.simulation
from sim.enums import ActivityProperty, ResourceProperty
from sim.model_configuration import ArrivalProcessConfig
from sim.time_utils import make_timezone_aware

@dataclass(unsafe_hash=True)
class BusinessHoursAdaptationEvent(ev_sys.Event):
    target: str
    new_business_hours: params.BusinessHours


@dataclass(unsafe_hash=True)
class ArrivalProcessAdaptationEvent(ev_sys.Event):
    ...


@dataclass(unsafe_hash=True)
class ArrivalProcessInsertionEvent(ArrivalProcessAdaptationEvent):
    new_process: str
    new_config: ArrivalProcessConfig


@dataclass(unsafe_hash=True)
class ArrivalProcessRemovalEvent(ArrivalProcessAdaptationEvent):
    old_process: str


@dataclass(unsafe_hash=True)
class ArrivalProcessSwapEvent(ArrivalProcessAdaptationEvent):
    old_process: str
    new_process: str
    new_config: ArrivalProcessConfig


class ButWhatIf:

    def __init__(self, sim_model: sim.simulation.SimulationModel) -> None:
        self.sim_model = sim_model
        self.scheduling_manager = sim_model.scheduling_manager
        self.working_set = {}
        self.scheduled_changes = []
        sim_model.graph.decision_map
        self.activity_datas = {am.label: am.data for am in sim_model.activity_manager.activity_demand}
        self.resource_datas = {rm.label: rm.data for rm in sim_model.resource_manager.resource_supply}

    def add(self, when, callback, event):
        self.scheduled_changes.append(ev_sys.TimedCallback(make_timezone_aware(when), callback, event))

    def hot(self, what):
        self.scheduling_manager.perform_hot_change(what)

    def schedule_activity_property_change(self, when: datetime.datetime, activity: str, key: ActivityProperty,
                                          new_value: Any) -> None:
        self.add(when, self.activity_datas[activity].receive_event, ev_sys.DictUpdateEvent(key, new_value))

    def schedule_resource_property_change(self, when: datetime.datetime, resource: str, key: ResourceProperty,
                                          new_value: Any) -> None:
        self.add(when, self.resource_datas[resource].receive_event,
                 ev_sys.DictUpdateEvent(key, new_value))

    def _activity_business_hours_change(self, event: BusinessHoursAdaptationEvent):
        def change():
            self.scheduling_manager.set_activity_business_hours(event.target, event.new_business_hours)

        self.hot(change)

    def _resource_business_hours_change(self, event: BusinessHoursAdaptationEvent):
        def change():
            self.scheduling_manager.set_resource_business_hours(event.target, event.new_business_hours)

        self.hot(change)

    def _arrival_process_change(self, event: ArrivalProcessAdaptationEvent):
        def change():
            if isinstance(event, ArrivalProcessRemovalEvent):
                self.scheduling_manager.remove_arrival_process(event.old_process)
            elif isinstance(event, ArrivalProcessInsertionEvent):
                self.scheduling_manager.add_arrival_process(event.new_process, event.new_config)
            elif isinstance(event, ArrivalProcessSwapEvent):
                self.scheduling_manager.remove_arrival_process(event.old_process)
                self.scheduling_manager.add_arrival_process(event.new_process, event.new_config)

        self.hot(change)

    def schedule_activity_business_hours_change(self, when: datetime.datetime, resource: str,
                                                new_business_hours: params.BusinessHours) -> None:
        self.add(when, self._activity_business_hours_change, BusinessHoursAdaptationEvent(resource, new_business_hours))

    def schedule_resource_business_hours_change(self, when: datetime.datetime, resource: str,
                                                new_business_hours: params.BusinessHours) -> None:
        self.add(when, self._resource_business_hours_change, BusinessHoursAdaptationEvent(resource, new_business_hours))

    def schedule_arrival_process_removal(self, when: datetime.datetime, arrival_label: str):
        self.add(when, self._arrival_process_change, ArrivalProcessRemovalEvent(arrival_label))

    def schedule_arrival_process_insertion(self, when: datetime.datetime, arrival_label: str,
                                           config: ArrivalProcessConfig):
        self.add(when, self._arrival_process_change, ArrivalProcessInsertionEvent(arrival_label, config))

    def schedule_arrival_process_swap(self, when: datetime.datetime, arrival_label: str, config: ArrivalProcessConfig):
        self.add(when, self._arrival_process_change, ArrivalProcessSwapEvent(arrival_label, arrival_label, config))

    def apply(self):
        for timed_callback in self.scheduled_changes:
            self.sim_model.event_queue.offer(timed_callback)
