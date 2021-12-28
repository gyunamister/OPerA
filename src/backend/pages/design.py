from flask import request
from backend.param.settings import CeleryConfig, redis_pwd
from time import sleep
import redis
import pickle
from dtween.digitaltwin.ocel.objects.ocel.converter import factory as ocel_converter_factory
from dtween.parsedata.objects.ocdata import ObjectCentricData
from dtween.available.available import AvailableTasks
from backend.tasks.tasks import get_remote_data, build_digitaltwin, store_redis_backend
from backend.util import add_job, run_task, forget_all_tasks, get_job_id, check_existing_job, read_global_signal_value, read_active_attribute_form, transform_to_guards, write_global_signal_value, no_update, parse_contents, transform_to_valves, transform_to_writes, transform_to_activity_variants

from dtween.digitaltwin.digitaltwin.util import guards_to_df, guard_df_to_dict
from dtween.digitaltwin.digitaltwin.visualization import visualizer as dt_vis_factory
import hashlib
import base64


from backend.components.misc import container, single_row, button, show_title_maker, show_button_id, global_signal_id_maker, temp_jobs_store_id_maker, global_form_load_signal_id_maker
import dash_interactive_graphviz
from dash.dependencies import Input, Output, State, MATCH
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from backend.app import app
import pandas as pd
import dash_table
import dash
import dash_daq as daq
from collections import OrderedDict
from backend.param.constants import DESIGN_TITLE, DESIGN_URL, PARSE_TITLE, JSON, GLOBAL_FORM_SIGNAL, VALVE_MIN, VALVE_MAX, VALVE_INIT, VALVE_NAME, VALVE_VALUE, WRITE_NAME, WRITE_OBJ_TYPE, WRITE_ATTR_NAME, TRANSITION, GUARD, WRITE_INIT, ACTIVITY_VARIANT_NAME, ACTIVITY_VARIANT_DESC, ACTIVITY_VARIANT_TR_NAME, ACTIVITY_VARIANT_DEFAULT


discover_title = "Discover OCPN"
upload_guard_title = "Upload Guards"
upload_valve_title = "Upload Valves"
upload_write_title = "Upload Writes"
upload_activity_variant_title = "Upload Activity Variants"

apply_guard_title = "Apply Guards"
apply_valve_title = "Apply Valves"
apply_write_title = "Apply Writes"
apply_activity_variant_title = "Apply Activity Variants"
apply_configuration_title = "Set default configuration"
connect_db_title = "Connect to Information System"

CELERY_TIMEOUT = 21600


db = redis.StrictRedis(host='localhost', port=6379, password=redis_pwd, db=0)


def results_key(task_id):
    return f'result-{task_id}'


def store_redis(data, task):
    key = results_key(task)
    pickled_object = pickle.dumps(data)
    db.set(key, pickled_object)


def get_redis_data(user, task):
    timeout = 0
    key = results_key(task)
    while not db.exists(key):
        sleep(1)
        timeout += 1
        if timeout > CELERY_TIMEOUT:
            return None
        if task.failed():
            return None
    return pickle.loads(db.get(key))


buttons = dbc.Row(
    [
        dbc.Col(button(discover_title, show_title_maker,
                show_button_id), width='auto'),
        dbc.Col(dcc.Upload(id="upload-valve",
                children=button(upload_valve_title, show_title_maker, show_button_id)), width='auto'),
        dbc.Col(dcc.Upload(id="upload-guard",
                children=button(upload_guard_title, show_title_maker, show_button_id)), width='auto'),
        dbc.Col(dcc.Upload(id="upload-write",
                children=button(upload_write_title, show_title_maker, show_button_id)), width='auto'),
        dbc.Col(dcc.Upload(id="upload-activity-variant",
                children=button(upload_activity_variant_title, show_title_maker, show_button_id)), width='auto'),
        dbc.Col(dcc.Upload(id="upload-system-config",
                children=button(connect_db_title, show_title_maker, show_button_id)), width='auto'),
    ], justify='start', className="g-0",
)

