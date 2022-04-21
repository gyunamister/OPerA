import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Union

from dtween.available.available import AvailableSelections
from dtween.parsedata.config.param import CsvParseParameters, JsonParseParameters
from dtween.parsedata.objects.ocdata import Event, EventId, EventClassic, EventClassicResource, Obj, \
    MetaObjectCentricData


@dataclass
class Trace:
    events: List[Event]
    id: int = field(compare=False)


@dataclass
class TraceLightweight:
    events: List[EventId]
    id: int


@dataclass
class TraceClassic:
    events: List[EventClassic]
    id: int


@dataclass
class TraceClassicResource:
    events: List[EventClassicResource]
    id: int


@dataclass
class ObjectCentricLog:
    traces: Dict[int, Trace]
    event_to_traces: Dict[str, int]
    objects: Dict[str, Obj]
    meta: MetaObjectCentricData
    vmap_param: Union[CsvParseParameters, JsonParseParameters]


@dataclass
class LightweightLog:
    traces: Dict[int, TraceLightweight]


@dataclass
class ClassicLog:
    traces: Dict[int, TraceClassic]


@dataclass
class ClassicResourceLog:
    traces: Dict[int, TraceClassicResource]


def get_tid_filtered_log(log: ObjectCentricLog,
                         tids: List[int]) -> ObjectCentricLog:
    new_traces = {tid: log.traces[tid] for tid in log.traces if tid in tids}
    return ObjectCentricLog(traces=new_traces, event_to_traces=log.event_to_traces, objects=log.objects,
                            meta=log.meta, vmap_param=log.vmap_param)
