import pandas as pd
import datetime
from dateutil import parser

from dtween.digitaltwin.diagnostics import algorithm as diagnostics_factory
from dtween.digitaltwin.ocel.objects.mdl.preprocessor import factory as mdl_preprocess_factory

from dtween.util.util import DIAGNOSTICS_MAP, OPS_MAP, DIAGNOSTICS_FILTER_MAP
from dtween.available.constants import EVENT_FILTER, OBJECT_FILTER

import json


def read_config(directory):
    with open(directory) as config_json:
        config = json.loads(config_json.read())
    return config['config']


def update_config(directory, valve, value):
    config = read_config(directory)
    new_config = {'config': config}
    with open(directory, 'w') as file:
        new_config['config'][valve] = value
        json.dump(new_config, file, indent=4)


def gen_diagnostics_scheme(action_pattern_repo):
    diagnostics_scheme = dict()
    for ap in action_pattern_repo:
        diag_dur = ap["condition"]["cond_duration"]
        cond_type = ap["condition"]["cond_type"]
        diag_type = DIAGNOSTICS_MAP[cond_type]
        diag_filter_type = DIAGNOSTICS_FILTER_MAP[diag_type]
        if diag_dur not in diagnostics_scheme:
            diagnostics_scheme[diag_dur] = {}
            diagnostics_scheme[diag_dur][diag_type] = diag_filter_type
        else:
            diagnostics_scheme[diag_dur][diag_type] = diag_filter_type
    return diagnostics_scheme


def gen_diagnostics_records(action_pattern_repo, dt, df, current_timestamp, interval, n_intervals):
    diagnostics_scheme = gen_diagnostics_scheme(action_pattern_repo)
    diagnostics_records = {}
    for dur in diagnostics_scheme:
        diag_start_timestamp = current_timestamp - \
            datetime.timedelta(hours=dur)
        # diag_end_timestamp = current_timestamp + \
        #     datetime.timedelta(hours=interval*n_intervals)
        diag_end_timestamp = current_timestamp
        print("Diagnostics start at {} and ends at {}".format(
            diag_start_timestamp, diag_end_timestamp))
        # print("df", df)
        # diagnostics after event filtering
        event_filtered_df = mdl_preprocess_factory.filter_by_timestamp(
            df, start_timestamp=diag_start_timestamp, end_timestamp=diag_end_timestamp)
        event_filtered_diagnostics = diagnostics_factory.apply(
            dt.ocpn, event_filtered_df)
        # print("event_filtered_df: ", event_filtered_df)

        # diagnostics after object filtering
        # TODO at the moment hard-coded to "order" type, but object graph concept should be used to be generalized.
        object_filtered_df = mdl_preprocess_factory.object_filter_by_timestamp(
            df, start_timestamp=diag_start_timestamp, end_timestamp=diag_end_timestamp, object_type="order")
        # print("object_filtered_df: ", object_filtered_df)
        object_filtered_diagnostics = diagnostics = diagnostics_factory.apply(
            dt.ocpn, object_filtered_df)
        diagnostics = {}
        for diag_type in diagnostics_scheme[dur]:
            diag_type_filter = diagnostics_scheme[dur][diag_type]
            if diag_type_filter == EVENT_FILTER:
                diagnostics[diag_type] = event_filtered_diagnostics[diag_type]
            elif diag_type_filter == OBJECT_FILTER:
                diagnostics[diag_type] = object_filtered_diagnostics[diag_type]
        diagnostics_records[dur] = diagnostics
        print(diagnostics)
    return diagnostics_records


def evaluate(action_pattern_repo, dt, event_df, current_timestamp, interval, n_intervals, config_dir):
    diagnostics_records = gen_diagnostics_records(action_pattern_repo, dt,
                                                  event_df, current_timestamp, interval, n_intervals)
    action_log = []
    exp_log = []
    for ap in action_pattern_repo:
        exp = {}
        trigger, eval_message, diag_val = evaluate_condition(
            diagnostics_records, ap["condition"])
        exp["val"] = diag_val
        exp["time"] = interval*n_intervals
        if trigger:
            action_message = execute_action(ap["action"], config_dir)
        else:
            action_message = "No action"
        exp["action"] = action_message
        action_log.append("[%s] %s -> \n %s" % (current_timestamp.strftime(
            "%Y-%m-%d, %H:%M:%S"), eval_message, action_message))
        exp_log.append(exp)
    return action_log, exp_log


def evaluate_condition(diagnostics_records, condition):
    dur = condition["cond_duration"]
    diag = diagnostics_records[dur]
    cond_type = condition["cond_type"]
    diag_type = DIAGNOSTICS_MAP[cond_type]
    operator = condition["cond_operator"]
    threshold = condition["cond_threshold"]
    el = condition["cond_element"]
    cond_name = condition["cond_name"]
    if diag[diag_type] == "act_count":
        if el not in diag[diag_type]['item'].keys():
            return False, "%s cannot be measured" % (cond_name), None
        else:
            diag_val = diag[diag_type]['item'][el]
    else:
        if el not in diag[diag_type].keys():
            return False, "%s cannot be measured" % (cond_name), None
        else:
            diag_val = diag[diag_type][el]
    # performance in seconds to hour
    if 's' in str(diag_val):
        diag_val = float(diag_val[:-1])/60
    elif 'h' in str(diag_val):
        diag_val = float(diag_val[:-1])
    elif 'D' in str(diag_val):
        diag_val = float(diag_val[:-1])*24
    else:
        diag_val = float(diag_val)
    eval_message = "Evaluate if {} {} {} at {}".format(
        diag_val, operator, threshold, el)
    print(eval_message)
    if OPS_MAP[operator](diag_val, threshold):
        return True, "%s evaluates to True" % (cond_name), diag_val
    else:
        return False, "%s evaluates to False" % (cond_name), diag_val


def execute_action(action, config_dir):
    valve = action["act_valve"]
    value = action["act_value"]
    update_config(config_dir, valve, value)
    action_message = "Update {} to {}".format(valve, value)
    print(action_message)
    return action_message
