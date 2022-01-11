from __future__ import annotations

import logging
from numbers import Number
from typing import Dict, Set, KeysView
from typing import TYPE_CHECKING

import numpy as np

from sim.utils import permuted, weighed_permutation

if TYPE_CHECKING:
    import sim.event_system as ev_sys
    import sim.sim_model as smodel


class ActivityResourceCorrespondence:

    def __init__(self, ar_mapping: Dict[smodel.ActivityModel, Set[smodel.ResourceModel]],
                 assignment_propensities: Dict[
                     smodel.ActivityModel, Dict[smodel.ResourceModel, Number]] = None) -> None:
        self.__assignable_activities_map = dict()
        self.__assignable_resources_map = dict()
        for a, resources in ar_mapping.items():
            self.__assignable_resources_map[a] = set(resources)
            for r in resources:
                if r not in self.__assignable_activities_map:
                    self.__assignable_activities_map[r] = set()
                self.__assignable_activities_map[r].add(a)

        if assignment_propensities is None:
            assignment_propensities = dict()
            for a, resources in self.__assignable_resources_map.items():
                assignment_propensities[a] = {r: 1.0 for r in resources}
        resource_activity_propensities = dict()
        for r, activities in self.__assignable_activities_map.items():
            derive = np.array(
                [resource_propensities.get(r, 0.0) for resource_propensities in assignment_propensities.values()],
                dtype=np.float)
            derive = derive / derive.sum()
            resource_activity_propensities[r] = {a: derive[i] for i, a in enumerate(assignment_propensities) if
                                                 derive[i] > 0}
        # print('assignment_propensities', {str(a): {str(r): v for r, v in d.items()} for a,d in assignment_propensities.items()})
        # print('resource_activity_propensities', {str(r): {str(a): v for a, v in d.items()} for r,d in resource_activity_propensities.items()})
        self.__activity_propensity_map = assignment_propensities
        self.__resource_propensity_map = resource_activity_propensities

    @property
    def activities(self) -> KeysView[smodel.ActivityModel]:
        return self.__assignable_resources_map.keys()

    @property
    def resources(self) -> KeysView[smodel.ResourceModel]:
        return self.__assignable_activities_map.keys()

    def activity_propensities(self, resource: smodel.ResourceModel):
        return self.__resource_propensity_map[resource]

    def resource_propensities(self, activity: smodel.ActivityModel):
        return self.__activity_propensity_map[activity]

    def assignable_activities(self, resource: smodel.ResourceModel) -> Set[smodel.ActivityModel]:
        return self.__assignable_activities_map[resource]

    def assignable_resources(self, activity: smodel.ActivityModel) -> Set[smodel.ResourceModel]:
        return self.__assignable_resources_map[activity]

    def is_valid(self, activity, resource):
        return resource in self.__assignable_resources_map[activity]

    def has_assignable_intersection(self, activities, resources):
        # can also be reversed like
        # {itertools.chain(iter(self.assignable_activities(r))) for r in resources}.intersection(activities)
        required_resources = set(r for a in activities for r in self.assignable_resources(a))
        available_resources = set(resources)
        return len(required_resources.intersection(available_resources)) > 0


