import pathlib
import hashlib
import base64
from datetime import datetime
from datetime import timedelta
import re
import sqlite3
import json

import subprocess

from backend.components.misc import container, single_row, button, show_title_maker, show_button_id, global_signal_id_maker, temp_jobs_store_id_maker, global_form_load_signal_id_maker
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from backend.app import app
import dash_table
import dash
import dash_daq as daq
from backend.param.constants import DASHBOARD_URL, GLOBAL_FORM_SIGNAL, CVIEW_TITLE, JSON, DASHBOARD_TITLE, DESIGN_TITLE, ACTIVITY_VARIANT_NAME, ACTIVITY_VARIANT_DESC, ACTIVITY_VARIANT_TR_NAME

from dtween.digitaltwin.digitaltwin.util import read_config
from dtween.util.util import REPLAY_DIAGNOSTICS_MAP
from dtween.digitaltwin.ocel.objects.ocel.importer import factory as ocel_import_factory
from dtween.digitaltwin.digitaltwin.action_engine.obj import ValveAction, WriteOperationAction, StaticAction, ActivityVariantAction
from backend import time_utils

from backend.util import read_global_signal_value, no_update, parse_contents, run_task
from backend.tasks.tasks import get_remote_data, store_redis_backend
from dtween.available.available import AvailableTasks, AvailableConfObjImpact, AvailableConfFuncImpact, AvailableRunObjImpact, AvailableRunFuncImpact, AvailableObjPerformanceMetric, AvailableFuncPerformanceMetric
from dtween.digitaltwin.digitaltwin.operation import factory as oper_factory
from dtween.digitaltwin.impact_analysis import visualizer as impact_visualizer
from flask import request
from dateutil import parser

import pickle
import redis
from time import sleep
from backend.param.settings import redis_pwd


set_default_config_title = "Sync to information system".title()
update_action_title = "Update actions".title()
start_title = "start".title()
move_forward_title = "forward".title()
add_action_instance_title = "Add action instance"


class SimulationController:
    proc: subprocess.Popen = None

    def __init__(self, proc=None):
        self.proc = proc

    # @proc.setter
    # def proc(self, proc):
    #     self._proc = proc

    # @property
    # def proc(self):
    #     return self._proc

    # def test(self):
    #     pass


path = pathlib.Path().resolve().parent.absolute()
proc = subprocess.Popen(
    ["python", f"{path}/sim/p2p.py"], stdin=subprocess.PIPE)
sc = SimulationController(proc)


def set_proc(proc):
    sc.proc = proc


def get_proc():
    return sc.proc


sim_process_id = "current-sim-process"


step_size_slider = html.Div(
    [
        dbc.Label("Select Simulation Step Size", html_for="slider"),
        dcc.Slider(id='step-size-slider', min=0, max=120, value=24),
        dbc.FormText(id='output-step-size-slider')
    ]
)

num_step_slider = html.Div(
    [
        dbc.Label("Select Number of Steps", html_for="slider"),
        dcc.Slider(id='num-step-slider', min=0, max=365, value=100),
        dbc.FormText(id='output-num-step-slider')
    ]
)

action_input = html.Div(
    [
        dbc.Label("Select action", html_for="example-password"),
        dcc.Dropdown(id='action-dropdown', multi=False),
        dbc.FormText(
            "You can select multiple actions.", color="secondary"
        ),
    ]
)

manual_action_instance = dbc.Row(
    [
        dbc.Col(action_input, width=2),
        dbc.Col(
            html.Div(
                [
                    dbc.Label("Select Action Range", html_for="range-slider"),
                    dcc.RangeSlider(id='action-time-slider',
                                    min=1, max=100, value=[1, 5]),
                    dbc.FormText(id='output-action-time-slider')
                ]
            ), width=8),
        dbc.Col(button(add_action_instance_title,
                show_title_maker, show_button_id), width="auto"),
        dcc.ConfirmDialog(
            id='confirm-add-action-instance',
            message='Action pattern is added.',
        ),
    ],
    className="h-25",
)

dashboard_buttons = [
    button(set_default_config_title, show_title_maker, show_button_id),
    button(update_action_title, show_title_maker, show_button_id),
]

