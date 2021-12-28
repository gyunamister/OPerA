
from backend.components.misc import container, single_row, button, show_title_maker, show_button_id, global_signal_id_maker, temp_jobs_store_id_maker, global_form_load_signal_id_maker

from backend.util import read_global_signal_value, no_update, run_task

from backend.tasks.tasks import get_remote_data, store_redis_backend

from dtween.available.available import AvailableTasks
from dtween.digitaltwin.digitaltwin.action_engine.obj import ValveAction, WriteOperationAction, StaticAction
from dtween.digitaltwin.digitaltwin.objects.obj import WriteOperation
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
from backend.param.constants import GLOBAL_FORM_SIGNAL, DESIGN_TITLE, PARSE_TITLE, CVIEW_URL, WRITE_NAME, WRITE_OBJ_TYPE, WRITE_ATTR_NAME, WRITE_INIT, WRITE_TR_NAME, CVIEW_TITLE

from flask import request
import copy


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

load_dtim_title_1 = "load digital twin interface model"
update_control_view_title = "update control view"
define_action_title = "Define Action"


buttons = dbc.Row(
    [
        dbc.Col(button(load_dtim_title_1, show_title_maker,
                show_button_id), width="auto"),
        dbc.Col(button(update_control_view_title, show_title_maker,
                show_button_id), width="auto"),
        dbc.Col(button(define_action_title, show_title_maker,
                show_button_id), width="auto"),
    ], justify='start'
)

valves_form = dbc.FormGroup(
    [
        dbc.Label("Valves"),
        dcc.Dropdown(id='valve-dropdown'),
        dcc.Slider(id='valve-slider'),
        html.Div(id='current-valve-value'),
        dbc.FormText(id='current-valve-value'),
        dcc.Input(id="action-specification", type="text",
                  placeholder="Enter Action name"),
        html.Br(),
    ]
)

write_operations_form = dbc.FormGroup(
    [
        dbc.Label("Write Operations"),
        dash_table.DataTable(
            id='temp',
            columns=[
                {'id': 'transition', 'name': 'transition'},
                {'id': 'guard', 'name': 'guard',
                 'presentation': 'dropdown'},
            ],
            editable=True
        ),
        dbc.FormText(
            "Click here if you want to apply the current guards to the digital twin",
            color="secondary",
        ),
    ]
)

tab1_content = dbc.Col(
    [
        html.Hr(),
        html.H2("Current Valve Setting"),
        html.Hr(),
        html.Div(
            id='valve_container',
            children=[],
            style={'width': '100%', 'display': 'inline-block',
                   'outline': 'thin lightgrey solid'}
        ),
        html.Hr(),
        html.H2("Current Write Operation Setting"),
        html.Hr(),
        html.Div(
            id='write_container',
            children=[],
            style={'width': '100%', 'display': 'inline-block',
                   'outline': 'thin lightgrey solid'}
        ),
    ], width=12
)


def template_configuration_edit(edit_valve_knob_list, edit_write_operation_table):
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
            html.H2("Change Write Operation"),
            html.Hr(),
            html.Div(
                id='write_container_edit',
                children=edit_write_operation_table,
                style={'width': '100%', 'display': 'inline-block',
                       'outline': 'thin lightgrey solid'}
            )
        ], width=12
    )


# tab2_content = dbc.Col([dash_table.DataTable(
#     id='edit-write-operation-table'
# )], width=12)

configuration_panel = dbc.Col(
    [
        dbc.Row(
            dbc.Col(
                dcc.Tabs(
                    id='tabs-configuration', value='tab-show-configuration',
                    children=[
                        dcc.Tab(tab1_content, label="Current Configuration",
                                value="tab-show-configuration"),
                        dcc.Tab(html.Div(id='edit-write-operation-table'), label='Action Definition',
                                value="tab-edit-configuration")
                    ]
                ), width=12
            )
        ),
        dbc.Row(
            html.Div(id='tabs-configuration-content',
                     children=[
                         dcc.Input(id="action-name-input", type="text", placeholder="Type Action Name", debounce=True)]
                     ), justify='end'
        ),
    ],
    width=6
)

