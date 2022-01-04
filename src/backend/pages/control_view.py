
from backend.components.misc import container, single_row, button, show_title_maker, show_button_id, global_signal_id_maker, temp_jobs_store_id_maker, global_form_load_signal_id_maker

from backend.util import read_global_signal_value, no_update, run_task

from backend.tasks.tasks import get_remote_data, store_redis_backend

from dtween.available.available import AvailableTasks
from dtween.digitaltwin.digitaltwin.action_engine.obj import ValveAction, WriteOperationAction, StaticAction, ActivityVariantAction
from dtween.digitaltwin.digitaltwin.util import read_config
from dtween.digitaltwin.digitaltwin.visualization import visualizer as dt_vis_factory

import dash
import dash_daq as daq
import dash_interactive_graphviz
from dash.dependencies import Input, Output, State, MATCH
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_table
from backend.param.constants import GLOBAL_FORM_SIGNAL, CVIEW_URL, CVIEW_TITLE, ACTIVITY_VARIANT_NAME, ACTIVITY_VARIANT_DESC, ACTIVITY_VARIANT_TR_NAME, DASHBOARD_TITLE

from flask import request


from backend.app import app
import pickle
import redis
from time import sleep
from backend.param.settings import redis_pwd

db = redis.StrictRedis(host='localhost', port=6379, password=redis_pwd, db=0)


def results_key(task_id):
    return f'result-{task_id}'


def store_redis(data, task):
    key = results_key(task)
    pickled_object = pickle.dumps(data)
    db.set(key, pickled_object)


def get_redis_data(task):
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


edit_valves_task = 'edit valves'
edit_write_operations_task = 'edit write operations'
edit_activity_variants_task = 'edit activity variants'

load_dtim_title_1 = "load digital twin interface model"
update_control_view_title = "update control view"
define_action_title = "Define Action"


buttons = dbc.Row(
    [
        # dbc.Col(button(load_dtim_title_1, show_title_maker,
        #         show_button_id), width="auto"),
        # dbc.Col(button(update_control_view_title, show_title_maker,
        #         show_button_id), width="auto"),
        dbc.Col(button(define_action_title, show_title_maker,
                show_button_id), width="auto"),
    ], justify='start'
)


def template_current_configuration(valve_knob_list, activity_variant_table):
    return dbc.Col(
        [
            html.Hr(),
            html.H2("Current Valve Setting"),
            html.Hr(),
            html.Div(
                id='valve_container',
                children=valve_knob_list,
                style={'width': '100%', 'display': 'inline-block',
                       'outline': 'thin lightgrey solid'}
            ),
            html.Hr(),
            html.H2("Current Activity Variants Setting"),
            html.Hr(),
            html.Div(
                id='activity_variant_container',
                children=activity_variant_table,
                style={'width': '100%', 'display': 'inline-block',
                       'outline': 'thin lightgrey solid'}
            ),
            html.Div(
                dcc.Input(id="action-name-input", type="text", placeholder="Type Action Name", debounce=True), style={'display': 'none'}
            )
        ], width=12
    )


def template_configuration_edit(edit_valve_knob_list, edit_activity_variant_data, activity_variants):
    return dbc.Col(
        [
            html.Hr(),
            dcc.Input(id="action-name-input", type="text",
                      placeholder="Type Action Name", debounce=True, style={'width': '100%'}),
            html.Hr(),
            html.H2("Change Valves"),
            html.Hr(),
            html.Div(
                id='valve_container_edit',
                children=edit_valve_knob_list,
                style={'width': '100%', 'display': 'inline-block',
                       'outline': 'thin lightgrey solid'}
            ),
            html.Hr(),
            html.H2("Change Activity Variant"),
            html.Hr(),
            html.Div(
                id='activity_variant_container_edit',
                # children=edit_activity_variant_table,
                children=dash_table.DataTable(
                    id='activity-variant-edit',
                    data=edit_activity_variant_data,
                    columns=[
                        {'id': ACTIVITY_VARIANT_TR_NAME,
                            'name': ACTIVITY_VARIANT_TR_NAME},
                        {'id': ACTIVITY_VARIANT_NAME, 'name': ACTIVITY_VARIANT_NAME,
                            'presentation': 'dropdown'}
                    ],
                    editable=True,
                    dropdown={
                        ACTIVITY_VARIANT_NAME: {
                            'options': [
                                {'label': variant.name, 'value': variant.name}
                                for variant in activity_variants
                            ]
                        }
                    }
                ),
                style={'width': '100%', 'display': 'inline-block',
                       'outline': 'thin lightgrey solid'}
            ),
        ], width=12
    )


