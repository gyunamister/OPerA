from __future__ import annotations

import numbers
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Set, Tuple

import numpy
from pm4py.objects.petri.petrinet import PetriNet

import sim.parameter_extraction as pe
import sim.sim_graph as sgraph
import sim.simple_parameter_extraction as spe
import sim.time_utils
from sim.model_parameters import InterArrivalSampler, BusinessHours, QueueingDiscipline, ProcessingTimeSampler, \
    DelaySampler, ResourcePerformance, CaseClassifier, ValueSampler, BusinessRules
from sim.replay_tracking import ActivityTracker, DecisionTracker, ResourcePool, ArrivalTracker
from sim.utils import auto_str, AcceptingPetrinet


def create_sim_graph(acc_petrinet: AcceptingPetrinet,
                     decision_points: Dict[PetriNet.Place, List[PetriNet.Transition]] = None) -> sgraph.SimulationGraph:
    net, im, fm = acc_petrinet.net, acc_petrinet.im, acc_petrinet.fm
    assert len(im) == len(fm) == 1

    im_place = next(iter(im))
    fm_place = next(iter(fm))

    activity_map = {}

    t_map = {}
    for t in net.transitions:
        if t.label is None:
            n = sgraph.TauNode()
        else:
            n = sgraph.ActivityNode(t.label)
            activity_map[t.label] = n
        in_node = out_node = n
        if len(t.in_arcs) > 1:
            and_join = sgraph.AndJoin(parallel_splits=len(t.in_arcs))
            and_join.successor = n
            in_node = and_join
        if len(t.out_arcs) > 1:
            and_split = sgraph.AndSplit()
            n.successor = and_split
            out_node = and_split
        t_map[t] = (in_node, out_node)

    taus = []

    p_map = {}
    for p in net.places:
        in_node = out_node = None
        if len(p.in_arcs) > 1:
            in_node = sgraph.XorJoin()
        elif len(p.in_arcs) == 0:
            assert p in im
            in_node = sgraph.ArrivalNode()
        if len(p.out_arcs) > 1:
            out_node = sgraph.XorSplit()
        elif len(p.out_arcs) == 0:
            assert p in fm
            out_node = sgraph.TerminalNode()

        if in_node is not None and out_node is not None:
            in_node.successor = out_node
        elif in_node is not None:
            out_node = in_node
        elif out_node is not None:
            in_node = out_node
        else:
            in_node = out_node = sgraph.TauNode()
            taus.append(in_node)

        p_map[p] = (in_node, out_node)

    decision_point_map = {}

    for p, (in_node, out_node) in p_map.items():
        # for preserving order at all costs
        if decision_points is not None and p in decision_points:
            post_ins = [t_map[t][0] for t in decision_points[p]]
        else:
            post_ins = [t_map[a.target][0] for a in p.out_arcs]
        if len(post_ins) > 1:
            out_node.successors = post_ins
            decision_point_map[p.name] = out_node
        elif len(post_ins) == 1:
            out_node.successor = post_ins[0]

    for t, (in_node, out_node) in t_map.items():
        post_ins = [p_map[a.target][0] for a in t.out_arcs]
        if len(post_ins) > 1:
            out_node.successors = post_ins
        else:
            out_node.successor = post_ins[0]

    for t, (in_node, out_node) in t_map.items():
        if isinstance(out_node, sgraph.LinearNode) and isinstance(out_node.successor, sgraph.TauNode):
            out_node.successor = out_node.successor.successor
        if isinstance(out_node, sgraph.SplittingNode):
            new = [post_node.successor if isinstance(post_node, sgraph.TauNode) else post_node for post_node in
                   out_node.successors]
            out_node.successors = new

    return sgraph.SimulationGraph(p_map[im_place][0], p_map[fm_place][1], activity_map, decision_point_map)


