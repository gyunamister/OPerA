from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List
import numpy as np
import pm4py.util.xes_constants as xes_const
from pm4py.algo.conformance.alignments import algorithm as alignment_alg
from pm4py.objects.log.log import EventLog
from pm4py.objects.petri.align_utils import SKIP
from pm4py.objects.petri.petrinet import PetriNet

from queues.lifecycles import LifecycleAutomaton
from sim import time_utils
from sim.enums import Lifecycle, AvailableLifecycles
from sim.replay_tracking import DecisionTracker, \
    ArrivalTracker, TraceTracker
from sim.utils import AcceptingPetrinet


@dataclass
class ReplayResult:
    trace_tracker: TraceTracker
    arrival_tracker: ArrivalTracker
    decision_trackers: Dict[PetriNet.Place, DecisionTracker]
    decision_points: Dict[PetriNet.Place, List[PetriNet.Transition]]
    considered_case_fraction: float = None


def define_variant_cost(variant):
    return {i: 1 if lifecycle == 'complete' else 0 for i, (activity, lifecycle) in enumerate(variant)}


def in_nodes(n):
    for a in n.in_arcs:
        yield a.source


def out_nodes(n):
    for a in n.out_arcs:
        yield a.target


def get_start_activities(im):
    return set(t.label for p in im for t in out_nodes(p))


def first_sync_move_index(alignment):
    for i, ((t_label, t_name), (a_label, a_name)) in enumerate(alignment):
        if t_name != SKIP or a_label != SKIP:
            return i

def first_non_model_move_index(alignment):
    for i, ((t_label, t_name), (a_label, a_name)) in enumerate(alignment):
        if a_label != SKIP:
            return i