class ActivityManager:

    def __init__(self, event_queue: ev_sys.EventQueue, resource_manager: ResourceManager = None) -> None:
        self.event_queue = event_queue
        self.__resource_manager = resource_manager
        self.__ar_correspondence = None
        self.activity_demand: Dict[smodel.ActivityModel, bool] = {}
        self.rng = np.random.default_rng()

    @property
    def ar_correspondence(self) -> ActivityResourceCorrespondence:
        return self.__ar_correspondence

    @ar_correspondence.setter
    def ar_correspondence(self, value: ActivityResourceCorrespondence):
        assert value is not None
        self.__ar_correspondence = value
        self.activity_demand = {a: self.activity_demand.get(a, False) for a in value.activities}

    @property
    def resource_manager(self) -> ResourceManager:
        return self.__resource_manager

    @resource_manager.setter
    def resource_manager(self, value: ResourceManager):
        assert value is not None
        self.__resource_manager = value

    def weighed_activities_for_resource(self, resource: smodel.ResourceModel):
        assignable_demanding_activities = list(self.demanding_activities(resource))
        propensities = np.array(
            [self.ar_correspondence.activity_propensities(resource)[a] for a in assignable_demanding_activities],
            dtype=np.float)
        return assignable_demanding_activities, propensities / propensities.sum()

    def demanding_activities(self, resource: smodel.ResourceModel = None):
        return filter(self.activity_demand.get,
                      self.activity_demand if resource is None else self.ar_correspondence.assignable_activities(
                          resource))

    def _demanding_activities_perm(self, resource: smodel.ResourceModel = None):
        return self.rng.permutation(list(self.demanding_activities(resource)))

    def activity_demand_change(self, activity: smodel.ActivityModel, new_state: bool) -> None:
        self.activity_demand[activity] = new_state
        logging.info(f'{activity.label} changed its demand to {new_state}')
        if new_state:
            self.event_queue.offer_end_of_timestep_task(self.whip_workers)

    def distribute_resource(self, resource: smodel.ResourceModel) -> bool:
        activities_for_resource, weights = self.weighed_activities_for_resource(resource)
        if len(activities_for_resource) > 0:
            activity = weighed_permutation(activities_for_resource, weights)[0]
            activity.use_resource(resource)
            return True
        else:
            return False
            # weigh ordering here
            # for activity in permed:  # assign as long as capacity is left
            #    if self.resource_manager.is_supplying(resource):
            #        activity.use_resource(resource)
            #    else:
            #        break

    def whip_workers(self):
        permed = permuted(self.demanding_activities())
        logging.info(
            f'whipping workers {[str(a) for a in permed]} with {[str(r) for r in self.resource_manager.supplying_resources()]}')
        for activity in permed:
            self.resource_manager.provide_resource_for(activity)
        if self.ar_correspondence.has_assignable_intersection(self.demanding_activities(),
                                                              self.resource_manager.supplying_resources()):
            self.whip_workers()


class ResourceManager:

    def __init__(self, event_queue: ev_sys.EventQueue, activity_manager: ActivityManager = None) -> None:
        self.event_queue = event_queue
        self.__activity_manager = activity_manager
        self.__ar_correspondence = None
        self.resource_supply: Dict[smodel.ResourceModel, bool] = {}
        self.rng = np.random.default_rng()

    @property
    def ar_correspondence(self) -> ActivityResourceCorrespondence:
        return self.__ar_correspondence

    @ar_correspondence.setter
    def ar_correspondence(self, value: ActivityResourceCorrespondence):
        assert value is not None
        self.__ar_correspondence = value
        self.resource_supply = {r: self.resource_supply.get(r, False) for r in value.resources}

    @property
    def activity_manager(self) -> ActivityManager:
        return self.__activity_manager

    @activity_manager.setter
    def activity_manager(self, value: ActivityManager):
        assert value is not None
        self.__activity_manager = value

    def weighed_resources_for_activity(self, activity: smodel.ActivityModel):
        assignable_supplying_resources = list(self.supplying_resources(activity))
        propensities = np.array(
            [self.ar_correspondence.resource_propensities(activity)[r] for r in assignable_supplying_resources],
            dtype=np.float)
        return assignable_supplying_resources, propensities / propensities.sum()

    def supplying_resources(self, activity: smodel.ActivityModel = None):
        return filter(self.resource_supply.get,
                      self.resource_supply if activity is None else self.ar_correspondence.assignable_resources(
                          activity))

    def resource_supply_change(self, resource: smodel.ResourceModel, new_state: bool) -> None:
        self.resource_supply[resource] = new_state
        logging.info(f'{resource.label} changed its supply to {new_state}')
        if new_state:
            self.event_queue.offer_end_of_timestep_task(self.redistribute_the_means)

    def redistribute_the_means(self):
        permed = permuted(self.supplying_resources())
        logging.info(
            f'redistributing the means of production {[str(r) for r in permed]} to {[str(a) for a in self.activity_manager.demanding_activities()]}')
        for resource in permed:
            self.activity_manager.distribute_resource(resource)
        if self.ar_correspondence.has_assignable_intersection(self.activity_manager.demanding_activities(),
                                                              self.supplying_resources()):
            self.redistribute_the_means()

    def provide_resource_for(self, activity: smodel.ActivityModel) -> bool:
        assignable_resources, weights = self.weighed_resources_for_activity(activity)
        if len(assignable_resources) > 0:
            resource = weighed_permutation(assignable_resources, weights)[0]
            activity.use_resource(resource)
            return True
        else:
            return False

    def is_supplying(self, resource: smodel.ResourceModel) -> bool:
        return self.resource_supply[resource]