@dataclass(unsafe_hash=True)
class ModelConfiguration:
    arrivals: Dict[str, ArrivalProcessConfig]
    activities: Dict[str, ActivityConfig]
    resources: Dict[str, ResourceConfig]
    decisions: Dict[str, DecisionConfig]
    mapping: MappingConfig
    objects: ObjectConfig = None

    def __str__(self) -> str:
        return 'Arrivals:' + ('\n' if len(self.arrivals) > 0 else ' n/a') \
               + '\n'.join(str(l) + ': ' + str(ar) for l, ar in self.arrivals.items()) + '\n' \
               + 'Activities:' + ('\n' if len(self.activities) > 0 else ' n/a') \
               + '\n'.join(str(a) + ': ' + str(ac) for a, ac in self.activities.items()) + '\n' \
               + 'Resources:' + ('\n' if len(self.resources) > 0 else ' n/a') \
               + '\n'.join(str(r) + ': ' + str(rc) for r, rc in self.resources.items()) + '\n' \
               + 'Decision Points:' + ('\n' if len(self.decisions) > 0 else ' n/a') \
               + '\n'.join(str(d) + ': ' + str(dec) for d, dec in self.decisions.items()) + '\n' \
               + str(self.mapping) + '\n' + str(self.objects)


def create_simplified_model_configuration(df, quantile_dicts, hyper_parameters,
                                          replay_result) -> ModelConfiguration:
    a_hyper, r_hyper = hyper_parameters.activity_hyper, hyper_parameters.resource_hyper
    activity_total_duration_quantile_dict, resource_concurrent_quantile_dict = quantile_dicts

    arrival_bh = pe.arrival_business_hours(replay_result.arrival_tracker)
    first, last = pe.arrival_span(replay_result.arrival_tracker)
    ias = spe.arrival_sampler(replay_result.arrival_tracker.arrival_history_df)

    activities = {}
    for a, step in a_hyper.items():
        disc = spe.queueing_discipline()
        pt = spe.processing_time_sampler(
            activity_total_duration_quantile_dict[a][step])
        activities[a] = ActivityConfig(
            queueing_discipline=disc, processing_time_sampler=pt)
    decisions = {}
    for p, tracker in replay_result.decision_trackers.items():
        dc = pe.decision_classifier(tracker)
        decisions[p.name] = DecisionConfig(classifier=dc)
    resources = {}
    for r, step in r_hyper.items():
        cap = spe.resource_capacity(resource_concurrent_quantile_dict[r][step])
        res_bh = spe.resource_business_hours(df, r)
        resources[r] = ResourceConfig(capacity=cap, business_hours=res_bh)

    ar_mapping: Dict[str, Set[str]] = spe.activity_resource_mapping(df)
    ar_prop: Dict[str, Dict[str, float]
                  ] = spe.activity_resource_propensities(df)

    return ModelConfiguration(
        arrivals={'default': ArrivalProcessConfig(first_arrival=first, last_arrival=last, inter_arrivals=ias,
                                                  business_hours=arrival_bh)},
        activities=activities,
        resources=resources,
        decisions=decisions,
        mapping=MappingConfig(assignable_resources=ar_mapping, propensities=ar_prop))


