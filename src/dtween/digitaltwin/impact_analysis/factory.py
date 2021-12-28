from __future__ import annotations

from dtween.digitaltwin.digitaltwin.control.obj import Valve, WriteOperation
from typing import List, Set, Any, Optional, Tuple
from dtween.digitaltwin.impact_analysis.util import compute_effective_actions, compute_impacted_functions, compute_impacted_objects, compute_impacted_object_instances, compute_impacted_function_instances
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dtween.digitaltwin.digitaltwin.action_engine.obj import ActionInstance
    from dtween.digitaltwin.digitaltwin.objects.obj import DigitalTwin


from random import randrange


def analyze_configure_time_object(dt: DigitalTwin, ai: ActionInstance):
    impacted_object_types = ai.impacted_objects
    return len(impacted_object_types)


def analyze_configure_time_function(dt: DigitalTwin, ai: ActionInstance):
    impacted_functions = ai.impacted_functions
    return len(impacted_functions)


def analyze_run_time_object(dt: DigitalTwin, ai: ActionInstance):
    impacted_object_instances = compute_impacted_object_instances(
        dt, ai)
    return len(impacted_object_instances)


def analyze_run_time_function(dt: DigitalTwin, ai: ActionInstance):
    impacted_function_instances = compute_impacted_function_instances(
        dt, ai)
    return len(impacted_function_instances)


NUM_IMPACTED_OBJECTS = 'number of impacted object types'.title()
NUM_IMPACTED_FUNCTIONS = 'number of impacted functions'.title()
NUM_IMPACTED_OBJECT_INSTANCES = 'number of impacted object instances'.title()
NUM_IMPACTED_FUNCTION_INSTANCES = 'number of impacted function instances'.title()

PRE_CONF_IMPACTS = {NUM_IMPACTED_OBJECTS: analyze_configure_time_object,
                    NUM_IMPACTED_FUNCTIONS: analyze_configure_time_function}

PRE_RUN_IMPACTS = {NUM_IMPACTED_OBJECT_INSTANCES: analyze_run_time_object,
                   NUM_IMPACTED_FUNCTION_INSTANCES: analyze_run_time_function}

SOJOURN_TIME = 'sojourn time'.title()
WAITING_TIME = 'waiting time'.title()
SERVICE_TIME = 'service time'.title()
OBJECT_FREQ = 'object frequency'.title()
THROUGHPUT_TIME = 'throughput time'.title()

POST_OBJ_PERF_IMPACTS = [THROUGHPUT_TIME]
POST_FUNC_PERF_IMPACTS = [SOJOURN_TIME,
                          WAITING_TIME, SERVICE_TIME, OBJECT_FREQ]


def analyze_obj_perf(pre_act_obj_diag, post_act_obj_diag):
    obj_post_impacts = {}
    for d in post_act_obj_diag:
        if d in pre_act_obj_diag:
            obj_post_impacts[d] = {}
            for element in post_act_obj_diag[d]:
                if element in pre_act_obj_diag[d]:
                    obj_post_impacts[d][element] = int(post_act_obj_diag[d][element]) - \
                        int(pre_act_obj_diag[d][element])

    # obj_post_impacts = {
    #     d: post_act_obj_diag[d][element] - pre_act_obj_diag.get(d, 0)[element] for d in post_act_obj_diag for element in post_act_obj_diag[d] if d in pre_act_obj_diag and element in pre_act_obj_diag[d]}

    # FIXME UI test: random values
    # for ot in ai.impacted_objects:
    #     obj_post_impacts[ot] = {}
    #     for obj_perf_metric in POST_OBJ_PERF_IMPACTS:
    #         obj_post_impacts[ot][obj_perf_metric] = randrange(10)
    return obj_post_impacts


def analyze_func_perf(pre_act_func_diag, post_act_func_diag):
    func_post_impacts = {}
    for d in post_act_func_diag:
        if d in pre_act_func_diag:
            func_post_impacts[d] = {}
            for element in post_act_func_diag[d]:
                if element in pre_act_func_diag[d]:
                    func_post_impacts[d][element] = int(post_act_func_diag[d][element]) - \
                        int(pre_act_func_diag[d][element])

    # FIXME UI test: random values
    # for tr in ai.impacted_functions:
    #     obj_post_impacts[tr.name] = {}
    #     for obj_perf_metric in POST_FUNC_PERF_IMPACTS:
    #         obj_post_impacts[tr.name][obj_perf_metric] = randrange(15)
    return func_post_impacts


def analyze_impacted_conf_entities(dt: DigitalTwin, ai: ActionInstance):
    effective_valve_actions, effective_write_operation_actions = compute_effective_actions(
        ai.action, dt.valves, dt.writes)
    impacted_object_types = compute_impacted_objects(
        dt, effective_write_operation_actions)
    impacted_functions = compute_impacted_functions(
        dt, effective_valve_actions, effective_write_operation_actions)

    return impacted_object_types, impacted_functions
    # set([tr.name for tr in impacted_functions])


def analyze_impacted_run_entities(dt: DigitalTwin, ai: ActionInstance):
    impacted_object_instances = compute_impacted_object_instances(
        dt, ai)
    impacted_function_instances = compute_impacted_function_instances(
        dt, ai)

    return set([token[1] for token in impacted_object_instances]), set([token[1] for token in impacted_function_instances])


def analyze_pre_impact(dt: DigitalTwin, ai: ActionInstance):
    pre_impact = {}
    for pci in PRE_CONF_IMPACTS:
        impact_score = PRE_CONF_IMPACTS[pci](
            dt, ai)
        pre_impact[pci] = impact_score

    for pri in PRE_RUN_IMPACTS:
        impact_score = PRE_RUN_IMPACTS[pri](
            dt, ai)
        pre_impact[pri] = impact_score
    return pre_impact


def analyze_post_impact(ai: ActionInstance):
    obj_post_impacts = analyze_obj_perf(
        ai.pre_action_obj_diagnostics, ai.post_action_obj_diagnostics)
    func_post_impacts = analyze_func_perf(
        ai.pre_action_func_diagnostics, ai.post_action_func_diagnostics)
    return obj_post_impacts, func_post_impacts
