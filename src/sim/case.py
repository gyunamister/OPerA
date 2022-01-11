from __future__ import annotations

import datetime
from collections import Sequence
from dataclasses import dataclass, field
from typing import Callable, Any, List, Iterator, Dict
import copy

import sim.utils


@dataclass(unsafe_hash=True)
class OCCaseEvent:
    activity: str
    resource: str
    timestamp: datetime.datetime
    lifecycle: str = 'complete'
    event_value_mapping: sim.utils.FrozenDict[str, Any] = field(
        default_factory=sim.utils.FrozenDict)
    event_object_mapping: sim.utils.FrozenDict[str, Any] = field(
        default_factory=sim.utils.FrozenDict)

    def __init__(self, activity: str, resource: str, time: datetime.datetime, lifecycle: str = 'complete', event_value_mapping: Dict[str, Dict[str, object]] = sim.utils.FrozenDict(), event_object_mapping: Dict[str, List[str]] = sim.utils.FrozenDict(), **attributes) -> None:
        self.activity = activity
        self.resource = resource
        self.timestamp = time
        self.lifecycle = lifecycle
        self.event_value_mapping = sim.utils.FrozenDict(event_value_mapping)
        self.event_object_mapping = sim.utils.FrozenDict(event_object_mapping)

    def __str__(self) -> str:
        return f'{self.activity}[{self.lifecycle}] @{self.timestamp.strftime("%Y-%m-%d %H:%M")} by {self.resource}]'


@ dataclass()
class OCObject:
    object_type: str
    object_id = str
    ovmap: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, object_type: str, object_id: str, ovmap: Dict[str, Any] = dict()) -> None:
        self.object_type = object_type
        self.object_id = object_id
        self.ovmap = ovmap

    def __str__(self) -> str:
        return f'{self.object_type} {self.object_id} {self.ovmap}'

    def __repr__(self) -> str:
        return f'{self.object_type}: {self.object_id} {self.ovmap}'

# TODO StaticHashable usage, see sim_model


class OCCase(Sequence):

    def __init__(self, case_id: str, objects: List[OCObject], events: List[OCCaseEvent] = None, **case_attributes):
        super(OCCase, self).__init__()  # hash_obj=case_id)
        self.case_id = case_id
        self.objects = objects
        self.attributes = case_attributes
        self.events = events if events else []

    def __getitem__(self, i: int) -> OCCaseEvent:
        return self.events[i]

    def index(self, x: Any, start: int = ..., end: int = ...) -> int:
        return self.events.index(x, start, end)

    def count(self, x: Any) -> int:
        return self.events.count(x)

    def __contains__(self, x: object) -> bool:
        return x in self.events

    def __iter__(self) -> Iterator[OCCaseEvent]:
        return iter(self.events)

    def __reversed__(self) -> Iterator[OCCaseEvent]:
        return reversed(self.events)

    def __len__(self) -> int:
        return len(self.events)

    def add_event(self, event: OCCaseEvent) -> None:
        self.events.append(event)

    def project(self, condition: Callable[[OCCaseEvent], bool] = lambda ce: ce.lifecycle == 'complete',
                projection: Callable[[OCCaseEvent], Any] = lambda ce: ce.activity):
        projection = projection if projection else lambda ce: ce
        condition = condition if condition else lambda ce: True
        return OCCase(self.case_id, self.objects, [projection(event) for event in self.events if condition(event)], **self.attributes)

    def filter(self, condition: Callable[[OCCaseEvent], bool]):
        return OCCase(self.case_id, self.objects, [event for event in self.events if condition(event)], **self.attributes)

    def temp_filter(self, condition: Callable[[OCCaseEvent], bool]):
        for event in self.events:
            print(event.lifecycle)
            if condition(event):
                print("okay")
            else:
                print("not okay")
        # return OCCase(self.case_id, [event for event in self.events if condition(event)], **self.attributes)

    def get_object_mapping(self, chosen_obj_types: List[str]):
        obj_mapping = dict()
        for obj in self.objects:
            if obj.object_type not in chosen_obj_types:
                continue
            if obj.object_type in obj_mapping:
                obj_mapping[obj.object_type].append(obj.object_id)
            else:
                obj_mapping[obj.object_type] = [obj.object_id]
        return obj_mapping

    def get_object(self, object_id):
        for obj in self.objects:
            if obj.object_id == object_id:
                return obj
        return None

    def update_object_value_mapping(self, vmap: Dict[str, Dict[str, object]]):
        if len(vmap) == 0:
            return
        # objects = []
        for obj in self.objects:
            new_ovmap = {}
            for old_attr in obj.ovmap:
                new_ovmap[old_attr] = obj.ovmap[old_attr]
            for oid in vmap:
                if obj.object_id == oid:
                    for attr in vmap[oid]:
                        new_ovmap[attr] = vmap[oid][attr]
            obj.ovmap = new_ovmap
            # objects.append(obj)
        # return objects

    def __str__(self) -> str:
        return f'OCCase {self.case_id}: ' + ','.join(map(str, self.events))
