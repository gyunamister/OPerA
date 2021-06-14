# We simplify the different lengths of months and years
HOURS_IN_DAY = 24
HOURS_IN_WEEK = 7 * HOURS_IN_DAY
HOURS_IN_MONTH = 4 * HOURS_IN_WEEK
HOURS_IN_YEAR = 12 * HOURS_IN_MONTH

SECONDS_IN_HOUR = 3600

DAYS_IN_WEEK_DATETIME = 6

MISSING = 'missing'

INTERVALS = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),    # 60 * 60 * 24
    ('hours', SECONDS_IN_HOUR),    # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
)


DETECTORS_KEY = 'detectors'
THRESHOLDS_KEY = 'thresholds'
LOG_KEY = 'log'
TRANSFORMATION_KEY = 'transform'

GUIDANCE_STD = 0.02
GUIDANCE_PEARSON = 0.75
GUIDANCE_P = 0.05
GUIDANCE_SKEW = 1.5
SITUATION_KEY = 'situation'
SITUATION_AGG_KEY = 'situation-agg'
ANTI_KEY = 'anti'
ENTITY_KEY = 'entity'
MAX_KEY = 'max'
MIN_KEY = 'min'
AVG_KEY = 'avg'
MED_KEY = 'med'

PARAMETER_CONSTANT_MAX_KEY = 'max'
PARAMETER_CONSTANT_MIN_KEY = 'min'

TRANSITION = 'transition'
PLACE = 'place'
FLOW = 'flow'
GUARD = 'guard'

COMP_OPERATORS = ['>', '=', '<', '>=', '<=', '!=']

OBJECT_FILTER = 'object-filter'
EVENT_FILTER = 'event-filter'