control_buttons = [
    button(start_title, show_title_maker, show_button_id),
    button(move_forward_title, show_title_maker, show_button_id),
]

show_impacted_objects_title = 'show impacted object types'
show_impacted_functions_title = 'show impacted functions'
show_impacted_object_instances_title = 'show impacted object instances'
show_impacted_function_instances_title = 'show impacted function instances'

pre_impact_content = dbc.Row(
    [
        dbc.Col(
            id='conf-obj-impact',
            children=[
                dcc.Dropdown(id='conf-obj-impact-dropdown'),
                daq.LEDDisplay(
                    id='conf-obj-impact-display',
                    value=0
                ),
                html.Div(
                    [
                        button(show_impacted_objects_title, show_title_maker,
                               show_button_id),
                        dbc.Collapse(
                            dbc.Card(dbc.CardBody(
                                "This content is hidden in the collapse"), id="conf-obj-impact-collapse-body"
                            ),
                            id="conf-obj-impact-collapse",
                            is_open=False,
                        ),
                    ]
                ),
            ], width=3
        ),
        dbc.Col(
            id='conf-func-impact',
            children=[
                dcc.Dropdown(id='conf-func-impact-dropdown'),
                daq.LEDDisplay(
                    id='conf-func-impact-display',
                    value=0
                ),
                html.Div(
                    [
                        button(show_impacted_functions_title, show_title_maker,
                               show_button_id),
                        dbc.Collapse(
                            dbc.Card(dbc.CardBody(
                                "This content is hidden in the collapse"), id="conf-func-impact-collapse-body"
                            ),
                            id="conf-func-impact-collapse",
                            is_open=False,
                        ),
                    ]
                ),

            ],
            width=3
        ),
        dbc.Col(
            id='run-object-impact',
            children=[
                dcc.Dropdown(id='run-obj-impact-dropdown'),
                daq.LEDDisplay(
                    id='run-obj-impact-display',
                    value=0
                ),
                html.Div(
                    [
                        button(show_impacted_object_instances_title, show_title_maker,
                               show_button_id),
                        dbc.Collapse(
                            dbc.Card(dbc.CardBody(
                                "This content is hidden in the collapse"), id="run-obj-impact-collapse-body"
                            ),
                            id="run-obj-impact-collapse",
                            is_open=False,
                        ),
                    ]
                ),
            ],
            width=3
        ),
        dbc.Col(
            id='run-function-impact',
            children=[
                dcc.Dropdown(id='run-func-impact-dropdown'),
                daq.LEDDisplay(
                    id='run-func-impact-display',
                    value=0
                ),
                html.Div(
                    [
                        button(show_impacted_function_instances_title, show_title_maker,
                               show_button_id),
                        dbc.Collapse(
                            dbc.Card(dbc.CardBody(
                                "This content is hidden in the collapse"), id="run-func-impact-collapse-body"
                            ),
                            id="run-func-impact-collapse",
                            is_open=False,
                        ),
                    ]
                ),
            ],
            width=3
        ),
    ]
)

post_impact_content = dbc.Row(
    [
        dbc.Col(
            id='obj-perf-impact',
            children=[
                dcc.Dropdown(id='object-perf-dropdown'),
                dcc.Dropdown(id='object-dropdown'),
                dcc.Dropdown(id='object-diag-dropdown'),
                daq.LEDDisplay(
                    id='obj-perf-impact-display',
                    value=0
                )
            ], width=4
        ),
        dbc.Col(
            id='func-perf-impact',
            children=[
                dcc.Dropdown(id='function-perf-dropdown'),
                dcc.Dropdown(id='function-dropdown'),
                dcc.Dropdown(id='function-diag-dropdown'),
                daq.LEDDisplay(
                    id='func-perf-impact-display',
                    value=0
                )
            ],
            width=3
        ),
    ]
)

impact_analysis_tabs = dbc.Tabs(
    [
        dbc.Tab(pre_impact_content, label="Pre-Action Impact Analysis"),
        dbc.Tab(post_impact_content, label="Post-Action Impact Analysis")
    ]
)

