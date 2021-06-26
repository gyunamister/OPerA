import logging
import dask.dataframe as ddf
import itertools
from pandas import to_datetime
from datetime import datetime
from typing import List, Dict, Any

from dtween.parsedata.objects.ocdata import Event, Obj, \
    ObjectCentricData, MetaObjectCentricData, RawObjectCentricData
from dtween.parsedata.config.param import JsonParseParameters, CsvParseParameters

logger = logging.getLogger('dtweenLogger')

counter = itertools.count()


def parse_csv(df: ddf.DataFrame, cfg: CsvParseParameters) -> ObjectCentricData:
    events = {}
    objects = {}
    acts = set()
    print(df)
    for index, row in df.iterrows():
        add_event(events, index, row, cfg),
        add_obj(objects,
                # Only nonempty sets of objects ids per object type
                list(itertools.chain.from_iterable(
                    [[obj_id + '/' + str(obj) for i, obj_id in enumerate(safe_split(row[obj]))]
                     for obj in cfg.obj_names if row[obj] != '{}']
                ))
                ),
        acts.add(row[cfg.act_name])

    attr_typ = {attr: name_type(str(df.dtypes[attr]))
                for attr in cfg.val_names}
    attr_types = list(set(typ for typ in attr_typ.values()))
    act_attr = {act: cfg.val_names for act in acts}
    meta = MetaObjectCentricData(
        attr_names=cfg.val_names,
        attr_types=attr_types,
        attr_typ=attr_typ,
        obj_types=cfg.obj_names,
        act_attr=act_attr
    )
    raw = RawObjectCentricData(
        events=events,
        objects=objects
    )
    return ObjectCentricData(meta, raw, cfg)


def name_type(typ: str) -> str:
    if typ == 'object':
        return 'string'
    else:
        return typ


def safe_split(row_obj):
    try:
        if '{' in row_obj:
            row_obj[1:-1].split(',')
        else:
            return row_obj.split(',')
    except TypeError:
        return []  # f'NA-{next(counter)}'


def add_event(events: Dict[str, Event], index, row, cfg) -> None:
    events[str(index)] = Event(
        id=str(index),
        act=row[cfg.act_name],
        time=to_datetime(row[cfg.time_name]),
        omap=list(itertools.chain.from_iterable(
            [safe_split(row[obj])
             for obj in cfg.obj_names if row[obj] != '{}']
        )),
        vmap={attr: row[attr] for attr in cfg.val_names})


def add_obj(objects: Dict[str, Obj], objs: List[str]) -> None:
    for obj_id_typ in objs:
        obj_id_typ = obj_id_typ.split('/')  # Unpack
        obj_id = obj_id_typ[0]  # First entry is the id
        obj_typ = obj_id_typ[1]  # second entry is the object type
        if obj_id not in objects:
            objects[obj_id] = Obj(id=obj_id, type=obj_typ, ovmap={})


def parse_json(data: Dict[str, Any], cfg: JsonParseParameters) -> ObjectCentricData:
    # parses the given dict
    events = parse_events(data[cfg.log_params['events']], cfg)
    objects = parse_objects(data[cfg.log_params['objects']], cfg)
    # Uses the last found value type
    attr_events = {v:
                   str(type(events[eid].vmap[v])) for eid in events
                   for v in events[eid].vmap}
    attr_objects = {v:
                    str(type(objects[oid].ovmap[v])) for oid in objects
                    for v in objects[oid].ovmap
                    }
    attr_types = list({attr_events[v] for v in attr_events}.union(
        {attr_objects[v] for v in attr_objects}))
    attr_typ = {**attr_events, **attr_objects}
    act_attr = {}
    for eid, event in events.items():
        act = event.act
        if act not in act_attr:
            act_attr[act] = {v for v in event.vmap}
        else:
            act_attr[act] = act_attr[act].union({v for v in event.vmap})
    for act in act_attr:
        act_attr[act] = list(act_attr[act])
    meta = MetaObjectCentricData(attr_names=data[cfg.log_params['meta']][cfg.log_params['attr_names']],
                                 obj_types=data[cfg.log_params['meta']
                                                ][cfg.log_params['obj_types']],
                                 attr_types=attr_types,
                                 attr_typ=attr_typ,
                                 act_attr=act_attr,
                                 attr_events=list(attr_events.keys()))
    data = ObjectCentricData(meta, RawObjectCentricData(events, objects), cfg)
    return data


def parse_events(data: Dict[str, Any], cfg: JsonParseParameters) -> Dict[str, Event]:
    # Transform events dict to list of events
    act_name = cfg.event_params['act']
    omap_name = cfg.event_params['omap']
    vmap_name = cfg.event_params['vmap']
    time_name = cfg.event_params['time']
    events = {item[0]: Event(id=item[0],
                             act=item[1][act_name],
                             omap=item[1][omap_name],
                             vmap=item[1][vmap_name],
                             time=datetime.fromisoformat(item[1][time_name]))
              for item in data.items()}
    return events


def parse_objects(data: Dict[str, Any], cfg: JsonParseParameters) -> Dict[str, Obj]:
    # Transform objects dict to list of objects
    type_name = cfg.obj_params['type']
    ovmap_name = cfg.obj_params['ovmap']
    objects = {item[0]: Obj(id=item[0],
                            type=item[1][type_name],
                            ovmap=item[1][ovmap_name])
               for item in data.items()}
    return objects