configuration_panel = dbc.Col(
    [
        dbc.Row(
            dbc.Col(
                dcc.Tabs(
                    id='tabs-configuration', value='tab-show-configuration',
                    children=[
                        dcc.Tab(label="Current Configuration",
                                value="tab-show-configuration"),
                        dcc.Tab(html.Div(id='activity-variant-edit'), label='Action Definition',
                                value="tab-edit-configuration")
                    ]
                ), width=12
            )
        ),
        dbc.Row(
            html.Div(id='tabs-configuration-content'), justify='end'
        ),
    ],
    width=6
)

control_view_content = dbc.Row(
    [
        dcc.Store(id='control-view-ocpn-dot', storage_type='session', data=""),
        html.Div(
            dcc.Input(id="action-name-input", type="text", placeholder="Type Action Name", debounce=True), style={'display': 'none'}
        ),
        dcc.ConfirmDialog(
            id='confirm-define-action',
            message='An action is defined.',
        ),
        configuration_panel,
        dbc.Col(dash_interactive_graphviz.DashInteractiveGraphviz(
            id="gv-control-view-dtim"), width=6),
    ],
    justify='center',
    style={"height": "100vh"},
)

page_layout = container('Digital Twin Interface Model: Control View',
                        [
                            buttons,
                            control_view_content
                        ]
                        )


