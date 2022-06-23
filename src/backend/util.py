import base64
import io
import json
import ast
import dash
from datetime import datetime
from collections import OrderedDict
import dash_html_components as html
import pandas as pd
from backend.param.constants import JOB_ID_KEY, JOBS_KEY, JOB_DATA_TYPE_KEY, JOB_DATA_NAME_KEY, JOB_DATA_DATE_KEY, \
    JOB_TASKS_KEY, SEP, NA, CSV, PROPS, CHILDREN, VALUE, OBJECTS, TIMESTAMP, VALUES, CORR_METHOD, ACTIVITY, MDL, JSON, START_TIMESTAMP, VALVE_MIN, VALVE_MAX, VALVE_INIT, VALVE_NAME, VALVE_VALUE, WRITE_NAME, WRITE_OBJ_TYPE, WRITE_ATTR_NAME, WRITE_INIT, ACTIVITY_VARIANT_NAME, ACTIVITY_VARIANT_DESC, ACTIVITY_VARIANT_TR_NAME, ACTIVITY_VARIANT_DEFAULT
from backend.tasks.tasks import celery, get_task, db, results_key
from celery.result import AsyncResult
from ocpa.objects.log.util.param import JsonParseParameters
from dtween.available.constants import INTERVALS, TRANSITION, GUARD
from typing import List, Set
from dtween.digitaltwin.digitaltwin.control.obj import NumericalValve, WriteOperation, ActivityVariant
from typing import List, Dict
from ocpa.util.vis_util import human_readable_stat


def add_job(data_format, date, jobs, log_hash, name):
    job_id = jobs[JOB_ID_KEY]
    jobs[JOB_ID_KEY] = job_id + 1
    jobs[JOBS_KEY][log_hash] = {}
    jobs[JOBS_KEY][log_hash][JOB_ID_KEY] = job_id
    jobs[JOBS_KEY][log_hash][JOB_DATA_TYPE_KEY] = data_format
    jobs[JOBS_KEY][log_hash][JOB_DATA_NAME_KEY] = name
    jobs[JOBS_KEY][log_hash][JOB_DATA_DATE_KEY] = date


def remove_tasks_in_jobs(jobs, log_hash, forget=False, task_type=None):
    if jobs is not None and log_hash in jobs[JOBS_KEY]:
        if task_type is not None:
            if task_type in jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY]:
                pass
            else:
                return
        if forget:
            task = get_task(jobs, log_hash, task_type)
            task.forget()
            remove_redis(jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][task_type])
        jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY] = {}


def check_task_type_in_jobs(jobs, log_hash, task_type):
    return jobs is not None and log_hash in jobs[JOBS_KEY] and task_type in jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY] and \
        jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][task_type] is not None


def check_most_recent_task(jobs1, jobs2, log_hash):
    # True if jobs1 contains the older or equally old task
    try:
        date1 = datetime.strptime(
            jobs1[JOBS_KEY][log_hash][JOB_TASKS_KEY][JOB_DATA_DATE_KEY], '%Y-%m-%d %H:%M:%S.%f')
    except (KeyError, TypeError) as e:
        # The first is not existing -> the second is newer
        return True
    try:
        date2 = datetime.strptime(
            jobs2[JOBS_KEY][log_hash][JOB_TASKS_KEY][JOB_DATA_DATE_KEY], '%Y-%m-%d %H:%M:%S.%f')
    except (KeyError, TypeError) as e:
        # The second is not existing -> the first is newer
        return False
    return date1 < date2


def run_task(jobs, log_hash, task_type, task, temp_jobs=None, **kwargs):
    task = task.delay(**kwargs)
    if temp_jobs is not None and log_hash in jobs[JOBS_KEY] and task_type in jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY] and jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][task_type] is not None:
        check_forget_task(task.id, temp_jobs, log_hash, task_type)
    remove_tasks_in_jobs(jobs, log_hash)
    jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][task_type] = task.id
    jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][JOB_DATA_DATE_KEY] = str(
        datetime.now())
    return task.id


def assign_task_id(jobs, log_hash, task_type, task_id):
    jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][task_type] = task_id


def check_forget_task(task_id, jobs, log_hash, task_type):
    if task_id != jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][task_type]:
        task = get_task(jobs, log_hash, task_type)
        task.forget()
        remove_redis(jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][task_type])


def forget_all_tasks(jobs):
    for log_hash in jobs[JOBS_KEY]:
        for task_type in jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY]:
            task_id = jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][task_type]
            task = AsyncResult(id=task_id,
                               app=celery)
            task.forget()
            remove_redis(task_id)