guards_form = dbc.FormGroup(
    [
        dbc.Label("Guards"),
        dash_table.DataTable(
            id='guard-table',
            columns=[
                {'id': 'transition', 'name': 'transition'},
                {'id': 'guard', 'name': 'guard',
                 'presentation': 'dropdown'},
            ],
            editable=True,
            # style_table={'overflowX': 'auto'},
            fixed_columns={'headers': True, 'data': 1},
            style_table={'minWidth': '100%'}
        ),
        button(apply_guard_title,
               show_title_maker, show_button_id),
        dbc.FormText(
            "Click here if you want to apply the current guards to the digital twin interface model",
            color="secondary",
        ),
    ]
)

valves_form = dbc.FormGroup(
    [
        dbc.Label("Valves"),
        dash_table.DataTable(
            id='valve-table',
            columns=[
                {'id': VALVE_NAME, 'name': VALVE_NAME},
                {'id': VALVE_INIT, 'name': VALVE_INIT},
                {'id': VALVE_MIN, 'name': VALVE_MIN},
                {'id': VALVE_MAX, 'name': VALVE_MAX},
            ],
            editable=True,
            style_table={'overflowX': 'auto'},
        ),
        button(apply_valve_title,
               show_title_maker, show_button_id),
        dbc.FormText(
            "Click here if you want to apply the current valves to the digital twin interface model",
            color="secondary",
        ),
    ]
)

writes_form = dbc.FormGroup(
    [
        dbc.Label("Writes"),
        dash_table.DataTable(
            id='write-table',
            columns=[
                {'id': WRITE_NAME, 'name': WRITE_NAME},
                {'id': WRITE_OBJ_TYPE, 'name': WRITE_OBJ_TYPE},
                {'id': WRITE_ATTR_NAME, 'name': WRITE_ATTR_NAME},
                {'id': WRITE_INIT, 'name': WRITE_INIT},
            ],
            editable=True,
            style_table={'overflowX': 'auto'},
        ),
        button(apply_write_title,
               show_title_maker, show_button_id),
        dbc.FormText(
            "Click here if you want to apply the current valves to the digital twin interface model",
            color="secondary",
        ),
    ]
)

activity_variants_form = dbc.FormGroup(
    [
        dbc.Label("Activity Variant"),
        dash_table.DataTable(
            id='activity-variant-table',
            columns=[
                {'id': ACTIVITY_VARIANT_NAME, 'name': ACTIVITY_VARIANT_NAME},
                {'id': ACTIVITY_VARIANT_DESC, 'name': ACTIVITY_VARIANT_DESC},
                {'id': ACTIVITY_VARIANT_DEFAULT, 'name': ACTIVITY_VARIANT_DEFAULT}
            ],
            editable=True,
            style_table={'overflowX': 'auto'},
        ),
        button(apply_activity_variant_title,
               show_title_maker, show_button_id),
        dbc.FormText(
            "Click here if you want to apply the current valves to the digital twin interface model",
            color="secondary",
        ),
    ]
)


design_content = dbc.Row(
    [
        dcc.Store(id='guard-store', storage_type='session'),
        dcc.Store(id='ocpn-dot', storage_type='session', data=""),
        dcc.ConfirmDialog(
            id='confirm-guard-update',
            message='Guard information is updated.',
        ),
        dbc.Col(
            dash_interactive_graphviz.DashInteractiveGraphviz(id="gv"), width=6
        ),
        dbc.Col(
            [
                valves_form,
                guards_form,
                writes_form,
                activity_variants_form
            ],
            width=6
        ),

    ],
    # style=dict(position="absolute", height="100%",
    #            width="100%", display="flex"),
    justify='center',
    style={"height": "100vh"},
)

page_layout = container('Design Digital Twin Interface Model',
                        [
                            buttons,
                            design_content
                        ]
                        )


@ app.callback(
    Output("gv", "dot_source"),
    Output("gv", "engine"),
    Input('url', 'pathname'),
    Input("ocpn-dot", "data")
)
def show_ocpn(pathname, value):
    if pathname == DESIGN_URL and value is not None:
        return value, "dot"
    return no_update(2)


@ app.callback(
    Output("selected", "children"),
    Input("gv", "selected")
)
def show_selected(value):
    return html.Div(value)


