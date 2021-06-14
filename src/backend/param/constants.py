from backend.param.colors import PRIMARY, PRIMARY_VERY_LIGHT, INTRINSIC_COLOR
from dtwin.available.available import AvailableSelections, AvailableAggregators

# Jobs Store
JOB_ID_KEY = 'job_id'
JOBS_KEY = 'jobs'
JOB_DATA_TYPE_KEY = 'upload_type'
JOB_TASKS_KEY = 'tasks'
JOB_DATA_NAME_KEY = 'name'
JOB_DATA_DATE_KEY = 'date'
DEFAULT_JOBS = {JOB_ID_KEY: 0,
                JOBS_KEY: {}}

# Default stores
DEFAULT_ROWS = {}
DEFAULT_FORM = {}

# Supported formats
CSV = 'csv'
MDL = 'mdl'
JSONOCEL = 'jsonocel'
JSON = 'json'

# Names for attribute selection
TIMESTAMP = 'timestamp'
OBJECTS = 'objects'
VALUES = 'values'
LOCATION = 'location'
RESOURCE = 'resource'
GLOBAL = 'global'
ACTIVITY = 'activity'
OBJECTTYPE = 'object type'
CORR_METHOD = 'correlation-method'
CSV_ATTRIBUTES_FST = [AvailableSelections.ACTIVITY.value.title(
), TIMESTAMP.title(), OBJECTS.title(), VALUES.title()]
CSV_ATTRIBUTES_SND = [AvailableSelections.RESOURCE.value.title(
), AvailableSelections.LOCATION.value.title()]
CSV_ATTRIBUTES_FST_MULT = [False, False, True, True]
CSV_ATTRIBUTES_SND_MULT = [False, False]

# Global names
NA = 'NA'
SEP = ';'
PROPS = 'props'
CHILDREN = 'children'
VALUE = 'value'
MEMORY_PERSISTENCE = 'memory'

# Multi-page naming
PARSE_TITLE = 'parse'

CORR_TITLE = 'correlate'
CORR_URL = '/correlate'

HOME_TITLE = 'home'
HOME_URL = '/home'

CVIEW_TITLE = 'control'
CVIEW_URL = '/control'

DVIEW_TITLE = 'diagnostics'
DVIEW_URL = '/diagnostics'

DASHBOARD_TITLE = 'dashboard'
DASHBOARD_URL = '/dashboard'

PATTERN_TITLE = 'pattern'
PATTERN_URL = '/pattern'

CORR_OUT_TITLE = 'log'
CORR_OUT_URL = '/log'

TRACE_TITLE = 'trace'
TRACE_URL = '/trace'
TRACE_SIGNAL = 'tracesignal'
TRACE_RETURN = 'tracereturn'
TRACE_RESULT_SIGNAL = 'traceresultsignal'


DEV_CTX_TITLE = 'deviation-context'
DEV_CTX_URL = '/deviation-context'
GUIDANCE_TITLE = 'guidance'

RESULT_TITLE = 'result'
RESULT_URL = '/result'
RESULT_INIT = 'result-init'  # Used as the id of a jobs store for context details
# Used as the id of a jobs store for summary details tasks
RESULT_INIT_SUMMARY = 'result-init-summary'
# Used as the id of a jobs store for post-processing tasks and as an id for a global signal
RESULT_POST = 'result-post'
# telling whether the current job has a valid post-processing task
# Used as the id of a global signal that tells whether a new dev ctx config
RESULT_RECOMPUTE = 'result-recompute'
# has been computed for the currently selected job and the id of a jobs store that keeps the last value to distinguish
# a new configuration from an old configuration
RESULT_WAIT = 'result-wait'

ABOUT_URL = '/about'

# Multi-page signaling and communication
STORES_SIGNALS = [HOME_TITLE, CVIEW_TITLE, DVIEW_TITLE, DASHBOARD_TITLE, PATTERN_TITLE, PARSE_TITLE, CORR_OUT_TITLE, TRACE_TITLE, DEV_CTX_TITLE, RESULT_TITLE, GUIDANCE_TITLE, RESULT_INIT,
                  RESULT_POST, RESULT_INIT_SUMMARY]
TYPED_STORES_SIGNALS = [TRACE_TITLE, DEV_CTX_TITLE]
GLOBAL_FORM_SIGNAL = 'current-log'
FORMS = [PARSE_TITLE, CORR_TITLE, CORR_OUT_TITLE,
         DEV_CTX_TITLE, RESULT_TITLE, TRACE_TITLE]
MULTI_PAGE_URLS = [CORR_OUT_TITLE, RESULT_TITLE,
                   TRACE_RESULT_SIGNAL, TRACE_RETURN]
MULTI_PAGE_REFRESH = [RESULT_URL, CORR_OUT_URL, DEV_CTX_URL, TRACE_URL]
URL_MAPPING = [CORR_OUT_URL, RESULT_URL]
TYPED_FORMS = [CORR_OUT_TITLE]
CB_TYPE_INSPECT = 'inspect-trace'
CB_TYPE_LOG = 'use-log'
CB_TYPE_DUMMY = 'dummy'
CB_TYPE_DETECT = 'detect'
CB_TYPE_INTERPRETATION = 'interpretation'

PLACEHOLDER_KEY = 'placeholder'
FORMTEXT_KEY = 'formtext'

INTRINSIC_DEVIATION = 'intrinsic deviations'
EXTERNAL_DEVIATION = 'external deviations'
DETECTION = 'detection methods'
NEGATIVE_CONTEXT = 'negative contexts'
POSITIVE_CONTEXT = 'positive contexts'
UNKNOWN_CAUSE = 'unknown cause'
EDGE_LBL_CAUSE = 'causes'
EDGE_LBL_DETECT = 'is detected by'
EDGE_LBL_CONTAIN = 'contains selected'
FONTSIZE_VIZ = '12'


# The maximum corresponds to the rule that if a trace has a deviating event,
# the whole trace is considered deviating --> most sensitive
AGGREGATOR = AvailableAggregators.MAX
TOP_KEY = 'top'
SUMMARY_KEY = 'summary'
CONTEXT_KEY = 'context'
INCLUDES_KEY = 'includes'
GUIDES_KEY = 'guides'
METHODS_KEY = 'methods'
FORM_PREFIX = 'form-load-global-signal-'
SIGNAL_PREFIX = 'global-signal-'
COLORSCALE = [[0, PRIMARY], [0.5, PRIMARY_VERY_LIGHT], [1, INTRINSIC_COLOR]]
deviation_score = 'deviation score'
positive_context = 'positive context'
negative_context = 'negative context'
deviating = 'Detection result'
tid_t = 'tid'
start_ts = 'start timestamp'
end_ts = 'end timestamp'
n_events = '# events'
group_t = 'Group'
high_t = 'high'
bord_ps = 'bordps'
bord_ng = 'bordng'
column_names = [deviation_score, positive_context, negative_context, deviating, tid_t, start_ts, end_ts, n_events,
                high_t, bord_ps, bord_ng]
DEFAULT_TOP = 5
DP = 4
SHOW_PREVIEW_ROWS = 20
ATTRIBUTE_CSV_TEXT = "Please assign the respective name(s) of your data's columns to their respective attributes:"
ATTRIBUTE_OCEL_TEXT = "If available, please assign the respective name(s) of your OCEL event values to their respective attribute:"