dashboard_content = dbc.Row(
    [
        dcc.Store(id='ocpn-operational-view-dot',
                  storage_type='session', data=""),
        dcc.Store(id='start-time', storage_type='session'),
        dcc.Store(id='step-size', storage_type='session', data=24),
        dcc.Store(id='num-step', storage_type='session', data=100),
        dcc.Store(id='click-data', storage_type='session'),
        dcc.Store(id='default-config-dir', storage_type='session'),
        dcc.Store(id='next-simulation-count', storage_type='session'),
        dcc.Store(id='timeline-data', storage_type='session'),
        dbc.Col(impact_analysis_tabs, width=12)
    ],
    className="h-25",
    # style=dict(position="absolute", height="100%",
    #            width="100%", display="flex"),
)

operation_content = dbc.Row(
    dash_table.DataTable(
        id='operation-table', columns=[]
    ), justify='center'
)

page_layout = container('Dashboard & Impact Analysis',
                        [
                            html.H2("Dashboard Control"),
                            single_row(html.Div(dashboard_buttons)),
                            html.Hr(),
                            html.H2("Simulation Control"),
                            dbc.Row([
                                dbc.Col(step_size_slider, width=6),
                                dbc.Col(num_step_slider, width=6),
                            ]),
                            single_row(html.Div(control_buttons)),
                            html.Div(id='current-timestamp',
                                     style={'display': 'none'}),
                            html.Hr(),
                            html.H2("Add Action Instance"),
                            manual_action_instance,
                            html.Hr(),
                            html.H2("Timeline"),
                            dcc.Graph(
                                id="timeline-graph"),
                            html.Hr(),
                            html.H2("Impact Analysis"),
                            dashboard_content,
                            html.Hr(),
                            html.H2("Operation Records"),
                            operation_content
                        ]
                        )


def awrite(writer, data):
    writer.write(data)
    # await writer.drain()
    writer.flush()