def create_model_configuration(activity_trackers: Dict[str, ActivityTracker],
                               decision_trackers: Dict[PetriNet.Place, DecisionTracker],
                               arrival_tracker: ArrivalTracker,
                               resource_pool: ResourcePool) -> ModelConfiguration:
    arrival_bh = pe.arrival_business_hours(arrival_tracker)
    ias = pe.inter_arrival_time_sampler(arrival_tracker)
    first, last = pe.arrival_span(arrival_tracker)
    activities = {}
    for a, tracker in activity_trackers.items():
        disc = pe.queueing_discipline(tracker.queue_model)
        bh = pe.queue_business_hours(tracker.queue_model)
        pt = pe.processing_time_sampler(tracker.processing_model)
        activities[a] = ActivityConfig(
            queueing_discipline=disc, processing_time_sampler=pt, business_hours=bh)
    decisions = {}
    for p, tracker in decision_trackers.items():
        dc = pe.decision_classifier(tracker)
        decisions[p.name] = DecisionConfig(dc)
    resources = {}
    cap = pe.resource_capacities(resource_pool)
    res_bh = pe.resource_business_hours(resource_pool)
    for r in cap.keys():
        resources[r] = ResourceConfig(
            capacity=cap[r], business_hours=res_bh[r])

    ar_mapping: Dict[str, Set[str]
                     ] = pe.activity_resource_mapping(resource_pool)
    ar_prop: Dict[str, Dict[str, float]
                  ] = pe.activity_resource_propensities(resource_pool)

    return ModelConfiguration(
        arrivals={'default': ArrivalProcessConfig(first_arrival=first, last_arrival=last, inter_arrivals=ias,
                                                  business_hours=arrival_bh)},
        activities=activities,
        resources=resources,
        decisions=decisions,
        mapping=MappingConfig(assignable_resources=ar_mapping, propensities=ar_prop))


@auto_str
@dataclass(unsafe_hash=True)
class ArrivalProcessConfig:
    first_arrival: datetime
    inter_arrivals: InterArrivalSampler
    business_hours: BusinessHours = None
    last_arrival: datetime = None

    def __init__(self, first_arrival: datetime, inter_arrivals: InterArrivalSampler,
                 business_hours: BusinessHours = None, last_arrival: datetime = None) -> None:
        self.first_arrival = sim.time_utils.make_timezone_aware(first_arrival)
        self.inter_arrivals = inter_arrivals
        self.business_hours = business_hours
        self.last_arrival = sim.time_utils.make_timezone_aware(
            last_arrival) if last_arrival is not None else None


@auto_str
@dataclass(unsafe_hash=True)
class ActivityConfig:
    queueing_discipline: QueueingDiscipline
    processing_time_sampler: ProcessingTimeSampler
    business_hours: BusinessHours = None
    delay_sampler: DelaySampler = None
    object_type: Dict[str, Dict[str, ValueSampler]] = None
    business_rules: BusinessRules = None

    def __init__(self, queueing_discipline: QueueingDiscipline, processing_time_sampler: ProcessingTimeSampler,
                 business_hours: BusinessHours = None, delay_sampler: DelaySampler = None, object_type: List[str] = None, business_rules: BusinessRules = None) -> None:
        self.queueing_discipline = queueing_discipline
        self.processing_time_sampler = processing_time_sampler
        self.delay_sampler = delay_sampler
        self.business_hours = business_hours
        self.object_type = object_type
        self.business_rules = business_rules


@auto_str
@dataclass(unsafe_hash=True)
class ObjectConfig:
    specs: Dict[str, Tuple[int, int]]

    def __init__(self, specs: Dict[str, Tuple[int, int]]) -> None:
        self.specs = specs


@auto_str
@dataclass(unsafe_hash=True)
class ResourceConfig:
    capacity: numbers.Number
    business_hours: BusinessHours = None
    performance: ResourcePerformance = None

    def __init__(self, capacity: numbers.Number, business_hours: BusinessHours = None,
                 performance: ResourcePerformance = None) -> None:
        self.capacity = capacity
        self.business_hours = business_hours
        self.performance = performance


@auto_str
@dataclass(unsafe_hash=True)
class DecisionConfig:
    classifier: CaseClassifier

    def __init__(self, classifier: CaseClassifier) -> None:
        self.classifier = classifier


@auto_str
@dataclass(unsafe_hash=True)
class MappingConfig:
    assignable_resources: Dict[str, Set[str]]
    propensities: Dict[str, Dict[str, float]] = None

    def __init__(self, assignable_resources: Dict[str, Set[str]],
                 propensities: Dict[str, Dict[str, float]] = None) -> None:
        self.assignable_resources = assignable_resources
        self.propensities = propensities


InfiniteResourceConfig = ResourceConfig(numpy.inf)