def remove_redis(task_id):
    key = results_key(task_id)
    if db.exists(key):
        db.delete(key)


def get_job_id(jobs, log_hash):
    job_id = jobs[JOBS_KEY][log_hash][JOB_ID_KEY]
    return job_id


def check_existing_job(jobs, log_hash):
    return log_hash in jobs[JOBS_KEY]


def parse_contents(content, data_format):
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if CSV == data_format:
            # Assume that the user uploaded a CSV file
            out = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif MDL == data_format:
            out = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif JSON == data_format:
            out = json.loads(decoded.decode('utf-8'))
        else:
            out = json.loads(decoded)
        return out, True
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ]), False


def write_global_signal_value(values):
    return SEP.join(values)


def read_global_signal_value(value):
    splitted = value.split(SEP)
    return tuple(splitted)


def read_init_signal_value(value):
    values = value.split(SEP)
    session = values[0]
    log_hash = values[1]
    data_format = values[2]
    name = values[3]
    date = values[4]
    return session, log_hash, data_format, name, date


def get_attribute_form_dict(activity, objects, timestamp, values, start_timestamp):
    return {ACTIVITY.title(): activity,
            OBJECTS.title(): SEP.join(objects),
            TIMESTAMP.title(): timestamp,
            VALUES.title(): SEP.join(values),
            START_TIMESTAMP.title(): start_timestamp}


def read_corr_form_dict(d):
    return d[CORR_METHOD.title()], d[OBJECTS.title()].split(SEP)


def guarantee_list_input(data):
    if not isinstance(data, list):
        data = [data]
    if '' in data:
        data.remove('')
    return data


def get_corr_form_dict(method, objects):
    return {OBJECTS.title(): SEP.join(objects),
            CORR_METHOD.title(): method}


def read_active_attribute_form(children):
    log_hash = children[0][PROPS][CHILDREN][0][PROPS][VALUE]
    activity = \
        children[0][PROPS][CHILDREN][3][PROPS][CHILDREN][0][PROPS][CHILDREN][0][PROPS][CHILDREN][1][
            PROPS][VALUE]
    timestamp = \
        children[0][PROPS][CHILDREN][3][PROPS][CHILDREN][1][PROPS][CHILDREN][0][PROPS][CHILDREN][1][
            PROPS][VALUE]
    if VALUE in children[0][PROPS][CHILDREN][3][PROPS][CHILDREN][2][PROPS][CHILDREN][0][PROPS][CHILDREN][1][
            PROPS]:
        objects = \
            children[0][PROPS][CHILDREN][3][PROPS][CHILDREN][2][PROPS][CHILDREN][0][PROPS][CHILDREN][1][
                PROPS][VALUE]
    else:
        objects = []
    if VALUE in children[0][PROPS][CHILDREN][3][PROPS][CHILDREN][3][PROPS][CHILDREN][0][PROPS][CHILDREN][1][
            PROPS]:
        values = \
            children[0][PROPS][CHILDREN][3][PROPS][CHILDREN][3][PROPS][CHILDREN][0][PROPS][CHILDREN][1][
                PROPS][VALUE]
    else:
        values = []
    start_timestamp = \
        children[0][PROPS][CHILDREN][4][PROPS][CHILDREN][0][PROPS][CHILDREN][0][PROPS][CHILDREN][1][
            PROPS][VALUE]
    return activity, log_hash, objects, timestamp, values, start_timestamp


def build_csv_param(activity, objects, timestamp, values, start_timestamp):
    csv_param = {
        "obj_names": objects,
        "val_names": values,
        "time_name": timestamp,
        "act_name": activity,
        "start_timestamp": start_timestamp
    }
    return csv_param


def build_json_param(start_timestamp):
    vmap_params = {}
    if start_timestamp != NA:
        vmap_params[START_TIMESTAMP] = start_timestamp
    json_param = JsonParseParameters(
        vmap_params=vmap_params
    )
    return json_param

# https://stackoverflow.com/questions/4048651/python-function-to-convert-seconds-into-minutes-hours-and-days


def display_time(seconds, granularity=2):
    result = []
    for name, count in INTERVALS:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])


def no_update(n):
    return tuple([dash.no_update] * n)


def get_dev_ctx_form_dict(args, current_offset):
    form_values = args[0:current_offset]
    form_entry = {}
    for index, val in enumerate(form_values):
        if isinstance(val, list):
            form_entry[index] = str(len(val))
        else:
            form_entry[index] = val
    return form_entry