@ app.callback(
    Output(temp_jobs_store_id_maker(DESIGN_TITLE), 'data'),
    Output('ocpn-dot', 'data'),
    Input(show_button_id(discover_title), 'n_clicks'),
    Input(show_button_id(apply_guard_title), 'n_clicks'),
    Input(show_button_id(apply_valve_title), 'n_clicks'),
    Input(show_button_id(apply_write_title), 'n_clicks'),
    Input(show_button_id(apply_activity_variant_title), 'n_clicks'),
    State('guard-table', 'data'),
    State('valve-table', 'data'),
    State('write-table', 'data'),
    State('activity-variant-table', 'data'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(PARSE_TITLE), 'data'),
    State(temp_jobs_store_id_maker(DESIGN_TITLE), 'data'),
    prevent_initial_call=True
)
def run_build_digitaltwin(n_discover, n_guard, n_valve, n_write, n_variant, guard_data, valve_data, write_data, activity_variant_data, value, data_jobs, design_jobs):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']
        # if value is None:
        #     value = old_value

    if button_value is not None:
        if button_id == show_button_id(discover_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            data = get_remote_data(user, log_hash, data_jobs,
                                   AvailableTasks.PARSE.value)

            eve_df, obj_df = ocel_converter_factory.apply(data)
            task_id = run_task(
                data_jobs, log_hash, AvailableTasks.DESIGN.value, build_digitaltwin, data=eve_df)
            dt = get_remote_data(user, log_hash, data_jobs,
                                 AvailableTasks.DESIGN.value)
            gviz = dt_vis_factory.apply(dt, parameters={"format": "svg"})
            dt_dot = str(gviz)
            return data_jobs, dt_dot

        elif button_id == show_button_id(apply_valve_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            valves = transform_to_valves(valve_data)
            dt = get_remote_data(user, log_hash, design_jobs,
                                 AvailableTasks.DESIGN.value)
            dt.valves = valves
            task_id = run_task(
                design_jobs, log_hash, AvailableTasks.DESIGN.value, store_redis_backend, data=dt)
            return design_jobs, dash.no_update

        elif button_id == show_button_id(apply_guard_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            dt = get_remote_data(user, log_hash, design_jobs,
                                 AvailableTasks.DESIGN.value)
            for record in guard_data:
                dt.add_guard(record[TRANSITION], record[GUARD])
            task_id = run_task(
                design_jobs, log_hash, AvailableTasks.DESIGN.value, store_redis_backend, data=dt)
            gviz = dt_vis_factory.apply(dt, parameters={"format": "svg"})
            dt_dot = str(gviz)
            return design_jobs, dt_dot

        elif button_id == show_button_id(apply_write_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            writes = transform_to_writes(write_data)
            dt = get_remote_data(user, log_hash, design_jobs,
                                 AvailableTasks.DESIGN.value)
            dt.writes = writes
            task_id = run_task(
                design_jobs, log_hash, AvailableTasks.DESIGN.value, store_redis_backend, data=dt)
            return design_jobs, dash.no_update

        elif button_id == show_button_id(apply_activity_variant_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            activity_variants = transform_to_activity_variants(
                activity_variant_data)
            dt = get_remote_data(user, log_hash, design_jobs,
                                 AvailableTasks.DESIGN.value)
            dt.activity_variants = activity_variants
            task_id = run_task(
                design_jobs, log_hash, AvailableTasks.DESIGN.value, store_redis_backend, data=dt)
            return design_jobs, dash.no_update

    return no_update(2)


@ app.callback(
    Output('valve-table', 'data'),
    Input('valve-store', 'data'),
)
def update_valve_table(valves):
    # df = guards_to_df(guards)
    # guards = [{'transition': 'notify', 'guard': 'g1'}, {'transition': 'split', 'guard': 'g2'}, {
    #     'transition': 'retry', 'guard': 'g3'}, {'transition': 'create', 'guard': 'g4'}]
    if valves is not None:
        valve_table = [{VALVE_NAME: v, VALVE_INIT: valves[v][VALVE_INIT],
                        VALVE_MIN: valves[v][VALVE_MIN], VALVE_MAX: valves[v][VALVE_MAX]} for v in valves]
        return valve_table
    else:
        dash.no_update


@ app.callback(
    Output('write-table', 'data'),
    Input('write-store', 'data'),
)
def update_write_table(writes):
    if writes is not None:
        write_table = [{
            WRITE_NAME: w,
            WRITE_OBJ_TYPE: writes[w][WRITE_OBJ_TYPE],
            WRITE_ATTR_NAME: writes[w][WRITE_ATTR_NAME],
            WRITE_INIT: writes[w][WRITE_INIT]
        } for w in writes]
        return write_table
    else:
        dash.no_update


@ app.callback(
    Output('activity-variant-table', 'data'),
    Input('activity-variant-store', 'data'),
)
def update_activity_variant_table(activity_variants):
    if activity_variants is not None:
        activity_variant_table = [{
            ACTIVITY_VARIANT_NAME: variant,
            ACTIVITY_VARIANT_DESC: str(activity_variants[variant][ACTIVITY_VARIANT_DESC]),
            ACTIVITY_VARIANT_DEFAULT: activity_variants[variant][ACTIVITY_VARIANT_DEFAULT]
        } for variant in activity_variants]
        return activity_variant_table
    else:
        dash.no_update


@ app.callback(
    Output('guard-table', 'data'),
    Output('guard-table', 'dropdown'),
    Input('guard-store', 'data'),
)
def update_guard_table(guards):
    if guards is not None:
        dropdown = {
            'guard': {
                'options': [{'label': d['guard'], 'value': d['guard']} for d in guards]
            }
        }
        return guards, dropdown
    else:
        return guards, dash.no_update


@ app.callback(
    Output('guard-store', 'data'),
    Input('upload-guard', 'contents'),
    State('guard-store', 'data')
)
def upload_guards(content, old_guards):
    if content is not None:
        data, success = parse_contents(content, JSON)
        guards = data['guards']
        return guards
    else:
        return old_guards


@ app.callback(
    Output('valve-store', 'data'),
    Input('upload-valve', 'contents'),
    State('valve-store', 'data')
)
def upload_valves(content, old_valves):
    if content is not None:
        data, success = parse_contents(content, JSON)
        valves = data['valves']
        return valves
    else:
        return old_valves


@ app.callback(
    Output('write-store', 'data'),
    Input('upload-write', 'contents'),
    State('write-store', 'data')
)
def upload_writes(content, old_writes):
    if content is not None:
        data, success = parse_contents(content, JSON)
        writes = data['writes']
        return writes
    else:
        return old_writes


@ app.callback(
    Output('activity-variant-store', 'data'),
    Input('upload-activity-variant', 'contents'),
    State('activity-variant-store', 'data')
)
def activity_variants(content, activity_variants):
    if content is not None:
        data, success = parse_contents(content, JSON)
        activity_variants = data['activity_variants']
        return activity_variants
    else:
        return activity_variants


@ app.callback(
    Output('valve-slider', 'min'),
    Output('valve-slider', 'max'),
    Output('valve-slider', 'value'),
    Output('valve-slider', 'marks'),
    Input('valve-dropdown', 'value'),
    State('valve-store', 'data'),
)
def update_valves(selected, valves):
    if selected is not None:
        r_min = valves[selected]['r_min']
        r_max = valves[selected]['r_max']
        cur = valves[selected]['default']
        marks = {
            r_min: {'label': 'Min: {}'.format(r_min), 'style': {'color': '#77b0b1'}},
            r_max: {'label': 'Max: {}'.format(r_max), 'style': {
                'color': '#f50'}}
        }
        return r_min, r_max, cur, marks
    else:
        return no_update(4)


@app.callback(
    Output('current-valve-value', 'children'),
    Input('valve-slider', 'value')
)
def valve_action(value):
    return "Set value to: {}".format(value)


@ app.callback(
    Output('valve-dropdown', 'options'),
    Output('valve-dropdown', 'value'),
    Input('valve-store', 'data')
)
def update_valve(valves):
    if valves is not None:
        options = [{'label': name, 'value': name}
                   for name, value in valves.items()]
        return options, options[0]['value']
    else:
        return no_update(2)


@ app.callback(
    Output('log-dir', 'data'),
    Output('config-dir', 'data'),
    Input('upload-system-config', 'contents'),
    State('log-dir', 'data'),
    State('config-dir', 'data'),
)
def connect_to_system(content, old_log_dir, old_config_dir):
    if content is not None:
        data, success = parse_contents(content, JSON)
        log_dir = data['dir-event-stream']
        config_dir = data['dir-system-config']
        return log_dir, config_dir
    else:
        return old_log_dir, old_config_dir
