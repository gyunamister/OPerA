import itertools
from typing import Dict

from dtween.available.available import AvailableCorrelations
from dtween.parsedata.objects.ocdata import ObjectCentricData, Event
from dtween.parsedata.objects.oclog import Trace, ObjectCentricLog


# TODO: P1 only outputs lightweight log with traces of EventIds
# TODO: P3 remove code duplication
# TODO: P2 create unit tests for this function
# TODO: P1 get corr out of event and put it into a [bool] of size events (copy)
# TODO: P4 check whether set is faster than list for the object map intersection test
def correlate_obj_path(data: ObjectCentricData, selection: set) -> Dict[str, ObjectCentricLog]:
    events = data.raw.events
    objects = data.raw.objects
    logs = {}  # TODO: different
    ordered_selections = itertools.permutations(selection)  # TODO: different
    key_list = list(events.keys())

    for ordered_selection in ordered_selections:  # TODO: different
        tid = 0
        pos = 0
        start_event = events[key_list[pos]]
        corr = start_event.corr
        all_correlated = False
        log = ObjectCentricLog({}, {}, objects, data.meta, data.vmap_param)
        pos_selection = 0  # Current position on ordered selection # TODO: different
        event_to_trace = {}

        while not all_correlated:

            while True:
                if len(events) - 1 == pos:  # finished
                    all_correlated = True
                    break
                if start_event.corr is not corr:  # already correlated events are not correlated again
                    pos += 1
                    start_event = events[key_list[pos]]
                elif len(get_obj_ids(start_event, objects,
                                     {ordered_selection[
                                         pos_selection]})) == 0:  # events with no matching object type are skipped
                    start_event.corr = not corr  # Mark as "correlated"
                    pos += 1
                    start_event = events[key_list[pos]]
                else:
                    break
            if all_correlated:
                break
            obj_ids = get_obj_ids(start_event, objects, selection)
            trace = Trace(events=[start_event],
                          id=tid)
            event_to_trace[start_event.id] = trace.id
            tid += 1
            start_event.corr = not corr
            # If the first event of a trace is the last in events, then we are done
            if len(events) - 1 == pos:
                log.traces[trace.id] = trace
                all_correlated = True
                break
            pos += 1
            pos_trace = pos
            # We search the rest of events for more events correlated to the first event of the new trace
            next_event = events[key_list[pos_trace]]
            while True:
                if next_event.corr is not corr:
                    pass
                # Correlated events share objects ids of the correct type
                elif not set(next_event.omap).isdisjoint(obj_ids):
                    trace.events.append(next_event)
                    event_to_trace[next_event.id] = trace.id
                    next_event.corr = not corr
                    pos_selection += 1  # TODO different

                    if pos_selection == len(ordered_selection):  # TODO different
                        break  # TODO different
                    # the current event's object id's for the correct type need to be shared by the next event
                    obj_ids = get_obj_ids(next_event, objects, {
                                          ordered_selection[pos_selection]})  # TODO different
                if len(events) - 1 == pos_trace:  # All events were searched for that trac
                    break
                pos_trace += 1
                next_event = events[key_list[pos_trace]]
            # Add trace to log and remove already correlated events
            log.traces[trace.id] = trace
            log.event_to_traces = event_to_trace
            pos_selection = 0
        logs[str(ordered_selection)] = log

    return logs


# TODO: create unit tests for this function
def correlate_shared_objs(data: ObjectCentricData,
                          selection: set,
                          version=AvailableCorrelations.MAXIMUM_CORRELATION) -> ObjectCentricLog:
    events = data.raw.events
    objects = data.raw.objects
    log = ObjectCentricLog({}, {}, objects, data.meta, data.vmap_param)

    tid = 0
    pos = 0
    key_list = list(events.keys())
    start_event = events[key_list[pos]]
    corr = start_event.corr
    all_correlated = False
    event_to_trace = {}
    # Correlate while uncorrelated events exist
    while not all_correlated:
        # The first event with correct object is always the start event
        # Assume events to be sorted according to total order
        while True:
            if len(events) - 1 == pos:  # finished
                all_correlated = True
                break
            if start_event.corr is not corr:  # already correlated events are not correlated again
                pos += 1
                start_event = events[key_list[pos]]
            elif len(get_obj_ids(start_event, objects,
                                 selection)) == 0:  # events with no matching object type are skipped
                start_event.corr = not corr  # Mark as "correlated"
                pos += 1
                start_event = events[key_list[pos]]
            else:
                break
        if all_correlated:
            break
        obj_ids = get_obj_ids(start_event, objects, selection)
        trace = Trace(events=[start_event],
                      id=tid)
        event_to_trace[start_event.id] = trace.id
        tid += 1
        start_event.corr = not corr
        if len(events) - 1 == pos:  # If the first event of a trace is the last in events, then we are done
            log.traces[trace.id] = trace
            all_correlated = True
            break
        #pos += 1
        pos_trace = pos  # We search the rest of events for more events correlated to the first event of the new trace
        next_event = events[key_list[pos_trace]]
        while True:
            if next_event.corr is not corr:  # Already correlated events cannot be correlated again
                pass
            elif not set(next_event.omap).isdisjoint(
                    obj_ids):  # Correlated events share objects ids of the correct type
                trace.events.append(next_event)
                event_to_trace[next_event.id] = trace.id
                next_event.corr = not corr
                if version == AvailableCorrelations.MAXIMUM_CORRELATION:
                    obj_ids.update({obj for obj in next_event.omap if
                                    data.raw.objects[obj].type in selection})
            if len(events) - 1 == pos_trace:
                break
            pos_trace += 1
            next_event = events[key_list[pos_trace]]

        # Add trace to log and remove already correlated events
        log.traces[trace.id] = trace
    log.event_to_traces = event_to_trace
    return log


def get_obj_ids(event: Event, objects: dict, selection: set) -> set:
    return {obj for obj in event.omap if
            objects[obj].type in selection
            }
