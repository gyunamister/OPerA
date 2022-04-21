import operator
from dtween.available.available import AvailablePlaceDiagnostics, AvailableTransitionDiagnostics, AvailableFlowDiagnostics, AvailableDiagnostics
from dtween.available.constants import EVENT_FILTER, OBJECT_FILTER

PERF_METRIC_NAME_MAP = {
    'throughput time'.title(): 'throughput',
    'sojourn time'.title(): 'sojourn',
    'waiting time'.title(): 'waiting',
    'synchronization time'.title(): 'synchronization',
    'coherent synchronization time'.title(): 'coherent_synchronization',
    'inherent synchronization time'.title(): 'inherent_synchronization',
    'absolute frequency'.title(): 'absolute_freq',
    'object frequency'.title(): 'object_freq',
    'object type frequency'.title(): 'object_type_freq',
    'interacting activity frequency'.title(): 'interacting_act_freq',
}

AGG_NAME_MAP = {
    'average'.title(): 'avg',
    'median'.title(): 'med',
    'standard deviation'.title(): 'std',
    'minimum'.title(): 'min',
    'maximum'.title(): 'max',
}

# DIAGNOSTICS_NAME_MAP = {
#     'avg. waiting time'.title(): 'mean_waiting_time',
#     'med. waiting time'.title(): 'median_waiting_time',
#     'min. waiting time'.title(): 'min_waiting_time',
#     'max. waiting time'.title(): 'max_waiting_time',
#     'std. waiting time'.title(): 'stdev_waiting_time',
#     'avg. service time'.title(): 'mean_service_time',
#     'med. service time'.title(): 'median_service_time',
#     'min. service time'.title(): 'min_service_time',
#     'max. service time'.title(): 'max_service_time',
#     'std. service time'.title(): 'stdev_service_time',
#     'avg. sojourn time'.title(): 'mean_sojourn_time',
#     'med. sojourn time'.title(): 'median_sojourn_time',
#     'min. sojourn time'.title(): 'min_sojourn_time',
#     'max. sojourn time'.title(): 'max_sojourn_time',
#     'std. sojourn time'.title(): 'stdev_sojourn_time',
#     'avg. synchronization time'.title(): 'mean_synchronization_time',
#     'med. synchronization time'.title(): 'median_synchronization_time',
#     'min. synchronization time'.title(): 'min_synchronization_time',
#     'max. synchronization time'.title(): 'max_synchronization_time',
#     'std. synchronization time'.title(): 'stdev_synchronization_time',
#     'avg. pooling time'.title(): 'mean_pooling_time',
#     'med. pooling time'.title(): 'median_pooling_time',
#     'min. pooling time'.title(): 'min_pooling_time',
#     'max. pooling time'.title(): 'max_pooling_time',
#     'std. pooling time'.title(): 'stdev_pooling_time',
#     'avg. lagging time'.title(): 'mean_lagging_time',
#     'med. lagging time'.title(): 'median_lagging_time',
#     'min. lagging time'.title(): 'min_lagging_time',
#     'max. lagging time'.title(): 'max_lagging_time',
#     'std. lagging time'.title(): 'stdev_lagging_time',
#     'activity frequency'.title(): 'act_freq',
#     'avg. group size'.title(): 'mean_group_size',
#     'med. group size'.title(): 'median_group_size',
#     'min. group size'.title(): 'min_group_size',
#     'max. group size'.title(): 'max_group_size',
#     'arc frequency'.title(): 'arc_freq'
# }

DIAGNOSTICS_NAME_MAP = {
    'waiting time'.title(): 'waiting_time',
    'service time'.title(): 'service_time',
    'sojourn time'.title(): 'sojourn_time',
    'synchronization time'.title(): 'synchronization_time',
    'pooling time'.title(): 'pooling_time',
    'lagging time'.title(): 'lagging_time',
    'flow time'.title(): 'flow_time',
    'activity frequency'.title(): 'act_freq',
    'object count'.title(): 'group_size',
    'arc frequency'.title(): 'arc_freq'
}

PERFORMANCE_AGGREGATION_NAME_MAP = {
    'mean'.title(): 'mean',
    'median'.title(): 'median',
    'minimum'.title(): 'min',
    'maximum'.title(): 'max',
    'standard deviation'.title(): 'stdev'
}

REPLAY_DIAGNOSTICS_MAP = {
    # AvailableDiagnostics.ACT_FREQ.value: 'replayed_act_freq',
    # AvailableDiagnostics.AVG_GROUP_SIZE.value: '',
    # AvailableDiagnostics.MED_GROUP_SIZE.value: '',
    # AvailableDiagnostics.MIN_GROUP_SIZE.value: '',
    # AvailableDiagnostics.MAX_GROUP_SIZE.value: '',
    # AvailableDiagnostics.ARC_FREQ.value: 'replayed_arc_frequency',
    # AvailableDiagnostics.AVG_SOJOURN_TIME.value: "replayed_performance_mean",
    # AvailableDiagnostics.MED_SOJOURN_TIME.value: "replayed_performance_median",
    # AvailableDiagnostics.MIN_SOJOURN_TIME.value: "replayed_performance_min",
    # AvailableDiagnostics.MAX_SOJOURN_TIME.value: "replayed_performance_max",
    # AvailableDiagnostics.PRODUCED_TOKENS.value: 'replayed_place_fitness',
    # AvailableDiagnostics.CONSUMED_TOKENS.value: 'replayed_place_fitness',
    # AvailableDiagnostics.MISSING_TOKENS.value: 'replayed_place_fitness',
    # AvailableDiagnostics.REMAINING_TOKENS.value: 'replayed_place_fitness',
    # AvailableDiagnostics.ACT_PROB.value: '',
    # AvailableDiagnostics.TOTAL_LOGMOVE.value: '',
    # AvailableDiagnostics.TOTAL_REWORK.value: '',
    # AvailableDiagnostics.TOTAL_MODELMOVE.value: '',
    # AvailableDiagnostics.AVG_THROUGHPUT_TIME.value: '',
    # AvailableDiagnostics.MED_THROUGHPUT_TIME.value: '',
    # AvailableDiagnostics.MIN_THROUGHPUT_TIME.value: '',
    # AvailableDiagnostics.MAX_THROUGHPUT_TIME.value: '',
    # AvailableDiagnostics.AVG_TOTAL_SERVICE_TIME.value: '',
    # AvailableDiagnostics.MED_TOTAL_SERVICE_TIME.value: '',
    # AvailableDiagnostics.MIN_TOTAL_SERVICE_TIME.value: '',
    # AvailableDiagnostics.MAX_TOTAL_SERVICE_TIME.value: ''

}

DIAGNOSTICS_FILTER_MAP = {
    'act_count': EVENT_FILTER,
    'aggregated_statistics_performance_mean_flattened': EVENT_FILTER,
    'aggregated_statistics_performance_median_flattened': EVENT_FILTER
}

OPS_MAP = {
    '>': operator.gt,
    '=': operator.eq,
    '<': operator.lt,
    '>=': operator.ge,  # use operator.div for Python 2
    '<=': operator.le,
    '!=': operator.ne,
}
