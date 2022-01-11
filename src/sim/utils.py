from __future__ import annotations

import collections
import random
from collections import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict

import numpy as np
from pm4py.objects.log.log import EventLog, Trace, Event
from pm4py.objects.petri.petrinet import PetriNet, Marking
from ocpa.objects.log.obj import Event, Obj, ObjectCentricEventLog, MetaObjectCentricData, RawObjectCentricData
from ocpa.objects.log.importer.ocel.parameters import JsonParseParameters
from pm4py.util import xes_constants

if TYPE_CHECKING:
    import sim.case


class PathConstants:
    base_event_log_path = str(
        Path(__file__).resolve().parent.joinpath('event_logs'))
    base_petrinet_path = str(
        Path(__file__).resolve().parent.joinpath('petrinets'))
    base_simulation_log_path = str(
        Path(__file__).resolve().parent.joinpath('simulation_logs'))


def auto_str(cls):
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join(f'{k}={v}' for k, v in vars(
                self).items() if v is not None)
        )

    cls.__str__ = __str__
    return cls


class StaticHashable:

    def __init__(self, hash_obj, **kwargs) -> None:
        super(StaticHashable, self).__init__(**kwargs)
        self.hash = hash(hash_obj)

    def __hash__(self) -> int:
        return self.hash

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self.__class__) and self.hash == o.hash


class FrozenDict(collections.Mapping):

    def __init__(self, *args, **kwargs):
        self._d = dict(*args, **kwargs)
        self._hash = None

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(tuple(sorted(self._d.items())))
        return self._hash

    def __str__(self):
        return str(self._d)

    def __repr__(self) -> str:
        return repr(self._d)


def permuted(seq):
    ret = list(seq)
    random.shuffle(ret)
    return ret


def weighed_permutation(elements, weights):
    length = len(elements)
    shuffled_indices = np.random.choice(
        np.arange(length), size=(length,), replace=False, p=weights)
    return [elements[i] for i in shuffled_indices]


class DataframeEventLogKeys:
    case_id = 'case:concept:name'
    time = 'time:timestamp'
    activity = 'concept:name'
    lifecycle = 'lifecycle:transition'


def create_log(cases: Iterable[sim.case.OCCase]) -> EventLog:
    log = EventLog()
    log.attributes[xes_constants.DEFAULT_NAME_KEY] = 'simulated log'

    for case in cases:

        trace = Trace()
        trace.attributes[xes_constants.DEFAULT_TRACEID_KEY] = case.case_id

        for case_event in case:
            event = Event()

            event[xes_constants.DEFAULT_NAME_KEY] = case_event.activity
            event[xes_constants.DEFAULT_TIMESTAMP_KEY] = case_event.timestamp
            event[xes_constants.DEFAULT_RESOURCE_KEY] = case_event.resource
            event[xes_constants.DEFAULT_TRANSITION_KEY] = case_event.lifecycle
            for attr_name in case_event.attributes:
                event[attr_name] = case_event.attributes[attr_name]

            trace.append(event)

        log.append(trace)

    return log


def create_oc_log(cases: Iterable[sim.case.OCCase]) -> ObjectCentricEventLog:
    events = {}
    objects = {}
    # acts = set()
    attr_names = set()
    object_types = set()

    event_count = 0
    for case in cases:
        for case_event in case.events:
            add_event(events, event_count, case_event)
            event_count += 1
            add_obj(objects, case.objects)
            # acts.add(case_event.activity)
            event_attr_names = [attr for oid in case_event.event_value_mapping.keys(
            ) for attr in case_event.event_value_mapping[oid].keys()]
            attr_names = attr_names | set(
                event_attr_names)
            object_types = object_types | set(
                case_event.event_object_mapping.keys())

    # attr_typ = {attr: name_type(str(df.dtypes[attr]))
    #             for attr in parameters["val_names"]}
    # attr_types = list(set(typ for typ in attr_typ.values()))
    # act_attr = {act: attr_names for act in acts}
    meta = MetaObjectCentricData(
        attr_names=list(attr_names),
        attr_types=None,
        attr_typ=None,
        obj_types=list(object_types),
        act_attr=None
    )
    raw = RawObjectCentricData(
        events=events,
        objects=objects
    )
    return ObjectCentricEventLog(meta, raw)


def add_event(events: Dict[str, Event], index, event) -> None:
    events[str(index)] = Event(id=str(index), act=event.activity, time=event.timestamp,
                               omap=[obj for objs in event.event_object_mapping.values() for obj in objs], vmap=dict(event.event_value_mapping))


def add_obj(objects: Dict[str, Obj], objs: List[sim.case.OCObject]) -> None:
    for obj in objs:
        obj_id = obj.object_id  # First entry is the id
        obj_typ = obj.object_type  # second entry is the object type
        ovmap = obj.ovmap
        if obj_id not in objects:
            objects[obj_id] = Obj(id=obj_id, type=obj_typ, ovmap=dict(ovmap))


@dataclass
class AcceptingPetrinet:
    net: PetriNet
    im: Marking
    fm: Marking
