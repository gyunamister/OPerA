from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from functools import partial

from dtween.available.available import AvailableSelections, AvailableNormRanges
from dtween.available.constants import TRANSFORMATION_KEY


class DtweenExtensible(Enum):
    CORR = 'correlation'


class DtweenExtension:
    """A generic class for extensible objects of dtween.
Create new event correlation methods, context entity & situation types and detection methods.

Keyword arguments:
- name: The name of the newly added method/type. Must equal the key of the constructing definition of one of the
extension enums in :doc:`../../backend/param/available`
- param: A dict of (default) keyword arguments passed to call in case of correlation methods, to the situation
constructor (contained in situation) in case of situations and to the context entity constructor (contained in entity)
in case of context entities.
- typ: An instance of DtweenExtensible.
- call: A reference to a function. In the case of correlation methods a reference to the correlation function,
in the case of situations the identification function (that maps context entities to situation values),
in the case of context entities the extraction function (that maps events to entity values) and in the case of
detection methods the constructor to the detector class that implements the detection methods (specifically
in its detect function).
- param_constructor (optional): Use only for situations. Contains a reference to the constructor of the detector class'
corresponding parameter class.
- input_display (optional): Use only for extending detection methods. The dict has the name of the input parameter as key and
another dict for the parameter's details as value. The parameter's details is a dict with keys: PLACEHOLDER_KEY and
string value for giving the user a hint for what to insert, FORMTEXT_KEY and string value with a hint text for the user;
and TRANSFORMATION_KEY and reference value to a function definition (or lambda) that converts the input string of
the user to the correct format and type of your new detection method's parameter. See :doc:`../../backend/param/available`
for examples.
- help_text (optional): Markdown formatted help string for the help button in case of detection methods and situations
- log_param (optional): Use only for detection methods. If the detector's parameter needs attributes of the
ObjectCentricLog object as parameters for instantiation, then you can specify all of them as a list of string names.
Please note that you are allowed to use nested attributes like attr1.attr2 to access attr2 during instantiation.
- available (optional): Contains a reference to the corresponding simple enum in :doc:`../available`
- available_entity (optional): Use only for situations. Contains a reference to the associated context entity that is in the domain
of the situation.
- selections (optional): Use only for situations. Contains the implemented selections of that situation.
- entity (optional): Use only for context entities. Contains a reference to the corresponding constructor.
- situation (optional): Use only for situations. Contains a reference to the corresponding constructor.
- extractor_target (optional): Use only for context entities. Contains the attribute name of the entity object
that will be instantiated with the output value of the extraction function.
- arguments (optional): Use only for context entities. Contains a list of string names of variables that are passed
as arguments to the extraction function. The available arguments are: ['selection', 'meta', 'vmap_param', 'objects',
'chunk'], where selection is the desired selection, meta is the MetaObjectCentricData object, vmap_param is the
 VmapParameters object of the ParseParameters object, objects contains a dict of object ids to Object objects and
 chunk is a Dict of event ids to events for this context entity.
- interpretation (optional): Use only for situations. Contains a reference to a function that takes arguments anti
(proportional vs. anti-proportional, necessary for guaranteeing a consistent interpretation of the situation's
codomain), rng (an instance of a normalization range AvailableNormRanges in :doc:`../available`), date (string),
sel (the name of the corresponding selection of the situation), unit (the time unit size), ctx_val (the situation value),
 event_table (a Dash data table containing the events that are used for respective situation), inspect_traces (
 a list of Dash Bootstrap Component's Rows and Cols containing buttons linked to trace inspection of traces that
 contain the respective event in event_table), entity_table (a Dash data table of context entities that are used
 by this situation). This function is used to automatically generate Dash Bootstrap Component's toasts with
 detailed interpretations for situations over a day on the result page. Please refer to :doc:`../../backend/callbacks/callbacks`
 for exemplary use and to :doc:`../../backend/param/interpretations` for definitions.
- interpretation_anti (optional): Use only for situations. The same as interpretation, but now for the anti-proportional case.
- interpretation_single (optional): Use only for situations. The same as interpretation, but now not for multiple situations
of the same type fora day, but a single situation. Hence, the referenced function takes only a subset as arguments:
anti, unit, val, rng, sel.
- helper_global (optional): Use only for situations. Contains a reference to the constructor of global helpers (
the drift is insignificant, the data can be normalized over the whole timespan by computing helpers such as maximum and
minimum).
- helper_granular (optional): Use only for situations. Contains a reference to the constructor of granular helpers (
the drift is moderate, significant, or very significant; the data can be normalized over a year / month / week by computing helpers such as maximum and
minimum)
- global_helper_call (optional): Use only for situations. Contains a reference to the function that extracts the
helper values for global helpers.
- granular_helper_call (optional): Use only for situations. Contains a reference to the function that extracts the
helper values for granular helpers.
- param_helper (optional): Use only for situations. A keyword arguments dict that is passed to the helper constructor.
- resource (optional): Use only for detection methods. If the detection method uses the event's resource, then specify this
with True, else False. Currently, this means that the detection method can only be selected, if a resource is available
in the data.

"""

    def __init__(self,
                 name,
                 param,
                 typ,
                 call,
                 param_constructor=None,
                 input_display=None,
                 help_text=None,
                 log_param=None,
                 available=None,
                 available_entity=None,
                 selections=None,
                 entity=None,
                 situation=None,
                 extractor_target=None,
                 arguments=None,
                 interpretation=None,
                 interpretation_anti=None,
                 interpretation_single=None,
                 helper_global=None,
                 helper_granular=None,
                 global_helper_call=None,
                 granular_helper_call=None,
                 param_helper=None,
                 resource=None):
        self.name = name
        self.input_display = input_display
        self.help_text = help_text
        self.available = available
        self.selections = selections
        self.interpretation = interpretation
        self.interpretation_anti = interpretation_anti
        self.interpretation_single = interpretation_single
        self.available_entity = available_entity
        self.resource = resource
        self._callable_helper_global = global_helper_call
        self._callable_helper_granular = granular_helper_call
        self._entity = entity
        self._situation = situation
        self._helper_global = helper_global
        self._helper_granular = helper_granular
        self._extractor_target = extractor_target
        self._arguments = arguments
        self._param = param
        self._param_helper = param_helper
        self._param_constructor = param_constructor
        self._typ = typ
        self._callable = call
        self._log_param = log_param

    name: str
    input_display: Dict[str, Dict[str, Any]]
    help_text: str
    available: Any
    selections: List[AvailableSelections]
    available_entity: Any
    interpretation: str
    interpretation_anti: str  # For aggregate context / time perspective
    interpretation_single: str  # For a single, barebone context
    # Contains true if resoure is needed in the current implementation of a detector
    resource: Optional[bool]
    _arguments: Any  # Will hold a list of argument names to be passed to the respective extractor
    _extractor_target: str  # The target attribute for entity extraction
    _entity: Any  # Contains the constructor for the context entity
    _situation: Any  # Contains the constructor for the situation
    _helper_global: Any  # Contains the constructor for the helper with global drift
    # contains the constructor for the helper with non-global drift (e.g. yearly)
    _helper_granular: Any
    # Contains a list of attribute names of the ObjectCentricLog that is used as a param
    _log_param: List[str]
    _param: Any  # Just a dict of parameters passed to call
    _param_helper: Dict[str, Any]  # Used for additional helper parameters
    _param_constructor: Any  # Used to build parameter objects
    _typ: DtweenExtensible
    # Used for various purposes (identification, extraction...)
    _callable: Callable
    # Used only for extraction of helper aggregators with global drift
    _callable_helper_global: Callable
    # Used only for extraction of helper aggregators with non-global drift
    _callable_helper_granular: Callable

    def call_with_param(self, **kwargs):
        return self._callable(**self._param, **kwargs)

    def call_wo_param(self, **kwargs):
        return self._callable(**kwargs)

    def build_param_obj(self, log, **kwargs):
        param_args = {}
        for arg in kwargs:
            param_args = {
                **param_args, **self.input_display[arg][TRANSFORMATION_KEY](kwargs[arg])}
        if self._log_param is not None:
            for log_param in self._log_param:
                for i, nested_param in enumerate(log_param.split('.')):
                    if i == 0:
                        current_attr = getattr(log, nested_param)
                    else:
                        current_attr = getattr(current_attr, nested_param)
                param_args = {**param_args, **{nested_param: current_attr}}
        return self._param_constructor(**param_args)
