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

DIAGNOSTICS_NAME_MAP = {
    'activity frequency'.title(): 'act_count',
    'avg. group size'.title(): 'mean_group_size',
    'med. group size'.title(): 'med_group_size',
    'min. group size'.title(): 'min_group_size',
    'max. group size'.title(): 'max_group_size',
    'flow frequency'.title(): 'arc_freq',
    'avg. service time'.title(): 'avg_service_time',
    'med. service time'.title(): 'avg_service_time',
    'min. service time'.title(): 'avg_service_time',
    'max. service time'.title(): 'avg_service_time',
    'avg. waiting time'.title(): 'avg_waiting_time',
    'med. waiting time'.title(): 'avg_waiting_time',
    'min. waiting time'.title(): 'avg_waiting_time',
    'max. waiting time'.title(): 'avg_waiting_time',
    'avg. sojourn time'.title(): 'avg_sojourn_time',
    'med. sojourn time'.title(): 'med_sojourn_time',
    'min. sojourn time'.title(): 'min_sojourn_time',
    'max. sojourn time'.title(): 'max_sojourn_time',
    'produced tokens'.title(): 'produced_token',
    'consumed tokens'.title(): 'consumed_token',
    'missing tokens'.title(): 'missing_token',
    'remaining tokens'.title(): 'remaining_token',
}

REPLAY_DIAGNOSTICS_MAP = {
    AvailableDiagnostics.ACT_FREQ.value: 'replayed_act_freq',
    AvailableDiagnostics.AVG_GROUP_SIZE.value: '',
    AvailableDiagnostics.MED_GROUP_SIZE.value: '',
    AvailableDiagnostics.MIN_GROUP_SIZE.value: '',
    AvailableDiagnostics.MAX_GROUP_SIZE.value: '',
    AvailableDiagnostics.FLOW_FREQ.value: 'replayed_arc_frequency',
    AvailableDiagnostics.AVG_SERVICE_TIME.value: "replayed_performance_mean",
    AvailableDiagnostics.MED_SERVICE_TIME.value: "replayed_performance_median",
    AvailableDiagnostics.MIN_SERVICE_TIME.value: "replayed_performance_min",
    AvailableDiagnostics.MAX_SERVICE_TIME.value: "replayed_performance_max",
    AvailableDiagnostics.AVG_WAITING_TIME.value: "replayed_performance_mean",
    AvailableDiagnostics.MED_WAITING_TIME.value: "replayed_performance_median",
    AvailableDiagnostics.MIN_WAITING_TIME.value: "replayed_performance_min",
    AvailableDiagnostics.MAX_WAITING_TIME.value: "replayed_performance_max",
    AvailableDiagnostics.AVG_SOJOURN_TIME.value: "replayed_performance_mean",
    AvailableDiagnostics.MED_SOJOURN_TIME.value: "replayed_performance_median",
    AvailableDiagnostics.MIN_SOJOURN_TIME.value: "replayed_performance_min",
    AvailableDiagnostics.MAX_SOJOURN_TIME.value: "replayed_performance_max",
    AvailableDiagnostics.PRODUCED_TOKENS.value: 'replayed_place_fitness',
    AvailableDiagnostics.CONSUMED_TOKENS.value: 'replayed_place_fitness',
    AvailableDiagnostics.MISSING_TOKENS.value: 'replayed_place_fitness',
    AvailableDiagnostics.REMAINING_TOKENS.value: 'replayed_place_fitness',
    AvailableDiagnostics.ACT_PROB.value: '',
    AvailableDiagnostics.TOTAL_LOGMOVE.value: '',
    AvailableDiagnostics.TOTAL_REWORK.value: '',
    AvailableDiagnostics.TOTAL_MODELMOVE.value: '',
    AvailableDiagnostics.AVG_THROUGHPUT_TIME.value: '',
    AvailableDiagnostics.MED_THROUGHPUT_TIME.value: '',
    AvailableDiagnostics.MIN_THROUGHPUT_TIME.value: '',
    AvailableDiagnostics.MAX_THROUGHPUT_TIME.value: '',
    AvailableDiagnostics.AVG_TOTAL_SERVICE_TIME.value: '',
    AvailableDiagnostics.MED_TOTAL_SERVICE_TIME.value: '',
    AvailableDiagnostics.MIN_TOTAL_SERVICE_TIME.value: '',
    AvailableDiagnostics.MAX_TOTAL_SERVICE_TIME.value: ''

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
