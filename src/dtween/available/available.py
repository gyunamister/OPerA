from enum import Enum

# TODO possibly change strings to ints
from dtween.available.constants import HOURS_IN_YEAR, HOURS_IN_MONTH, HOURS_IN_WEEK


def get_simple_available_from_name(name, default, available):
    for candidate in available:
        if name == candidate.value:
            return candidate
    return default


class AvailablePerformanceMetric(Enum):
    THROUGHPUT_TIME = 'throughput time'.title()
    SOJOURN_TIME = 'sojourn time'.title()
    # SERVICE_TIME = 'service time'.title()
    WAITING_TIME = 'waiting time'.title()
    SYNCRONIZATION_TIME = 'synchronization time'.title()
    COHERENT_SYNC_TIME = 'coherent synchronization time'.title()
    INHERENT_SYNC_TIME = 'inherent synchronization time'.title()
    ABS_FREQ = 'absolute frequency'.title()
    OBJECT_FREQ = 'object frequency'.title()
    # COMPLETE_FREQ = 'complete frequency'.title()
    # ONGOING_FREQ = 'ongoing frequency'.title()
    OBJECT_TYPE_FREQ = 'object type frequency'.title()
    INTERACTING_ACT_FREQ = 'interacting activity frequency'.title()


class AvailableAggregators(Enum):
    UNDEFINED = ""
    AVG = 'average'.title()
    MED = 'median'.title()
    STD = 'standard deviation'.title()
    MIN = 'minimum'.title()
    MAX = 'maximum'.title()


class DefaultDiagnostics(Enum):
    ACT_FREQ = 'activity frequency'.title()
    FLOW_FREQ = 'flow frequency'.title()
    AVG_SOJOURN_TIME = 'avg. sojourn time'.title()
    MED_SOJOURN_TIME = 'med. sojourn time'.title()
    MIN_SOJOURN_TIME = 'min. sojourn time'.title()
    MAX_SOJOURN_TIME = 'max. sojourn time'.title()


class AvailableDiagnostics(Enum):
    ACT_FREQ = 'activity frequency'.title()
    AVG_GROUP_SIZE = 'avg. group size'.title()
    MED_GROUP_SIZE = 'med. group size'.title()
    MIN_GROUP_SIZE = 'min. group size'.title()
    MAX_GROUP_SIZE = 'max. group size'.title()
    FLOW_FREQ = 'flow frequency'.title()
    AVG_SERVICE_TIME = 'avg. service time'.title()
    MED_SERVICE_TIME = 'med. service time'.title()
    MIN_SERVICE_TIME = 'min. service time'.title()
    MAX_SERVICE_TIME = 'max. service time'.title()
    AVG_WAITING_TIME = 'avg. waiting time'.title()
    MED_WAITING_TIME = 'med. waiting time'.title()
    MIN_WAITING_TIME = 'min. waiting time'.title()
    MAX_WAITING_TIME = 'max. waiting time'.title()
    AVG_SOJOURN_TIME = 'avg. sojourn time'.title()
    MED_SOJOURN_TIME = 'med. sojourn time'.title()
    MIN_SOJOURN_TIME = 'min. sojourn time'.title()
    MAX_SOJOURN_TIME = 'max. sojourn time'.title()
    PRODUCED_TOKENS = 'produced tokens'.title()
    CONSUMED_TOKENS = 'consumed tokens'.title()
    MISSING_TOKENS = 'missing tokens'.title()
    REMAINING_TOKENS = 'remaining tokens'.title()
    ACT_PROB = 'routing probability'.title()
    TOTAL_LOGMOVE = 'tot. move on log'.title()
    TOTAL_REWORK = 'tot. rework'.title()
    TOTAL_MODELMOVE = 'tot. move on model'.title()
    AVG_THROUGHPUT_TIME = 'avg. throughput time'.title()
    MED_THROUGHPUT_TIME = 'med. throughput time'.title()
    MIN_THROUGHPUT_TIME = 'min. throughput time'.title()
    MAX_THROUGHPUT_TIME = 'max. throughput time'.title()
    AVG_TOTAL_SERVICE_TIME = 'avg. total service time'.title()
    MED_TOTAL_SERVICE_TIME = 'med. total service time'.title()
    MIN_TOTAL_SERVICE_TIME = 'min. total service time'.title()
    MAX_TOTAL_SERVICE_TIME = 'max. total service time'.title()


class AvailableConfObjImpact(Enum):
    NUM_IMPACTED_OBJECTS = 'number of impacted object types'.title()


class AvailableConfFuncImpact(Enum):
    NUM_IMPACTED_FUNCTIONS = 'number of impacted functions'.title()


class AvailableRunObjImpact(Enum):
    NUM_IMPACTED_OBJECT_INSTANCES = 'number of impacted object instances'.title()


class AvailableRunFuncImpact(Enum):
    NUM_IMPACTED_FUNCTION_INSTANCES = 'number of impacted function instances'.title()


class AvailableObjPerformanceMetric(Enum):
    AVG_THROUGHPUT_TIME = 'avg. throughput time'.title()
    MED_THROUGHPUT_TIME = 'med. throughput time'.title()
    MIN_THROUGHPUT_TIME = 'min. throughput time'.title()
    MAX_THROUGHPUT_TIME = 'max. throughput time'.title()
    AVG_TOTAL_SERVICE_TIME = 'avg. total service time'.title()
    MED_TOTAL_SERVICE_TIME = 'med. total service time'.title()
    MIN_TOTAL_SERVICE_TIME = 'min. total service time'.title()
    MAX_TOTAL_SERVICE_TIME = 'max. total service time'.title()