def get_result_form_dict(args, current_offset):
    form_values = args[0:current_offset]
    form_entry = {}
    for index, val in enumerate(form_values):
        form_entry[index] = val
    return form_entry


def read_result_form_dict(form, log_hash):
    args = []
    for index, entry in form[log_hash].items():
        args.append(entry)
    return tuple(args)


def get_corrout_form_dict(log_name, method):
    return {CORR_METHOD: method,
            'log_name': log_name}


def read_corrout_form_dict(form):
    return form[CORR_METHOD], form['log_name']


def transform_to_guards(records):
    guards = OrderedDict()
    for r in records:
        guards.update({r[TRANSITION]: r[GUARD]})
    return guards


def transform_to_valves(records):
    valves: Set[NumericalValve] = set()
    for r in records:
        valve = NumericalValve(r[VALVE_NAME], None,
                               r[VALVE_MIN], r[VALVE_MAX], r[VALVE_INIT])
        valves.add(valve)
    return valves


def transform_to_writes(records):
    writes: Set[WriteOperation] = set()
    for r in records:
        write = WriteOperation(
            r[WRITE_NAME], None, r[WRITE_OBJ_TYPE], r[WRITE_ATTR_NAME], r[WRITE_INIT])
        writes.add(write)
    return writes


def transform_to_activity_variants(records):
    activity_variants: Set[ActivityVariant] = set()
    for r in records:
        activity_variant = ActivityVariant(
            r[ACTIVITY_VARIANT_NAME], ast.literal_eval(r[ACTIVITY_VARIANT_DESC]), None, r[ACTIVITY_VARIANT_DEFAULT])
        activity_variants.add(activity_variant)
    return activity_variants


def transform_config_to_datatable_dict(config):
    datatable_dict = []
    for valve in config:
        temp_dict = {}
        temp_dict['valve'] = valve
        temp_dict['value'] = config[valve]
        datatable_dict.append(temp_dict)
    return datatable_dict


def create_performance_measure_plate(plate_width, name, val, time_measure):
    if time_measure:
        val = human_readable_stat(val)
    return html.Div(  # small block upper most
        className='number-plate-single',
        children=[
            html.H3(f'{name}'),
            html.H3('{}'.format(val))
        ], style={'width': f'{plate_width}%', 'display': 'inline-block'})


def create_1d_plate(title, value):
    return html.Div(
        className='number-plate-single',
        style={'border-top': '#292929 solid .2rem', },
        children=[
            html.H5(
                style={'color': '#292929', },
                children=title
            ),
            html.H3(
                style={'color': '#292929'},
                children=[
                    '{}'.format(value),
                    html.P(
                        style={'color': '#ffffff', },
                        children='xxxx xx xxx xxxx xxx xxxxx'
                    ),
                ]
            ),
        ]
    )


def create_2d_plate(title, diag, time_measure):
    num_plates = len(diag.keys())
    plate_width = (100 / num_plates) - 1

    plates = []
    for agg in diag:
        plates.append(create_performance_measure_plate(
            plate_width, agg, diag[agg], time_measure))

    return html.Div(
        className='number-plate-single',
        style={'border-top': '#292929 solid .2rem', },
        children=[
            html.H5(
                style={'color': '#292929', },
                children=title
            ),
            html.Div(
                style={'color': '#292929'},
                children=plates
            ),
        ]
    )


def create_3d_plate(title, diag, time_measure):
    first_plates = []
    for ot in diag:
        second_plates = []
        num_plates = len(diag[ot].keys())
        plate_width = (100 / num_plates) - 1
        for agg in diag[ot]:
            second_plates.append(create_performance_measure_plate(
                plate_width, agg, diag[ot][agg], time_measure))
        first_plate = html.Div(
            className='number-plate-single',
            style={'border-top': '#292929 solid .2rem', },
            children=[
                html.H5(
                    style={'color': '#292929', },
                    children=ot
                ),
                html.Div(
                    style={'color': '#292929'},
                    children=second_plates
                ),
            ]
        )
        first_plates.append(first_plate)

    return html.Div(
        className='number-plate-single',
        style={'border-top': '#292929 solid .2rem', },
        children=[
            html.H5(
                style={'color': '#292929', },
                children=title
            ),
            html.Div(
                style={'color': '#292929'},
                children=first_plates
            ),
        ]
    )