def replay_log(log: EventLog, petrinet_model: AcceptingPetrinet) -> ReplayResult:
    net, im, fm = petrinet_model.net, petrinet_model.im, petrinet_model.fm
    # variant extraction
    case_id_variant_map = {}
    variants = defaultdict(list)
    available_lifecycles = defaultdict(set)
    for i, trace in enumerate(log):
        case_id = trace.attributes[xes_const.DEFAULT_TRACEID_KEY]
        variant = []
        for event in trace:
            activity = event[xes_const.DEFAULT_NAME_KEY]
            lifecycle = event[xes_const.DEFAULT_TRANSITION_KEY]
            available_lifecycles[activity].add(lifecycle)
            variant.append((activity, lifecycle))
        tupled = tuple(variant)
        variants[tupled].append(i)
        case_id_variant_map[case_id] = tupled

    # filter only proper complete lifecycles
    # TODO ugly as hell
    toRemove = set()
    for variant in variants:
        lfas = defaultdict(lambda: LifecycleAutomaton())
        passes = all(lfas[activity].transition(lifecycle) for (activity, lifecycle) in variant) \
                 and all(lf.is_final_state() for lf in lfas.values())
        if not passes:
            toRemove.add(variant)

    # TODO make more explicit
    original_case_count = sum(len(idx) for idx in variants.values())
    # print('initial number of cases', original_case_count)
    for v in toRemove:
        del variants[v]
    lifecycle_filtered_case_count = sum(len(idx) for idx in variants.values())
    # print('remaining cases with proper lifecycles', lifecycle_filtered_case_count)

    available_lifecycles = {activity: (
        AvailableLifecycles.ScheduleStartComplete if {'schedule', 'start', 'complete'} <= cycles else (
            AvailableLifecycles.StartComplete) if {'start',
                                                   'complete'} <= cycles else AvailableLifecycles.CompleteOnly) for
        activity, cycles in available_lifecycles.items()}

    variant_alignments = {variant: alignment_alg.apply_trace(log[ids[0]], net, im, fm, parameters={
        alignment_alg.Parameters.PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE: True,
        alignment_alg.Parameters.PARAM_TRACE_COST_FUNCTION: define_variant_cost(variant)}) for variant, ids in
                          variants.items()}

    transition_map = {t.name: t for t in net.transitions}
    activity_transition_map = {t.label: t for t in net.transitions if t.label is not None}
    decision_points = {p: list(out_nodes(p)) for p in net.places if len(p.out_arcs) > 1}

    def execute_transition(t, i, m, tracking):
        for p in in_nodes(t):
            if p in decision_points:
                tracking[m[p]].append((p, t))
        j = max(m.pop(p) for p in in_nodes(t))
        if j < np.inf: # only track if it wasn't enabled by a model move
            if available_lifecycles[t.label] is AvailableLifecycles.CompleteOnly:
                tracking[j].append((t.label, Lifecycle.Enabled))
            tracking[i].append((t.label, Lifecycle.Completed))
        else:
            print('skipping', t, i, m)
        m.update({p: i for p in out_nodes(t)})

    def execute_silently(t, m, tracking):
        for p in in_nodes(t):
            if p in decision_points:
                tracking[m[p]].append((p, t))
        j = max(m.pop(p) for p in in_nodes(t))
        m.update({p: j for p in out_nodes(t)})

    def execute_model_move(t, m, tracking):
        for p in in_nodes(t):
            if p in decision_points:
                tracking[m[p]].append((p, t))
        for p in in_nodes(t):
            m.pop(p)
        m.update({p: np.inf for p in out_nodes(t)})

    def get_event_mappings(variant, alignment):
        trace_index = 0
        event_action_mapping = defaultdict(list)
        marking = {}
        for p in im:
            marking[p] = first_sync_move_index(alignment)

        for ((t_label, t_name), (a_label, a_name)) in alignment:
            if t_name == SKIP:
                # log moves are irrelevant on complete-only logs
                activity, lifecycle = variant[trace_index]
                enabled = trace_index
                if set(in_nodes(activity_transition_map[activity])) <= marking.keys():
                    j = max(marking[p] for p in in_nodes(activity_transition_map[activity]))
                    enabled = min(trace_index, j)
                if lifecycle == 'schedule':
                    event_action_mapping[enabled].append((activity, Lifecycle.Enabled))
                    event_action_mapping[trace_index].append((activity, Lifecycle.Scheduled))
                if lifecycle == 'start':
                    if available_lifecycles[activity] == AvailableLifecycles.StartComplete:
                        event_action_mapping[enabled].append((activity, Lifecycle.Enabled))
                    event_action_mapping[trace_index].append((activity, Lifecycle.Started))
                trace_index += 1
            elif a_label == SKIP:
                # model move
                if t_label is None or t_label == SKIP:  # or contains tau?
                    # silent move
                    t = transition_map[t_name]
                    execute_silently(t, marking, event_action_mapping)
                else:
                    t = transition_map[t_name]
                    execute_model_move(t, marking, event_action_mapping)
                    # model
                    # cannot occur because 0 cost
            else:
                # sync
                t = transition_map[t_name]
                execute_transition(t, trace_index, marking, event_action_mapping)
                trace_index += 1
        return event_action_mapping

    variant_event_mappings = {}
    for variant, alignment in variant_alignments.items():
        if alignment['cost'] == 0:
            variant_event_mappings[variant] = get_event_mappings(variant, alignment['alignment'])

    alignment_filtered_case_count = sum(len(variants[v]) for v in variant_event_mappings)
    # print('remaining cases with 0 alignment cost', alignment_filtered_case_count) TODO take a look here as well

    arrival_tracker = ArrivalTracker()
    trace_tracker = TraceTracker(available_lifecycles)
    decision_trackers = {}
    for p, options in decision_points.items():
        tracker = DecisionTracker()
        tracker.options = options
        decision_trackers[p] = tracker

    for trace in log:
        case_id = trace.attributes[xes_const.DEFAULT_TRACEID_KEY]
        variant = case_id_variant_map[case_id]

        if len(trace) == 0 or variant not in variant_event_mappings:
            continue

        event_mapping = variant_event_mappings[variant]

        arrival_tracked = False
        for i, event in enumerate(trace):
            time = time_utils.get_event_timestamp(event)

            for (key, payload) in event_mapping.get(i, []):
                if key in decision_trackers:
                    tracker = decision_trackers[key]
                    tracker.track(case_id, time, payload)
                else:
                    if not arrival_tracked:
                        arrival_tracker.track(time, trace.attributes)
                        arrival_tracked = True
                    trace_tracker.track(case_id, key, payload, event)

    return ReplayResult(trace_tracker, arrival_tracker, decision_trackers, decision_points,
                        considered_case_fraction=(alignment_filtered_case_count / original_case_count))
