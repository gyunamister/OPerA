from collections import Iterable
from ocpa.objects.log.obj import Event, Obj, ObjectCentricEventLog, MetaObjectCentricData, RawObjectCentricData
from ocpa.objects.log.importer.ocel.parameters import JsonParseParameters
from typing import TYPE_CHECKING, List, Dict

if TYPE_CHECKING:
    import sim.case


def create_oc_log(cases: Iterable[sim.case.OCCase]) -> ObjectCentricEventLog:
    events = {}
    objects = {}
    acts = set()
    attr_names = set()
    object_types = set()

    for case in cases:
        event_count = 0
        for case_event in case.events:
            add_event(events, event_count, case_event)
            event_count += 1
            add_obj(objects, case.objects)
            acts.add(case_event.activity)
            attr_names = attr_names | set(
                case_event.event_value_mapping.keys())
            object_types = object_types | set(
                case_event.event_object_mapping.keys())

    # attr_typ = {attr: name_type(str(df.dtypes[attr]))
    #             for attr in parameters["val_names"]}
    # attr_types = list(set(typ for typ in attr_typ.values()))
    act_attr = {act: attr_names for act in acts}
    meta = MetaObjectCentricData(
        attr_names=attr_names,
        attr_types=None,
        attr_typ=None,
        obj_types=object_types,
        act_attr=act_attr
    )
    raw = RawObjectCentricData(
        events=events,
        objects=objects
    )
    return ObjectCentricEventLog(meta, raw)


def add_event(events: Dict[str, Event], index, event) -> None:
    events[str(index)] = Event(id=str(index), act=event.activity, time=event.timestamp,
                               omap=event.event_object_mappin, vmap=event.event_value_mapping)


def add_obj(objects: Dict[str, Obj], objs: List[sim.case.OCObject]) -> None:
    for obj in objs:
        obj_id = obj.object_id  # First entry is the id
        obj_typ = obj.object_type  # second entry is the object type
        ovmap = obj.ovmap
        if obj_id not in objects:
            objects[obj_id] = Obj(id=obj_id, type=obj_typ, ovmap=ovmap)