class AvailableFuncPerformanceMetric(Enum):
    AVG_SOJOURN_TIME = 'avg. sojourn time'.title()
    MED_SOJOURN_TIME = 'med. sojourn time'.title()
    MIN_SOJOURN_TIME = 'min. sojourn time'.title()
    MAX_SOJOURN_TIME = 'max. sojourn time'.title()
    AVG_SERVICE_TIME = 'avg. service time'.title()
    MED_SERVICE_TIME = 'med. service time'.title()
    MIN_SERVICE_TIME = 'min. service time'.title()
    MAX_SERVICE_TIME = 'max. service time'.title()
    AVG_WAITING_TIME = 'avg. waiting time'.title()
    MED_WAITING_TIME = 'med. waiting time'.title()
    MIN_WAITING_TIME = 'min. waiting time'.title()
    MAX_WAITING_TIME = 'max. waiting time'.title()
    ACT_FREQ = 'activity frequency'.title()
    FLOW_FREQ = 'flow frequency'.title()


class AvailablePlaceDiagnostics(Enum):
    PRODUCED_TOKENS = 'produced tokens'.title()
    CONSUMED_TOKENS = 'consumed tokens'.title()
    MISSING_TOKENS = 'missing tokens'.title()
    REMAINING_TOKENS = 'remaining tokens'.title()
    AVG_WAITING_TIME = 'avg. waiting time'.title()
    MED_WAITING_TIME = 'med. waiting time'.title()
    MIN_WAITING_TIME = 'min. waiting time'.title()
    MAX_WAITING_TIME = 'max. waiting time'.title()
    TOTAL_LOGMOVE = 'tot. move on log'.title()


class AvailableTransitionDiagnostics(Enum):
    ACT_FREQ = 'activity frequency'.title()
    AVG_GROUP_SIZE = 'avg. group size'.title()
    MED_GROUP_SIZE = 'med. group size'.title()
    MIN_GROUP_SIZE = 'min. group size'.title()
    MAX_GROUP_SIZE = 'max. group size'.title()
    AVG_SERVICE_TIME = 'avg. service time'.title()
    MED_SERVICE_TIME = 'med. service time'.title()
    MIN_SERVICE_TIME = 'min. service time'.title()
    MAX_SERVICE_TIME = 'max. service time'.title()
    TOTAL_REWORK = 'tot. rework'.title()
    TOTAL_MODELMOVE = 'tot. move on model'.title()


class AvailableFlowDiagnostics(Enum):
    FLOW_FREQ = 'flow frequency'.title()
    AVG_SOJOURN_TIME = 'avg. sojourn time'.title()
    MED_SOJOURN_TIME = 'med. sojourn time'.title()
    MIN_SOJOURN_TIME = 'min. sojourn time'.title()
    MAX_SOJOURN_TIME = 'max. sojourn time'.title()
    ACT_PROB = 'routing probability'.title()


class AvailableSelections(Enum):
    GLOBAL = 'global'.title()
    ACTIVITY = 'activity'.title()
    OBJECTTYPE = 'object type'.title()
    RESOURCE = 'resource'.title()
    LOCATION = 'location'.title()


class AvailableValves(Enum):
    NUMERICAL = 'numerical'.title()


class AvailableCorrelations(Enum):
    MAXIMUM_CORRELATION = 'shared object id relation (maximum)'.title()
    INITIAL_PAIR_CORRELATION = 'shared object id relation (minimum)'.title()
    OBJ_PATH_CORRELATION = 'object path correlation'.title()


class AvailableGranularity(Enum):
    SEC = 'sec'
    MIN = 'min'
    HR = 'hour'
    DAY = 'day'
    WK = 'wk'
    MON = 'mon'
    YR = 'yr'


class AvailableNormRanges(Enum):
    GLOBAL = 'insignificant'
    BINS = {'moderate': HOURS_IN_YEAR,
            'significant': HOURS_IN_MONTH,
            'very significant': HOURS_IN_WEEK}


def extract_options(ranges):
    options = [ranges.GLOBAL.value]
    return options + [option for option in ranges.BINS.value]


def get_range_from_name(name):
    if name == AvailableNormRanges.GLOBAL.value:
        return {AvailableNormRanges.GLOBAL: 1}
    elif name in AvailableNormRanges.BINS.value:
        return {AvailableNormRanges.BINS: AvailableNormRanges.BINS.value[name]}


# class AvailableAggregators(Enum):
#     MIN = 1
#     MAX = 2
#     AVG = 3
#     MED = 4


class AvailableDataFormats(Enum):
    CSV = 'csv'
    JSON = 'json'
    MDL = 'mdl'
    OCDATA = 'ocdata'
    OCLOG = 'oclog'


class AvailableTasks(Enum):
    PARSE = 'parse'
    UPLOAD = 'upload'
    CORR = 'correlate'
    DESIGN = 'design'
    VISUALIZE = 'visualize'
    DIAGNIZE = 'diagnize'
    OPERATE = 'operate'
    CONVERT = 'convert'
    EVALUATE = 'evaluate'
    STORE_CONFIG = 'store_config'
    SIMULATE = 'simulate'


class AvailableColorPalettes(Enum):
    BLIND = 'colorblind'


def get_available_granularity_from_name(granularity):
    if granularity == AvailableGranularity.HR.value.title():
        granularity = AvailableGranularity.HR
    else:
        granularity = AvailableGranularity.DAY
    return granularity
