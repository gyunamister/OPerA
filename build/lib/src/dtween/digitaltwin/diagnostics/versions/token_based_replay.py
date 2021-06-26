import pm4py
# from pm4pymdl.algo.mvp.utils import succint_mdl_to_exploded_mdl, clean_frequency, clean_arc_frequency
from ocpa.objects.log.importer.mdl.factory import succint_mdl_to_exploded_mdl, clean_frequency, clean_arc_frequency
from dtween.digitaltwin.mvp.projection import algorithm
from pm4py.algo.discovery.alpha import algorithm as alpha_miner
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.statistics.start_activities.log import get as sa_get
from pm4py.statistics.end_activities.log import get as ea_get
from pm4py.objects.conversion.dfg import converter as dfg_converter
from pm4py.algo.conformance.tokenreplay import algorithm as tr_factory
from pm4py.visualization.petrinet.util import performance_map
from pm4py.statistics.variants.log import get as variants_module
from pm4py.algo.filtering.log.paths import paths_filter
from pm4py.algo.filtering.log.variants import variants_filter
from pm4py.algo.filtering.log.attributes import attributes_filter
from pm4py.objects.petri.petrinet import PetriNet, Marking
from pm4py.objects.petri.utils import add_arc_from_to
from pm4py.objects.petri.utils import remove_place, remove_transition
from dtween.digitaltwin.ocpn.objects.obj import ObjectCentricPetriNet
from copy import deepcopy
import uuid
import pandas as pd
import time

PARAM_ACTIVITY_KEY = pm4py.util.constants.PARAMETER_CONSTANT_ACTIVITY_KEY
MAX_FREQUENCY = float("inf")


