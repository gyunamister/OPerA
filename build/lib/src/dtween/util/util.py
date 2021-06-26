import operator
from dtween.available.available import AvailablePlaceDiagnostics, AvailableTransitionDiagnostics, AvailableFlowDiagnostics
from dtween.available.constants import EVENT_FILTER, OBJECT_FILTER


DIAGNOSTICS_MAP = {
    AvailableTransitionDiagnostics.OBJECT_COUNT.value: 'act_count',
    AvailableFlowDiagnostics.AVG_SOJOURN.value: 'aggregated_statistics_performance_mean_flattened',
    AvailableFlowDiagnostics.MED_SOJOURN.value: 'aggregated_statistics_performance_median_flattened',
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