@app.callback(
    Output('interval-component', 'disabled'),
    Output('start-time', 'data'),
    Output('current-timestamp', 'children'),
    Output('next-simulation-count', 'data'),
    Input(show_button_id(start_title), 'n_clicks'),
    Input(show_button_id(move_forward_title), 'n_clicks'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    State('start-time', 'data'),
    State('interval-component', 'disabled'),
    State('interval-component', 'interval'),
    State('interval-component', 'n_intervals'),
    State('step-size', 'data'),
    State('action-pattern-repository', 'data'),
    State('next-simulation-count', 'data'),
)
def callback_control_simulation(n_start, n_stop, value, dashboard_jobs, start_time, disabled, interval, n_intervals, step_size, action_pattern_repo, next_sim_count):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']
    if button_id == show_button_id(start_title):
        proc = get_proc()
        awrite(proc.stdin, b"start\n")
        return True, datetime.now().strftime(time_utils.DATETIME_FORMAT), datetime.now().strftime(time_utils.DATETIME_FORMAT), 0
    elif button_id == show_button_id(move_forward_title):
        proc = get_proc()
        awrite(proc.stdin, b"resume\n")
        start_timestamp = datetime.strptime(
            start_time, time_utils.DATETIME_FORMAT) + timedelta(hours=interval/1000*n_intervals-step_size)
        start_timestamp = time_utils.make_timezone_aware(start_timestamp)
        end_timestamp = datetime.strptime(
            start_time, time_utils.DATETIME_FORMAT) + timedelta(hours=interval/1000*n_intervals)
        end_timestamp = time_utils.make_timezone_aware(end_timestamp)

        return True, dash.no_update, end_timestamp.strftime(time_utils.DATETIME_FORMAT), next_sim_count+1
    return no_update(4)


@app.callback(
    Output('output-action-time-slider', 'children'),
    Input('action-time-slider', 'value')
)
def update_action_time(action_time_value):
    return 'The action will be efective from {} to {}'.format(action_time_value[0], action_time_value[1])


@app.callback(
    Output('output-step-size-slider', 'children'),
    Output('interval-component', 'interval'),
    Output('step-size', 'data'),
    Input('step-size-slider', 'value')
)
def update_step_size(value):
    return 'Each step moves forward {} hours.'.format(value), value*1000, value


@app.callback(
    Output('output-num-step-slider', 'children'),
    Output('num-step', 'data'),
    Input('num-step-slider', 'value')
)
def update_step_size(value):
    return f'Simulation continues up to {value} steps', value


@ app.callback(
    Output(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    Output('timeline-data', 'data'),
    Output('operation-table', 'columns'),
    Output('operation-table', 'data'),
    Output('token-map', 'data'),
    Output('action-dropdown', 'options'),
    Input(show_button_id(set_default_config_title), 'n_clicks'),
    Input(show_button_id(add_action_instance_title), 'n_clicks'),
    Input(show_button_id(update_action_title), 'n_clicks'),
    Input('next-simulation-count', 'data'),
    State('action-definition', 'data'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DESIGN_TITLE), 'data'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    State('action-dropdown', 'value'),
    State('action-time-slider', 'value'),
    State('timeline-data', 'data'),
    State('log-dir', 'data'),
    State('start-time', 'data'),
    State('step-size', 'data'),
    State('num-step', 'data'),
    State('config-dir', 'data')
)
def callback_set_default_config(n_default, n_add, n_action, next_sim_count, action_definition, value, design_jobs, dashboard_jobs, selected_action_name, action_time_value, timeline_data, log_dir, start_time, step_size, num_step, config_dir):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']
    if button_value is not None:
        if button_id == show_button_id(set_default_config_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            dt = get_remote_data(user, log_hash, design_jobs,
                                 AvailableTasks.DESIGN.value)
            conf_valves, conf_activity_variants = read_config(config_dir)
            for valve in conf_valves:
                dt.update_valve(valve, conf_valves[valve])

            for tr_name in conf_activity_variants.keys():
                dt.update_acvitiy_variant(
                    tr_name, conf_activity_variants[tr_name][ACTIVITY_VARIANT_NAME])
            # dt.action_engine.clear_action_instances()
            task_id = run_task(
                design_jobs, log_hash, AvailableTasks.SIMULATE.value, store_redis_backend, data=dt)
            ft = datetime.strptime(
                start_time, time_utils.DATETIME_FORMAT) + timedelta(days=num_step)
            timeline_data = [
                dict(Task="Simulation", Start=start_time, Finish=ft.strftime(time_utils.DATETIME_FORMAT), InstanceName='Simulation')]
            return design_jobs, timeline_data, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        elif button_id == show_button_id(add_action_instance_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            dt = get_remote_data(user, log_hash, dashboard_jobs,
                                 AvailableTasks.SIMULATE.value)
            ai = dt.action_engine.add_action_instance(
                selected_action_name, action_time_value[0], action_time_value[1])
            task_id = run_task(
                dashboard_jobs, log_hash, AvailableTasks.SIMULATE.value, store_redis_backend, data=dt)
            st = datetime.strptime(start_time, time_utils.DATETIME_FORMAT) + \
                timedelta(hours=ai.start*step_size)
            ft = datetime.strptime(start_time, time_utils.DATETIME_FORMAT) + \
                timedelta(hours=ai.end*step_size)
            timeline_data.append(dict(
                Task=ai.action.name, Start=st.strftime(time_utils.DATETIME_FORMAT), Finish=ft.strftime(time_utils.DATETIME_FORMAT), InstanceName=ai.name))
            return dashboard_jobs, timeline_data, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        elif button_id == 'next-simulation-count' and next_sim_count > 0:
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            dt = get_remote_data(user, log_hash, dashboard_jobs,
                                 AvailableTasks.SIMULATE.value)
            # update operational views
            print("streaming event data from {}".format(log_dir))
            data = ocel_import_factory.apply(log_dir)
            event_df = data[0]
            sublog = event_df
            if len(sublog) == 0:
                print("no events")
            dt.marking = oper_factory.apply(dt.ocpn, sublog, dt.marking)
            token_map = {}
            for pl, oi in dt.marking.tokens:
                if pl.name not in token_map.keys():
                    token_map[pl.name] = [oi]
                else:
                    token_map[pl.name].append(oi)
            operation_table_columns = [{"name": i, "id": i}
                                       for i in sublog.columns]
            operation_table_data = sublog.to_dict('records')

            # apply action instance & compute pre impacts
            dt.action_engine.apply_action_instance(
                dt, next_sim_count, event_df)

            task_id = run_task(
                dashboard_jobs, log_hash, AvailableTasks.SIMULATE.value, store_redis_backend, data=dt)

            return dashboard_jobs, dash.no_update, operation_table_columns, operation_table_data, json.dumps(token_map), dash.no_update
        elif button_id == show_button_id(update_action_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            dt = get_remote_data(user, log_hash, dashboard_jobs,
                                 AvailableTasks.SIMULATE.value)
            for action_name in action_definition:
                if action_name not in [a.name for a in dt.action_engine.action_repo]:
                    edit_valves = action_definition[action_name]["valves"]
                    edit_activity_variants = action_definition[action_name]["activity_variants"]
                    valve_actions = []
                    for valve in edit_valves:
                        valve_action = ValveAction(valve, edit_valves[valve])
                        valve_actions.append(valve_action)

                    activity_variant_actions = []
                    for edit_variant in edit_activity_variants:
                        activity_variant_action = ActivityVariantAction(
                            edit_variant[ACTIVITY_VARIANT_TR_NAME], edit_variant[ACTIVITY_VARIANT_NAME])
                        activity_variant_actions.append(
                            activity_variant_action)

                    action = StaticAction(name=action_name, valve_actions=valve_actions,
                                          activity_variant_actions=activity_variant_actions)
                    dt.action_engine.add_action(action)
            task_id = run_task(
                dashboard_jobs, log_hash, AvailableTasks.SIMULATE.value, store_redis_backend, data=dt)
            action_options = [{'label': action.name,
                               'value': action.name} for action in dt.action_engine.action_repo]
            return dashboard_jobs, *no_update(4), action_options
        else:
            return no_update(6)
    else:
        return no_update(6)


@app.callback(
    Output('timeline-graph', 'figure'),
    Input('timeline-data', 'data'),
    Input('next-simulation-count', 'data'),
)
def update_timeline_graph(timeline_data, next_sim_count):
    if timeline_data is not None:
        return impact_visualizer.draw_gannt_chart(timeline_data, next_sim_count)
    else:
        dash.no_update


@app.callback(
    Output('click-data', 'data'),
    Input('timeline-graph', 'clickData'),
)
def update_click_data(click_data):
    if click_data is not None:
        return click_data
    else:
        return dash.no_update


@app.callback(
    Output('conf-obj-impact-dropdown', 'options'),
    Output('conf-obj-impact-dropdown', 'value'),
    Output('conf-func-impact-dropdown', 'options'),
    Output('conf-func-impact-dropdown', 'value'),
    Output('run-obj-impact-dropdown', 'options'),
    Output('run-obj-impact-dropdown', 'value'),
    Output('run-func-impact-dropdown', 'options'),
    Output('run-func-impact-dropdown', 'value'),
    Output('object-dropdown', 'options'),
    Output('object-dropdown', 'value'),
    Output('object-perf-dropdown', 'options'),
    Output('object-perf-dropdown', 'value'),
    Output('function-dropdown', 'options'),
    Output('function-dropdown', 'value'),
    Output('function-perf-dropdown', 'options'),
    Output('function-perf-dropdown', 'value'),
    Input('timeline-graph', 'clickData'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    State('timeline-graph', 'figure'),
)
def update_impact_analysis_panel(click_data, value, dashboard_jobs, figure):
    if click_data is not None:
        conf_obj_options = [{'label': metric.value, 'value': metric.value}
                            for metric in AvailableConfObjImpact]
        conf_obj_value = list(AvailableConfObjImpact)[0].value

        conf_func_options = [{'label': metric.value, 'value': metric.value}
                             for metric in AvailableConfFuncImpact]
        conf_func_value = list(AvailableConfFuncImpact)[0].value

        run_obj_options = [{'label': metric.value, 'value': metric.value}
                           for metric in AvailableRunObjImpact]
        run_obj_value = list(AvailableRunObjImpact)[0].value

        run_func_options = [{'label': metric.value, 'value': metric.value}
                            for metric in AvailableRunFuncImpact]
        run_func_value = list(AvailableRunFuncImpact)[0].value

        obj_perf_options = [{'label': metric.value, 'value': metric.value}
                            for metric in AvailableObjPerformanceMetric]
        obj_perf_value = list(AvailableObjPerformanceMetric)[0].value

        func_perf_options = [{'label': metric.value, 'value': metric.value}
                             for metric in AvailableFuncPerformanceMetric]
        func_perf_value = list(AvailableFuncPerformanceMetric)[0].value

        log_hash, date = read_global_signal_value(value)
        user = request.authorization['username']
        dt = get_remote_data(user, log_hash, dashboard_jobs,
                             AvailableTasks.SIMULATE.value)
        action_instance_name = click_data["points"][0]['text']
        ai = dt.action_engine.get_action_instance(
            action_instance_name)
        if ai.post_obj_impact is not None:
            obj_options = [{'label': ot, 'value': ot}
                           for ot in ai.impacted_objects]
            # obj_value = obj_types[0]

            func_options = [{'label': tr.name, 'value': tr.name}
                            for tr in ai.impacted_functions]
            # func_value = funcs[0]

            return conf_obj_options, conf_obj_value, conf_func_options, conf_func_value, run_obj_options, run_obj_value, run_func_options, run_func_value, obj_options, dash.no_update, obj_perf_options, obj_perf_value, func_options, dash.no_update, func_perf_options, func_perf_value
        else:
            return conf_obj_options, conf_obj_value, conf_func_options, conf_func_value, run_obj_options, run_obj_value, run_func_options, run_func_value, *no_update(8)

    return no_update(16)


@app.callback(
    Output('object-diag-dropdown', 'options'),
    # Output('object-diag-dropdown', 'value'),
    Input('object-dropdown', 'value'),
    Input('object-perf-dropdown', 'value'),
    State('timeline-graph', 'clickData'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
)
def update_impact_analysis_panel(obj, obj_perf, click_data, value, dashboard_jobs):
    log_hash, date = read_global_signal_value(value)
    user = request.authorization['username']
    dt = get_remote_data(user, log_hash, dashboard_jobs,
                         AvailableTasks.SIMULATE.value)
    action_instance_name = click_data["points"][0]['text']
    ai = dt.action_engine.get_action_instance(
        action_instance_name)
    if obj is not None:
        obj_diag_options = [{'label': d, 'value': d}
                            for d in ai.get_obj_impact_diagnostics(obj, obj_perf)]

        return obj_diag_options
    else:
        return dash.no_update


@app.callback(
    Output('function-diag-dropdown', 'options'),
    # Output('object-diag-dropdown', 'value'),
    Input('function-dropdown', 'value'),
    Input('function-perf-dropdown', 'value'),
    State('timeline-graph', 'clickData'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
)
def update_impact_analysis_panel(func, func_perf, click_data, value, dashboard_jobs):
    log_hash, date = read_global_signal_value(value)
    user = request.authorization['username']
    dt = get_remote_data(user, log_hash, dashboard_jobs,
                         AvailableTasks.SIMULATE.value)
    action_instance_name = click_data["points"][0]['text']
    ai = dt.action_engine.get_action_instance(
        action_instance_name)
    if func is not None:
        func_diag_options = [{'label': d, 'value': d}
                             for d in ai.get_func_impact_diagnostics(func, func_perf)]

        return func_diag_options
    else:
        return dash.no_update


@app.callback(
    Output('conf-obj-impact-display', 'value'),
    Output('conf-func-impact-display', 'value'),
    Output('run-obj-impact-display', 'value'),
    Output('run-func-impact-display', 'value'),
    Output('conf-obj-impact-collapse-body', 'children'),
    Output('conf-func-impact-collapse-body', 'children'),
    Output('run-obj-impact-collapse-body', 'children'),
    Output('run-func-impact-collapse-body', 'children'),
    Input('conf-obj-impact-dropdown', 'value'),
    Input('conf-func-impact-dropdown', 'value'),
    Input('run-obj-impact-dropdown', 'value'),
    Input('run-func-impact-dropdown', 'value'),
    State('timeline-graph', 'clickData'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
)
def update_pre_impact_analysis(conf_obj_metric, conf_func_metric, run_obj_metric, run_func_metric, click_data, value, dashboard_jobs):
    if click_data is not None:
        log_hash, date = read_global_signal_value(value)
        user = request.authorization['username']
        dt = get_remote_data(user, log_hash, dashboard_jobs,
                             AvailableTasks.SIMULATE.value)
        action_instance_name = click_data["points"][0]['text']
        ai = dt.action_engine.get_action_instance(
            action_instance_name)
        return ai.pre_impact[conf_obj_metric], ai.pre_impact[conf_func_metric], ai.pre_impact[run_obj_metric], ai.pre_impact[run_func_metric], \
            dcc.Checklist(
                options=[
                    {'label': obj, 'value': obj} for obj in ai.impacted_objects
                ],
                value=[obj for obj in ai.impacted_objects]
        ), \
            dcc.Checklist(
                options=[
                    {'label': tr.name, 'value': tr.name} for tr in ai.impacted_functions
                ],
                value=[tr.name for tr in ai.impacted_functions]
        ), \
            dcc.Checklist(
                options=[
                    {'label': obj, 'value': obj} for obj in ai.impacted_obj_instances
                ],
                value=[obj for obj in ai.impacted_obj_instances]
        ), \
            dcc.Checklist(
                options=[
                    {'label': obj, 'value': obj} for obj in ai.impacted_func_instances
                ],
                value=[obj for obj in ai.impacted_func_instances]
        )

    return no_update(5)


@app.callback(
    Output('obj-perf-impact-display', 'value'),
    Input('object-dropdown', 'value'),
    Input('object-perf-dropdown', 'value'),
    State('timeline-graph', 'clickData'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    State('timeline-graph', 'figure'),
)
def update_obj_post_impact_analysis(obj_type, obj_perf_metric, click_data, value, dashboard_jobs, figure):
    if click_data is not None:
        if obj_type is not None and obj_perf_metric is not None:
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            dt = get_remote_data(user, log_hash, dashboard_jobs,
                                 AvailableTasks.SIMULATE.value)
            action_instance_name = click_data["points"][0]['text']
            ai = dt.action_engine.get_action_instance(
                action_instance_name)
            if ai.post_obj_impact is not None:
                replay_metric = REPLAY_DIAGNOSTICS_MAP[obj_perf_metric]
                return ai.post_obj_impact[replay_metric][obj_type]
            else:
                dash.no_update
        else:
            dash.no_update
    return dash.no_update


@app.callback(
    Output('func-perf-impact-display', 'value'),
    Input('function-diag-dropdown', 'value'),
    State('function-dropdown', 'value'),
    State('function-perf-dropdown', 'value'),
    State('timeline-graph', 'clickData'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    State('timeline-graph', 'figure'),
)
def update_func_post_impact_analysis(func_diag, func, func_perf_metric, click_data, value, dashboard_jobs, figure):
    if click_data is not None:
        if func_diag is not None and func_perf_metric is not None:
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            dt = get_remote_data(user, log_hash, dashboard_jobs,
                                 AvailableTasks.SIMULATE.value)
            action_instance_name = click_data["points"][0]['text']
            ai = dt.action_engine.get_action_instance(
                action_instance_name)
            if ai.post_func_impact is not None:
                return ai.post_func_impact[func_perf_metric][func_diag]
            else:
                dash.no_update
        else:
            dash.no_update

    return dash.no_update


@app.callback(
    Output("conf-obj-impact-collapse", "is_open"),
    Input(show_button_id(show_impacted_objects_title), 'n_clicks'),
    [State("conf-obj-impact-collapse", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


@app.callback(
    Output("conf-func-impact-collapse", "is_open"),
    Input(show_button_id(show_impacted_functions_title), 'n_clicks'),
    [State("conf-func-impact-collapse", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


@app.callback(
    Output("run-obj-impact-collapse", "is_open"),
    Input(show_button_id(show_impacted_object_instances_title), 'n_clicks'),
    [State("run-obj-impact-collapse", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


@app.callback(
    Output("run-func-impact-collapse", "is_open"),
    Input(show_button_id(show_impacted_function_instances_title), 'n_clicks'),
    [State("run-func-impact-collapse", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open
