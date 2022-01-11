from __future__ import annotations

from datetime import timedelta, datetime
from typing import List, Any, Dict, Tuple
from typing import TYPE_CHECKING

import sim.event_system as ev_sys
import sim.parameter_implementations as pimpls
import sim.utils
from sim.enums import ActivityProperty, ActivityState, ResourceProperty, ResourceState

if TYPE_CHECKING:
    import sim.case
    import sim.managers as smanagers
    import sim.sim_model as smodel


@sim.utils.auto_str
class OCActivityData(ev_sys.Updatable):

    def __init__(self, activity_model: smodel.ActivityModel,
                 activity_manager: smanagers.ActivityManager = None) -> None:
        super(OCActivityData, self).__init__()
        self.activity_model = activity_model
        self.__activity_manager = activity_manager
        self.__properties: Dict[ActivityProperty,
                                Any] = OCActivityData.initial_properties()
        self.__state: Dict[ActivityState, Any] = OCActivityData.initial_state()
        self.__is_demanding: bool = False

    @staticmethod
    def initial_properties():
        return {
            ActivityProperty.QueueingDiscipline: pimpls.Fifo,
            ActivityProperty.ProcessingTimeSampler: pimpls.StaticSampler(timedelta(minutes=60)),
        }

    @staticmethod
    def initial_state():
        return {ActivityState.InBusiness: False,
                ActivityState.QueueLength: 0}

    @property
    def is_demanding(self) -> bool:
        return self.__is_demanding

    @property
    def activity_manager(self) -> smanagers.ActivityManager:
        return self.__activity_manager

    @activity_manager.setter
    def activity_manager(self, value: smanagers.ActivityManager):
        assert value is not None
        self.__activity_manager = value

    @property
    def properties(self) -> Dict[ActivityProperty, Any]:
        return self.__properties

    @properties.setter
    def properties(self, value: Dict[ActivityProperty, Any]):
        assert value is not None
        self.__properties = value

    def peek_at_state(self, key: ActivityState):
        return self.__state.get(key)

    def peek_at_property(self, key: ActivityProperty):
        return self.__properties.get(key)

    def queue_changed(self) -> None:
        self.__state[ActivityState.QueueLength] = len(
            self.activity_model.waiting_queue)
        self._determine_status()

    def receive_event(self, event: ev_sys.DictUpdateEvent) -> None:
        key = event.key
        if type(key) is ActivityState:
            self.__state[key] = event.new_value
        elif key in ActivityState.vals:
            self.__state[ActivityState(key)] = event.new_value
        elif type(key) is ActivityProperty:
            self.properties[key] = event.new_value
        elif key in ActivityProperty.vals:
            self.properties[ActivityProperty(key)] = event.new_value
        self._determine_status()

    def _determine_status(self):
        new_status = self.__state[ActivityState.InBusiness] and self.__state[ActivityState.QueueLength] > 0
        if self.is_demanding is not new_status:
            self.__is_demanding = new_status
            self.activity_manager.activity_demand_change(
                self.activity_model, new_status)

    def dequeue(self, queue: List[Tuple[datetime, sim.case.OCCase]]) -> sim.case.OCCase:
        return queue.pop(self.properties[ActivityProperty.QueueingDiscipline].select(queue))[1]

    def sample_processing_time(self, case: sim.case.OCCase, resource: smodel.ResourceModel) -> timedelta:
        return self.properties[ActivityProperty.ProcessingTimeSampler].sample(case, resource)

    def sample_delay(self, case: sim.case.OCCase):
        if ActivityProperty.DelaySampler in self.properties:
            return self.properties[ActivityProperty.DelaySampler].sample(case)

    def get_event_object_mapping(self, case: sim.case.OCCase) -> Dict[str, List[str]]:
        if ActivityProperty.ObjectType in self.properties:
            return case.get_object_mapping(self.properties[ActivityProperty.ObjectType].keys())
        else:
            return dict()

    def get_value_mapping(self, case: sim.case.OCCase) -> Dict[str, Dict[str, object]]:
        vmap = dict()
        for k in self.properties[ActivityProperty.ObjectType].keys():
            for obj in case.objects:
                if obj.object_type == k:
                    vmap[obj.object_id] = {}
                    for attr in self.properties[ActivityProperty.ObjectType][k]:
                        vmap[obj.object_id][attr] = self.properties[ActivityProperty.ObjectType][k][attr].sample(
                        )
        return vmap

    def sample_object(self):
        return {"test": "test"}

    def sample_attributes(self):
        return {"test": "test"}


@sim.utils.auto_str
class ResourceData(ev_sys.Updatable):

    def __init__(self, resource: smodel.ResourceModel, resource_manager: smanagers.ResourceManager = None) -> None:
        super(ResourceData, self).__init__()
        self.resource = resource
        self.__resource_manager = resource_manager
        self.__properties: Dict[ResourceProperty,
                                Any] = ResourceData.initial_properties()
        self.__state: Dict[ResourceState, Any] = ResourceData.initial_state()
        self.__is_supplying: bool = False

    @staticmethod
    def initial_properties():
        return {ResourceProperty.Capacity: 1, ResourceProperty.Cooldown: timedelta(seconds=1)}

    @staticmethod
    def initial_state():
        return {ResourceState.InBusiness: False,
                ResourceState.CurrentlyAssigned: 0,
                ResourceState.OnCooldown: False,
                ResourceState.Disabled: False}

    @property
    def is_supplying(self) -> bool:
        return self.__is_supplying

    @property
    def resource_manager(self) -> smanagers.ResourceManager:
        return self.__resource_manager

    @resource_manager.setter
    def resource_manager(self, value: smanagers.ResourceManager):
        assert value is not None
        self.__resource_manager = value

    @property
    def properties(self) -> Dict[ResourceProperty, Any]:
        return self.__properties

    @properties.setter
    def properties(self, value: Dict[ResourceProperty, Any]):
        assert value is not None
        self.__properties = value

    def peek_at_state(self, key: ResourceState):
        return self.__state.get(key)

    def peek_at_property(self, key: ResourceProperty):
        return self.__properties.get(key)

    def assignment_changed(self, released: bool):
        # TODO what was cooldown needed for again?
        # if released:
        #    self.__state[ResourceState.OnCooldown] = True
        #    self.resource.cooldown(self.properties[ResourceProperty.Cooldown])
        self.__state[ResourceState.CurrentlyAssigned] = len(
            self.resource.current_assignments)
        self._determine_status()

    def receive_event(self, event: ev_sys.DictUpdateEvent) -> None:
        key = event.key
        if type(key) is ResourceState:
            self.__state[key] = event.new_value
        elif key in ResourceState.vals:
            self.__state[ResourceState(key)] = event.new_value
        elif type(key) is ResourceProperty:
            self.properties[key] = event.new_value
        elif key in ResourceProperty.vals:
            self.properties[ResourceProperty(key)] = event.new_value
        self._determine_status()

    def _determine_status(self):
        new_state = (not self.__state[ResourceState.Disabled]) \
            and self.__state[ResourceState.InBusiness] \
            and (not self.__state[ResourceState.OnCooldown]) \
            and self.properties[ResourceProperty.Capacity] > self.__state[ResourceState.CurrentlyAssigned]
        if new_state is not self.is_supplying:
            self.__is_supplying = new_state
            self.resource_manager.resource_supply_change(
                self.resource, new_state)