@app.callback(
    Output('tabs-configuration-content', 'children'),
    Input('tabs-configuration', 'value'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    State('config-dir', 'data')
    # State('valve-store', 'data'),
)
def render_content(tab, value, dashboard_jobs, cview_jobs, config_dir):
    if tab == 'tab-show-configuration':
        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        dt = get_remote_data(user, log_hash, dashboard_jobs,
                             AvailableTasks.SIMULATE.value)

        valve_knob_list = []
        count = 0
        for valve in dt.valves:
            valve_knob = html.Div(
                style={'width': '33%', 'display': 'inline-block',
                       'outline': 'thin lightgrey solid', 'padding': 10},
                children=[
                    html.Div(
                        daq.Knob(
                            size=150,
                            min=valve.r_min,
                            max=valve.r_max,
                            value=valve.value,
                            label=valve.name,
                            disabled=True
                        )
                    ),
                    html.Div(
                        f'Set to {valve.value}', style={'display': 'inline'}
                    )
                ]
            )
            valve_knob_list.append(valve_knob)
            count += 1

        activity_variant_data = []
        for tr in dt.ocpn.transitions:
            record = {}
            record[ACTIVITY_VARIANT_TR_NAME] = tr.name
            for variant in dt.activity_variants:
                if variant.tr_name == tr.name:
                    record[ACTIVITY_VARIANT_NAME] = variant.name
            if ACTIVITY_VARIANT_NAME not in record:
                record[ACTIVITY_VARIANT_NAME] = 'Not assigned'
            activity_variant_data.append(record)

        activity_variant_table = dash_table.DataTable(
            data=activity_variant_data,
            columns=[
                {'id': ACTIVITY_VARIANT_TR_NAME,
                    'name': ACTIVITY_VARIANT_TR_NAME},
                {'id': ACTIVITY_VARIANT_NAME, 'name': ACTIVITY_VARIANT_NAME}
            ]
        )
        return template_current_configuration(valve_knob_list, activity_variant_table)
    elif tab == 'tab-edit-configuration':
        edit_valves = {}
        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        dt = get_remote_data(user, log_hash, dashboard_jobs,
                             AvailableTasks.SIMULATE.value)
        edit_valve_knob_list = []
        count = 0
        for valve in dt.valves:
            new_valve_edit = html.Div(
                style={'width': '33%', 'display': 'inline-block',
                       'outline': 'thin lightgrey solid', 'padding': 10},
                children=[
                    html.Div(
                        daq.Knob(id={
                            'type': 'dynamic-knob',
                            'index': count
                        },
                            size=150,
                            min=valve.r_min,
                            max=valve.r_max,
                            value=valve.value,
                            label=valve.name
                        )
                    ),
                    html.Div(
                        id={
                            'type': 'dynamic-knob-output',
                            'index': count
                        }, style={'display': 'inline'}
                    )
                ]
            )
            edit_valves[valve.name] = valve.value
            edit_valve_knob_list.append(new_valve_edit)
            count += 1

        edit_activity_variant_data = []
        for tr in dt.ocpn.transitions:
            record = {}
            record[ACTIVITY_VARIANT_TR_NAME] = tr.name
            for variant in dt.activity_variants:
                if variant.tr_name == tr.name:
                    record[ACTIVITY_VARIANT_NAME] = variant.name
                    record[ACTIVITY_VARIANT_DESC] = str(variant.writes)
            if ACTIVITY_VARIANT_NAME not in record:
                record[ACTIVITY_VARIANT_NAME] = 'Not assigned'
            edit_activity_variant_data.append(record)

        store_redis(edit_valves, edit_valves_task)

        return template_configuration_edit(edit_valve_knob_list, edit_activity_variant_data, dt.activity_variants)


@ app.callback(
    Output('confirm-define-action', 'displayed'),
    Output('action-definition', 'data'),
    Input(show_button_id(define_action_title), 'n_clicks'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    State('activity-variant-edit', 'data'),
    State('action-name-input', 'value'),
    State('action-definition', 'data'),
)
def define_action(n_action, value, dashboard_jobs, edit_activity_variants, action_name, action_definition):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']
    if button_value is not None:
        if button_id == show_button_id(define_action_title):
            edit_valves = get_redis_data(edit_valves_task)
            action_definition[action_name] = {'valves': edit_valves,
                                              'activity_variants': edit_activity_variants}
            return True, action_definition
    else:
        return False, dash.no_update


@ app.callback(
    Output({'type': 'dynamic-knob-output', 'index': MATCH}, 'children'),
    [Input({'type': 'dynamic-knob', 'index': MATCH}, 'value'),
     ],
    State({'type': 'dynamic-knob', 'index': MATCH}, 'label')
)
def display_output(value, valve_name):
    edit_valves = get_redis_data(edit_valves_task)
    edit_valves[valve_name] = value
    store_redis(edit_valves, edit_valves_task)
    return f'Set to {value}'


@ app.callback(
    Output("gv-control-view-dtim", "dot_source"),
    Output("gv-control-view-dtim", "engine"),
    Input('url', 'pathname'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
)
def show_control_view_dtim(pathname, value, dashboard_jobs):
    if pathname == CVIEW_URL:
        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        dt = get_remote_data(user, log_hash, dashboard_jobs,
                             AvailableTasks.SIMULATE.value)
        gviz = dt_vis_factory.apply(dt, parameters={"format": "svg"})
        dt_dot = str(gviz)
        return dt_dot, "dot"
    return no_update(2)


# @ app.callback(
#     Output('control-view-ocpn-dot', 'data'),
#     Input(show_button_id(load_dtim_title_1), 'n_clicks'),
#     State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
#     State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
#     State('control-view-ocpn-dot', 'data')
# )
# def load_dtim(n, value, dashboard_jobs, old_dot):
#     if n is not None:
#         user = request.authorization['username']
#         log_hash, date = read_global_signal_value(value)
#         dt = get_remote_data(user, log_hash, dashboard_jobs,
#                              AvailableTasks.SIMULATE.value)
#         gviz = dt_vis_factory.apply(dt, parameters={"format": "svg"})
#         dt_dot = str(gviz)
#         return dt_dot
#     return old_dot