def apply(ocpn, df, parameters=None):
    if parameters is None:
        parameters = {}

    allowed_activities = parameters["allowed_activities"] if "allowed_activities" in parameters else None
    debug = parameters["debug"] if "debug" in parameters else False

    df = succint_mdl_to_exploded_mdl(df)

    if len(df) == 0:
        df = pd.DataFrame({"event_id": [], "event_activity": []})

    min_node_freq = parameters["min_node_freq"] if "min_node_freq" in parameters else 0
    min_edge_freq = parameters["min_edge_freq"] if "min_edge_freq" in parameters else 0

    df = clean_frequency(df, min_node_freq)
    df = clean_arc_frequency(df, min_edge_freq)

    if len(df) == 0:
        df = pd.DataFrame({"event_id": [], "event_activity": []})

    diag = dict()

    diag["act_count"] = {}
    diag["replay"] = {}
    diag["group_size_hist"] = {}
    diag["act_count_replay"] = {}
    diag["group_size_hist_replay"] = {}
    diag["aligned_traces"] = {}
    diag["place_fitness_per_trace"] = {}
    diag["aggregated_statistics_frequency"] = {}
    diag["aggregated_statistics_performance_min"] = {}
    diag["aggregated_statistics_performance_max"] = {}
    diag["aggregated_statistics_performance_median"] = {}
    diag["aggregated_statistics_performance_mean"] = {}

    diff_log = 0
    diff_model = 0
    diff_token_replay = 0
    diff_performance_annotation = 0
    diff_basic_stats = 0

    persps = ocpn.object_types
    # when replaying streaming log, some objects are missing.
    persps = [x for x in persps if x in df.columns]

    for persp in persps:
        net, im, fm = ocpn.nets[persp]
        aa = time.time()
        if debug:
            print(persp, "getting log")
        log = algorithm.apply(df, persp, parameters=parameters)
        if debug:
            print(len(log))

        if allowed_activities is not None:
            if persp not in allowed_activities:
                continue
            filtered_log = attributes_filter.apply_events(
                log, allowed_activities[persp])
        else:
            filtered_log = log
        bb = time.time()

        diff_log += (bb - aa)

        # filtered_log = variants_filter.apply_auto_filter(deepcopy(filtered_log), parameters={"decreasingFactor": 0.5})

        if debug:
            print(len(log))
            print(persp, "got log")

        cc = time.time()

        dd = time.time()

        diff_model += (dd - cc)

        if debug:
            print(persp, "got model")

        xx1 = time.time()
        activ_count = algorithm.apply(
            df, persp, variant="activity_occurrence", parameters=parameters)
        if debug:
            print(persp, "got activ_count")
        xx2 = time.time()

        ee = time.time()
        variants_idx = variants_module.get_variants_from_log_trace_idx(log)
        # variants = variants_module.convert_variants_trace_idx_to_trace_obj(log, variants_idx)
        # parameters_tr = {PARAM_ACTIVITY_KEY: "concept:name", "variants": variants}

        if debug:
            print(persp, "got variants")

        aligned_traces, place_fitness_per_trace, transition_fitness_per_trace, notexisting_activities_in_model = tr_factory.apply(
            log, net, im, fm, parameters={"enable_pltr_fitness": True, "disable_variants": True})

        if debug:
            print(persp, "done tbr")
        element_statistics = performance_map.single_element_statistics(log, net, im,
                                                                       aligned_traces, variants_idx)

        if debug:
            print(persp, "done element_statistics")
        ff = time.time()

        diff_token_replay += (ff - ee)

        aggregated_statistics = performance_map.aggregate_statistics(
            element_statistics)

        if debug:
            print(persp, "done aggregated_statistics")

        element_statistics_performance = performance_map.single_element_statistics(log, net, im,
                                                                                   aligned_traces, variants_idx)

        if debug:
            print(persp, "done element_statistics_performance")

        gg = time.time()

        aggregated_statistics_performance_min = performance_map.aggregate_statistics(element_statistics_performance,
                                                                                     measure="performance",
                                                                                     aggregation_measure="min")
        aggregated_statistics_performance_max = performance_map.aggregate_statistics(element_statistics_performance,
                                                                                     measure="performance",
                                                                                     aggregation_measure="max")
        aggregated_statistics_performance_median = performance_map.aggregate_statistics(element_statistics_performance,
                                                                                        measure="performance",
                                                                                        aggregation_measure="median")
        aggregated_statistics_performance_mean = performance_map.aggregate_statistics(element_statistics_performance,
                                                                                      measure="performance",
                                                                                      aggregation_measure="mean")

        hh = time.time()

        diff_performance_annotation += (hh - ee)

        if debug:
            print(persp, "done aggregated_statistics_performance")

        group_size_hist = algorithm.apply(
            df, persp, variant="group_size_hist", parameters=parameters)

        if debug:
            print(persp, "done group_size_hist")

        occurrences = {}
        for trans in transition_fitness_per_trace:
            occurrences[trans.label] = set()
            for trace in transition_fitness_per_trace[trans]["fit_traces"]:
                if not trace in transition_fitness_per_trace[trans]["underfed_traces"]:
                    case_id = trace.attributes["concept:name"]
                    for event in trace:
                        if event["concept:name"] == trans.label:
                            occurrences[trans.label].add(
                                (case_id, event["event_id"]))
            # print(transition_fitness_per_trace[trans])

        len_different_ids = {}
        for act in occurrences:
            len_different_ids[act] = len(set(x[1] for x in occurrences[act]))

        eid_acti_count = {}
        for act in occurrences:
            eid_acti_count[act] = {}
            for x in occurrences[act]:
                if not x[0] in eid_acti_count:
                    eid_acti_count[act][x[0]] = 0
                eid_acti_count[act][x[0]] = eid_acti_count[act][x[0]] + 1
            eid_acti_count[act] = sorted(list(eid_acti_count[act].values()))

        ii = time.time()

        diff_basic_stats += (ii - hh) + (xx2-xx1)

        diag["act_count"][persp] = activ_count
        diag["aligned_traces"][persp] = aligned_traces
        diag["place_fitness_per_trace"][persp] = place_fitness_per_trace
        diag["aggregated_statistics_frequency"][persp] = aggregated_statistics
        diag["aggregated_statistics_performance_min"][persp] = aggregated_statistics_performance_min
        diag["aggregated_statistics_performance_max"][persp] = aggregated_statistics_performance_max
        diag["aggregated_statistics_performance_median"][persp] = aggregated_statistics_performance_median
        diag["aggregated_statistics_performance_mean"][persp] = aggregated_statistics_performance_mean

        diag["replay"][persp] = aggregated_statistics
        diag["group_size_hist"][persp] = group_size_hist
        diag["act_count_replay"][persp] = len_different_ids
        diag["group_size_hist_replay"][persp] = eid_acti_count

    diag["aggregated_statistics_performance_median_flattened"] = {}
    for persp in diag["aggregated_statistics_performance_median"]:
        for el in diag["aggregated_statistics_performance_median"][persp]:
            diag["aggregated_statistics_performance_median_flattened"][repr(
                el)] = diag["aggregated_statistics_performance_median"][persp][el]['label']

    diag["aggregated_statistics_performance_mean_flattened"] = {}
    for persp in diag["aggregated_statistics_performance_mean"]:
        for el in diag["aggregated_statistics_performance_mean"][persp]:
            diag["aggregated_statistics_performance_mean_flattened"][repr(
                el)] = diag["aggregated_statistics_performance_mean"][persp][el]['label']

    diag["computation_statistics"] = {"diff_log": diff_log, "diff_model": diff_model,
                                      "diff_token_replay": diff_token_replay,
                                      "diff_performance_annotation": diff_performance_annotation,
                                      "diff_basic_stats": diff_basic_stats}

    return diag