control_view_content = dbc.Row(
    [
        dcc.Store(id='control-view-ocpn-dot', storage_type='session', data=""),
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

page_layout = container('Design Digital Twin Interface Model',
                        [
                            buttons,
                            control_view_content
                        ]
                        )


@app.callback(
    Output('tabs-configuration-content', 'children'),
    Input('tabs-configuration', 'value'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data')
)
def render_content(tab, value, cview_jobs):
    if tab == 'tab-show-configuration':
        return []
    elif tab == 'tab-edit-configuration':
        edit_write_operations = {}
        edit_valves = {}
        # if value is None:
        #     value = old_value
        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        dt = get_remote_data(user, log_hash, cview_jobs,
                             AvailableTasks.STORE_CONFIG.value)
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

        for write_operation in dt.writes:
            if write_operation.tr_name not in edit_write_operations:
                edit_write_operations[write_operation.tr_name] = [
                    write_operation.name]
            else:
                edit_write_operations[write_operation.tr_name].append(
                    write_operation.name)

        edit_write_operation_data = [
            {WRITE_NAME: w.name, WRITE_OBJ_TYPE: w.object_type,
             WRITE_ATTR_NAME: w.attr_name, WRITE_TR_NAME: w.tr_name} for w in dt.writes
        ]

        edit_write_operation_table = dash_table.DataTable(
            id='edit-write-operation-table',
            data=edit_write_operation_data,
            columns=[
                {'id': 'name', 'name': 'Name'},
                {'id': 'object_type', 'name': 'Object Type'},
                {'id': 'attr_name', 'name': 'Attribute Name'},
                {'id': 'tr_name', 'name': 'Transition',
                    'presentation': 'dropdown'},
            ],

            editable=True,
            dropdown={
                'tr_name': {
                    'options': [
                        {'label': tr.name, 'value': tr.name}
                        for tr in dt.ocpn.transitions
                    ]
                }
            }
        ),

        # store_redis(edit_write_operations, edit_write_operations_task)
        store_redis(edit_valves, edit_valves_task)

        return template_configuration_edit(edit_valve_knob_list, edit_write_operation_table)


@ app.callback(
    Output('control-view-ocpn-dot', 'data'),
    Input(show_button_id(load_dtim_title_1), 'n_clicks'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    # State(global_signal_id_maker(PARSE_TITLE), 'children'),
    State(temp_jobs_store_id_maker(DESIGN_TITLE), 'data'),
    State('control-view-ocpn-dot', 'data')
)
def load_dtim(n, value, control_jobs, old_dot):
    if n is not None:
        # if value is None:
        #     value = old_value
        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        dt = get_remote_data(user, log_hash, control_jobs,
                             AvailableTasks.DESIGN.value)
        gviz = dt_vis_factory.apply(dt, parameters={"format": "svg"})
        dt_dot = str(gviz)
        return dt_dot
    return old_dot


@ app.callback(
    Output(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    Output('valve_container', 'children'),
    Output('write_container', 'children'),
    Output('confirm-define-action', 'displayed'),
    Input(show_button_id(update_control_view_title), 'n_clicks'),
    Input(show_button_id(define_action_title), 'n_clicks'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    # State(global_signal_id_maker(PARSE_TITLE), 'children'),
    State(temp_jobs_store_id_maker(DESIGN_TITLE), 'data'),
    State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    State('valve-store', 'data'),
    State('config-dir', 'data'),
    State('edit-write-operation-table', 'data'),
    State('action-name-input', 'value'),
)
def update_cview_and_define_action(n_update, n_action, value, design_jobs, cview_jobs, valves, config_dir, edit_write_operations, action_name):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']
    if button_id == show_button_id(update_control_view_title):
        conf_valves, conf_write_operations = read_config(config_dir)
        print("configuration from {}".format(config_dir))

        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        dt = get_remote_data(user, log_hash, design_jobs,
                             AvailableTasks.DESIGN.value)

        valve_knob_list = []
        if valves is not None:
            count = 0
            for name, value in valves.items():
                dt.update_valve(name, conf_valves[name])
                r_min = valves[name]['r_min']
                r_max = valves[name]['r_max']
                cur = conf_valves[name]
                valve_knob = html.Div(
                    style={'width': '33%', 'display': 'inline-block',
                           'outline': 'thin lightgrey solid', 'padding': 10},
                    children=[
                        html.Div(
                            daq.Knob(
                                size=150,
                                min=r_min,
                                max=r_max,
                                value=cur,
                                label=name,
                                disabled=True
                            )
                        ),
                        html.Div(
                            f'Set to {cur}', style={'display': 'inline'}
                        )
                    ]
                )
                valve_knob_list.append(valve_knob)
                count += 1

        for wo in conf_write_operations.keys():
            dt.update_write(wo, conf_write_operations[wo][WRITE_TR_NAME])

        write_operations = {}
        for write_operation in dt.writes:
            if write_operation.tr_name not in write_operations:
                write_operations[write_operation.tr_name] = [
                    write_operation.name]
            else:
                write_operations[write_operation.tr_name].append(
                    write_operation.name)

        write_operation_data = [
            {WRITE_NAME: w.name, WRITE_OBJ_TYPE: w.object_type,
             WRITE_ATTR_NAME: w.attr_name, WRITE_TR_NAME: w.tr_name} for w in dt.writes
        ]

        write_operation_table = dash_table.DataTable(
            id='write-operation-table',
            data=write_operation_data,
            columns=[
                {'id': 'name', 'name': 'Name'},
                {'id': 'object_type', 'name': 'Object Type'},
                {'id': 'attr_name', 'name': 'Attribute Name'},
                {'id': 'tr_name', 'name': 'Transition',
                    'presentation': 'dropdown'},
            ],
            dropdown={
                'tr_name': {
                    'options': [
                        {'label': tr.name, 'value': tr.name}
                        for tr in dt.ocpn.transitions
                    ]
                }
            }
        ),
        task_id = run_task(
            design_jobs, log_hash, AvailableTasks.STORE_CONFIG.value, store_redis_backend, data=dt)
        return design_jobs, valve_knob_list, write_operation_table, False
    elif button_id == show_button_id(define_action_title):
        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        dt = get_remote_data(user, log_hash, cview_jobs,
                             AvailableTasks.STORE_CONFIG.value)
        edit_valves = get_redis_data(edit_valves_task)
        valve_actions = []
        for valve in edit_valves:
            valve_action = ValveAction(valve, edit_valves[valve])
            valve_actions.append(valve_action)
        write_operation_actions = []
        for edit_wo in edit_write_operations:
            write_operation_action = WriteOperationAction(
                edit_wo[WRITE_NAME], edit_wo[WRITE_TR_NAME])
            write_operation_actions.append(write_operation_action)

        action = StaticAction(name=action_name, valve_actions=valve_actions,
                              write_operation_actions=write_operation_actions)
        dt.action_engine.add_action(action)
        task_id = run_task(
            cview_jobs, log_hash, AvailableTasks.STORE_CONFIG.value, store_redis_backend, data=dt)
        return cview_jobs, dash.no_update, dash.no_update, True
    else:
        return no_update(3), False


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
    Output({'type': 'dynamic-dropdown-output', 'index': MATCH}, 'children'),
    [Input({'type': 'dynamic-dropdown', 'index': MATCH}, 'value'),
     ],
    State({'type': 'dynamic-dropdown', 'index': MATCH}, 'id')
)
def save_edit_write_operations(write_name, dropdown_id):
    tr_name = dropdown_id['index']
    edit_write_operations = get_redis_data(edit_write_operations_task)
    # new_edit_write_operations = copy.deepcopy(old_edit_write_operations)
    edit_write_operations[tr_name] = write_name
    # print("WRITE OPERATIONS UPLOADED")
    # print(new_edit_write_operations)
    store_redis(edit_write_operations, edit_write_operations_task)
    return dash.no_update


@ app.callback(
    Output("gv-control-view-dtim", "dot_source"),
    Output("gv-control-view-dtim", "engine"),
    Input('url', 'pathname'),
    Input("control-view-ocpn-dot", "data")
)
def show_control_view_dtim(pathname, value):
    if pathname == CVIEW_URL and value is not None:
        return value, "dot"
    return no_update(2)
