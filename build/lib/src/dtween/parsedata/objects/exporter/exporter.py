from typing import Dict, Union, List, Any

import pandas as pd
import itertools

from dtween.available.available import AvailableSelections
from dtween.available.constants import SITUATION_KEY, ANTI_KEY
from dtween.parsedata.objects.ocdata import Event, Obj
from pm4py.objects.log.log import EventLog
from pm4py.objects.log.util import dataframe_utils
from pm4py.objects.conversion.log import converter as log_converter

from dtween.parsedata.objects.oclog import ObjectCentricLog, Trace
from dtween.util.event_colors import get_color_to_events_assignment

TID_KEY = 'trace_id'
EVENTS_KEY = 'events'
EID_KEY = 'event_id'
ACT_KEY = 'activity'
TIMESTAMP_KEY = 'timestamp'
OBJECTS_KEY = 'objects'
VALUES_KEY = 'values'
COLOR_KEY = 'color'
CA_SCORE_KEY = 'cascore'
SCORE_KEY = 'score'
POSITIVE_KEY = 'positive'
NEGATIVE_KEY = 'negative'
RECOMMENDATION_KEY = 'recommendation'
PS_ALPHA_KEY = 'psalpha'
NG_ALPHA_KEY = 'ngalpha'


def export_trace_to_dict(trace: Trace, variant=True, detector=None, vmap_params=None, objects=None, threshold=None,
                         labels=None) -> Dict[str, Union[int, List[Dict[str, Any]]]]:
    color_assignment = get_color_to_events_assignment(
        [event.id for event in trace.events])
    if variant:
        return {TID_KEY: trace.id,
                EVENTS_KEY:
                    [{EID_KEY: event.id,
                      ACT_KEY: event.act,
                      TIMESTAMP_KEY: str(event.time),
                      OBJECTS_KEY: event.omap,
                      VALUES_KEY: event.vmap,
                      COLOR_KEY: color_assignment[event.id]} for event in trace.events]
                }
    else:
        round_n = 4
        label = labels[trace.id]
        return {TID_KEY: trace.id,
                EVENTS_KEY:
                    [{EID_KEY: event.id,
                      ACT_KEY: event.act,
                      TIMESTAMP_KEY: str(event.time),
                      OBJECTS_KEY: ','.join(
                          list({objects[oid].type for oid in event.omap})) if objects is not None else '',
                      VALUES_KEY: f'**Resource**: {event.vmap[vmap_params[AvailableSelections.RESOURCE]] if (AvailableSelections.RESOURCE in vmap_params and vmap_params[AvailableSelections.RESOURCE] in event.vmap) else "NA"} \n '
                                  f'**Location**: {event.vmap[vmap_params[AvailableSelections.LOCATION]] if (AvailableSelections.LOCATION in vmap_params and vmap_params[AvailableSelections.LOCATION] in event.vmap) else "NA"} \n',
                      COLOR_KEY: color_assignment[event.id]
                      }]
                }


def export_log_to_dict(log: ObjectCentricLog) -> List[Dict[str, Union[int, List[Dict[str, Any]]]]]:
    return [export_trace_to_dict(trace) for index, trace in log.traces.items()]


def export_logs_to_dict(logs: Dict[str, ObjectCentricLog]) -> Dict[str,
                                                                   List[Dict[str, Union[int, List[Dict[str, Any]]]]]]:
    return {name: [export_trace_to_dict(trace) for index, trace in log.traces.items()]
            for name, log in logs.items()}


def export_oc_data_events_to_dataframe(events: Dict[str, Event], objects: Dict[str, Obj], rows=None) -> pd.DataFrame:
    export_dicts, cols = export_events(
        objects, [events[eid] for eid in events], rows=rows)
    df = pd.DataFrame(export_dicts).T
    return df[cols]


def export_trace_to_dataframe(trace: Trace, log: ObjectCentricLog, result=False, detector=None) -> pd.DataFrame:
    export_dicts, cols = export_events(
        log.objects, trace.events, result, detector)
    df = pd.DataFrame(export_dicts).T
    return df[cols]


def export_events(objects, events, result=False, detector=None, rows=None):
    if not result:
        if rows is None:
            end_export = len(events)
        else:
            end_export = rows
        events_dict = {index:
                       {**{EID_KEY.title().replace("_", ""): event.id,
                        ACT_KEY.title(): event.act,
                        TIMESTAMP_KEY.title(): event.time},
                        **{ot.title() + ':Object':
                        ', '.join(
                            [obj for obj in event.omap if objects[obj].type == ot])
                           for ot in {objects[oid].type: 1 for oid in event.omap}},
                        **{value.title() + ':Value': event.vmap[value] for value in event.vmap}}
                       for index, event in enumerate(events) if index < end_export
                       }
        cols = list(events_dict[0].keys())
        return events_dict, cols
    else:
        ps = AvailableSituationType.POSITIVE
        ng = AvailableSituationType.NEGATIVE
        events_dict = {index:
                       {**{EID_KEY.title().replace("_", ""): event.id,
                        ACT_KEY.title(): event.act,
                        TIMESTAMP_KEY.title(): event.time,
                        POSITIVE_KEY.title(): event.complex_context[detector][ps],
                        NEGATIVE_KEY.title(): event.complex_context[detector][ng],
                           },
                        **{f'{sit.value.title()}-{sel.value.title()}:{typ.value.title()}':
                        f'*{event.rich_context[detector][typ][sit][sel][SITUATION_KEY]}'
                           if event.rich_context[detector][typ][sit][sel][ANTI_KEY] else
                           f'{event.rich_context[detector][typ][sit][sel][SITUATION_KEY]}'
                           for typ in event.rich_context[detector]
                           for sit in event.rich_context[detector][typ]
                           for sel in event.rich_context[detector][typ][sit]},
                        **{ot.title() + ':Object':
                        ', '.join(
                            [obj for obj in event.omap if objects[obj].type == ot])
                           for ot in {objects[oid].type: 1 for oid in event.omap}},
                        **{value.title() + ':Value': event.vmap[value] for value in event.vmap}}
                       for index, event in enumerate(events)
                       }
        cols = list(events_dict[0].keys())
        return events_dict, cols


def export_to_dataframe(log: ObjectCentricLog) -> pd.DataFrame:
    export_dicts = list(itertools.chain.from_iterable([[{TID_KEY.title(): trace.id,
                                                         ACT_KEY.title(): event.act,
                                                         TIMESTAMP_KEY.title(): event.time} for event in trace.events]
                                                       for index, trace in log.traces.items()]))
    export_dict = {'case:' + TID_KEY.title(): [d[TID_KEY.title()] for d in export_dicts],
                   'concept:name': [d[ACT_KEY.title()] for d in export_dicts],
                   TIMESTAMP_KEY.title(): [d[TIMESTAMP_KEY.title()] for d in export_dicts]
                   }
    return pd.DataFrame.from_dict(export_dict)


def export_to_pm4py(log: ObjectCentricLog) -> EventLog:
    log_df = export_to_dataframe(log)
    log_df = dataframe_utils.convert_timestamp_columns_in_df(log_df)
    log_df = log_df.sort_values(TIMESTAMP_KEY.title())
    parameters = {
        log_converter.Variants.TO_EVENT_LOG.value.Parameters.CASE_ID_KEY: 'case:' + TID_KEY.title()}
    return log_converter.apply(log_df, parameters=parameters)
