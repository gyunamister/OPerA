from enum import Enum

# TODO possibly change strings to ints
from dtween.available.constants import HOURS_IN_YEAR, HOURS_IN_MONTH, HOURS_IN_WEEK


def get_simple_available_from_name(name, default, available):
    for candidate in available:
        if name == candidate.value:
            return candidate
    return default


class AvailablePlaceDiagnostics(Enum):
    AVG_WAITING = 'avg. waiting'.title()
    MED_WAITING = 'med. waiting'.title()
    STD_WAITING = 'std. waiting'.title()
    TOTAL_LOGMOVE = 'tot. move on log'.title()


class AvailableTransitionDiagnostics(Enum):
    AVG_SERVICE = 'avg. service'.title()
    MED_SERVICE = 'med. service'.title()
    STD_SERVICE = 'std. service'.title()
    TOTAL_REWORK = 'tot. rework'.title()
    TOTAL_MODELMOVE = 'tot. move on model'.title()
    OBJECT_COUNT = 'object count'.title()


class AvailableFlowDiagnostics(Enum):
    PROB = 'routing probability'.title()
    AVG_SOJOURN = 'avg. sojourn'.title()
    MED_SOJOURN = 'med. sojourn'.title()
    STD_SOJOURN = 'std. sojourn'.title()


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


class AvailableAggregators(Enum):
    MIN = 1
    MAX = 2
    AVG = 3
    MED = 4


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
    BUILD = 'build'
    DIAGNIZE = 'diagnize'
    OPERATE = 'operate'
    CONVERT = 'convert'
    EVALUATE = 'evaluate'


class AvailableColorPalettes(Enum):
    BLIND = 'colorblind'


def get_available_granularity_from_name(granularity):
    if granularity == AvailableGranularity.HR.value.title():
        granularity = AvailableGranularity.HR
    else:
        granularity = AvailableGranularity.DAY
    return granularity
