import hashlib
import base64
from datetime import date
import re
import time

from backend.components.misc import container, single_row, button, show_title_maker, show_button_id, global_signal_id_maker, temp_jobs_store_id_maker, global_form_load_signal_id_maker
import dash_interactive_graphviz
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from backend.app import app
import pandas as pd
import dash
from backend.param.constants import DESIGN_TITLE, PERF_ANALYSIS_TITLE, GLOBAL_FORM_SIGNAL, PERF_ANALYSIS_URL, PARSE_TITLE
from dtween.util.util import PERF_METRIC_NAME_MAP, AGG_NAME_MAP
from dtween.available.constants import COMP_OPERATORS

from ocpa.visualization.oc_petri_net import factory as ocpn_vis_factory
from backend.util import add_job, run_task, forget_all_tasks, get_job_id, check_existing_job, read_global_signal_value, read_active_attribute_form, write_global_signal_value, no_update
from backend.tasks.tasks import get_remote_data
from dtween.available.available import AvailableTasks, AvailablePerformanceMetric, AvailableAggregators
from ocpa.objects.log.converter.versions import jsonocel_to_mdl as ocel_to_mdl_factory
import dash_core_components as dcc
from ocpa.objects.oc_petri_net.obj import Subprocess

from dateutil import parser
from flask import request

from ocpa.algo.projection.ocpn import algorithm as ocpn_project_factory
from ocpa.algo.filtering.graph.event_graph import algorithm as event_graph_filtering_factory
from ocpa.algo.enhancement.event_graph_based_performance import algorithm as performance_factory
from ocpa.objects.graph.event_graph.retrieval import algorithm as event_graph_factory
from ocpa.objects.graph.correlated_event_graph.retrieval import algorithm as correlated_event_graph_factory
from ocpa.algo.enhancement.event_graph_based_performance import algorithm as performance_factory

import pickle
import redis
from time import sleep
from backend.param.settings import CeleryConfig, redis_pwd

CELERY_TIMEOUT = 21600

proj_ocpn_id = "current-projected-ocpn"
original_cegs_id = "current-original-cegs"
filtered_cegs_id = "current-filtered-cegs"
subprocess_id = "current-subprocess"


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


initial_ocpn_buttion_title = "show model".title()
projection_button_title = "project model".title()
build_button_title = "build event graph".title()
clear_button_title = "clear".title()
compute_button_title = "compute".title()

buttons = [
    button(initial_ocpn_buttion_title, show_title_maker, show_button_id),
    button(projection_button_title, show_title_maker, show_button_id),
    button(build_button_title, show_title_maker, show_button_id)
]

diagnostics_date_picker = html.Div([
    dcc.Store(id='perf-analysis-start', storage_type='session', data=""),
    dcc.Store(id='perf-analysis-end', storage_type='session', data=""),
    dcc.Store(id='perf-analysis-duration', storage_type='session'),
    dcc.Store(id='perf-analysis-list', storage_type='session'),
    dbc.Label("Time Period"),
    html.Br(),
    dcc.DatePickerRange(
        id='perf-analysis-date-picker-range',
        min_date_allowed=date(1995, 8, 5),
        max_date_allowed=date(2017, 9, 19),
        initial_visible_month=date(2017, 8, 5),
        end_date=date(2017, 8, 25),
        display_format='YYYY-MM-DD',
    ),
    dbc.FormText(
        html.Div(id='perf-analysis-output-container-date-picker-range'),
        color="secondary",
    ),
])

diagnostics_input = html.Div(
    [
        dbc.Label("Object-centric Performance Metric"),
        dcc.Dropdown(id='performance-metrics-dropdown', options=[
                     {'label': x, 'value': x} for x in [e.value for e in AvailablePerformanceMetric]]),
        dbc.FormText(
            "Select a performance metric of your interest",
            color="secondary",
        ),
    ]
)

aggregator_input = html.Div(
    [
        dbc.Label("Aggregation"),
        dcc.Dropdown(id='aggregator-dropdown',
                     options=[{'label': x, 'value': x} for x in [e.value for e in AvailableAggregators]]),
        dbc.FormText(
            "Select a type of aggregation",
            color="secondary",
        ),
    ]
)

object_projection_input = html.Div(
    [
        dbc.Label("Select object types", html_for="example-password"),
        dcc.Dropdown(id='object-proj-dropdown', multi=True),
        dbc.FormText(
            "You can select multiple conditions.", color="secondary"
        ),
    ]
)

subprocess_projection_input = html.Div(
    [
        dbc.Label("Select activities", html_for="example-password"),
        dcc.Dropdown(id='subprocess-proj-dropdown', multi=True),
        dbc.FormText(
            "You can select multiple actions.", color="secondary"
        ),
    ]
)

ocpn_projection_panel = dbc.Row(
    [
        dbc.Col(object_projection_input),
        dbc.Col(subprocess_projection_input),
    ]
)

perf_analysis_content = dbc.Row(
    [
        dcc.Store(id='ocpn-perf-analysis-dot',
                  storage_type='session', data=""),
        dcc.Store(id='projected-ocpn-dot', storage_type='session', data=""),
        dbc.Col(
            dash_interactive_graphviz.DashInteractiveGraphviz(id="perf-analysis-gv"), width=8
        ),
        dbc.Col(
            [
                html.H3("Performance Analysis"),
                html.Hr(),
                diagnostics_date_picker,
                html.Hr(),
                diagnostics_input,
                aggregator_input,
                html.Hr(),
                button(compute_button_title,
                       show_title_maker, show_button_id),
                html.Br(),
                dbc.Alert(children="", id="performance-output",
                          is_open=False, color="success"),
            ],
            width=4
        ),
    ],
    style=dict(position="absolute", height="100%",
               width="100%", display="flex"),
)

page_layout = container('Object-Centric Performance Analysis',
                        [
                            single_row(html.Div(buttons)),
                            ocpn_projection_panel,
                            perf_analysis_content
                        ]
                        )


@ app.callback(
    Output("perf-analysis-gv", "dot_source"),
    Output("perf-analysis-gv", "engine"),
    Input('url', 'pathname'),
    Input("ocpn-perf-analysis-dot", "data")
)
def show_ocpn(pathname, value):
    if pathname == PERF_ANALYSIS_URL and value is not None:
        return value, "dot"
    return no_update(2)


@app.callback(
    Output("perf-analysis-date-picker-range", "min_date_allowed"),
    Output("perf-analysis-date-picker-range", "max_date_allowed"),
    Output("perf-analysis-date-picker-range", "initial_visible_month"),
    Output("perf-analysis-date-picker-range", "start_date"),
    Output("perf-analysis-date-picker-range", "end_date"),
    Input('url', 'pathname'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(global_signal_id_maker(PARSE_TITLE), 'children'),
    State(temp_jobs_store_id_maker(PARSE_TITLE), 'data'),
)
def initialize_date(pathname, value, old_value, data_jobs):
    if pathname == PERF_ANALYSIS_URL and (value is not None or old_value is not None):
        if value is None:
            value = old_value
        log_hash, date = read_global_signal_value(value)
        user = request.authorization['username']
        data = get_remote_data(user, log_hash, data_jobs,
                               AvailableTasks.PARSE.value)
        eve_df, obj_df = ocel_to_mdl_factory.apply(data)
        min_date = min(eve_df['event_timestamp']).to_pydatetime().date()
        max_date = max(eve_df['event_timestamp']).to_pydatetime().date()
        return min_date, max_date, max_date, min_date, max_date
    return no_update(5)


@app.callback(
    Output('ocpn-perf-analysis-dot', 'data'),
    Output("object-proj-dropdown", "options"),
    Output("subprocess-proj-dropdown", "options"),
    Output('subprocess-proj-dropdown', 'value'),
    Input(show_button_id(initial_ocpn_buttion_title), 'n_clicks'),
    Input(show_button_id(projection_button_title), 'n_clicks'),
    Input(show_button_id(build_button_title), 'n_clicks'),
    Input("perf-analysis-gv", "selected_node"),
    Input("perf-analysis-gv", "selected_edge"),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(global_signal_id_maker(PARSE_TITLE), 'children'),
    State(temp_jobs_store_id_maker(PARSE_TITLE), 'data'),
    State(temp_jobs_store_id_maker(DESIGN_TITLE), 'data'),
    State('object-proj-dropdown', 'value'),
    State('subprocess-proj-dropdown', 'value'),
)
def load_initial_ocpn(n_show_orig_ocpn, n_show_proj_ocpn, n_build_eg, selected_node, selected_edge, value, old_value, data_jobs, control_jobs, object_proj_values, subprocess_proj_values):
    ctx = dash.callback_context
    if not ctx.triggered:
        click_id = 'No clicks yet'
        click_value = None
    else:
        click_id = ctx.triggered[0]['prop_id'].split('.')[0]
        click_value = ctx.triggered[0]['value']
        if value is None:
            value = old_value

    if click_value is not None:
        if click_id == show_button_id(initial_ocpn_buttion_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            ocpn = get_remote_data(user, log_hash, control_jobs,
                                   AvailableTasks.DESIGN.value)

            object_types = ocpn.object_types
            ot_options = [{'label': ot,
                           'value': ot} for ot in object_types]
            transition_labels = [t.name for t in ocpn.transitions]
            act_options = [{'label': act,
                            'value': act} for act in transition_labels]

            parameters = dict()
            parameters['format'] = 'svg'
            gviz = ocpn_vis_factory.apply(
                ocpn, variant="control_flow", parameters=parameters)
            ocpn_diagnostics_dot = str(gviz)

            # TODO store ocpn
            # store_redis(cegs, filtered_task_id)

            return ocpn_diagnostics_dot, ot_options, act_options, dash.no_update

        if click_id == show_button_id(build_button_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']

            data = get_remote_data(user, log_hash, data_jobs,
                                   AvailableTasks.PARSE.value)
            print("Start building EG")
            st = time.time()
            eg = event_graph_factory.apply(data)
            et = time.time()
            print("End building EG: {}".format(et-st))
            print("Start building CEGs")
            st2 = time.time()
            cegs = correlated_event_graph_factory.apply(eg)
            et2 = time.time()
            print("End building CEGs: {}".format(et2-st2))
            store_redis(cegs, original_cegs_id)
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

        elif click_id == show_button_id(projection_button_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            ocpn = get_remote_data(user, log_hash, control_jobs,
                                   AvailableTasks.DESIGN.value)
            sp = Subprocess(ocpn, object_proj_values, subprocess_proj_values)
            store_redis(sp, subprocess_id)

            print("Start projection: {} and {}".format(
                ocpn.object_types, ocpn.transitions))
            st = time.time()
            if sp.object_types != None and len(sp.object_types) != 0:
                ot_proj_parameters = dict()
                ot_proj_parameters['selected_object_types'] = list(
                    sp.object_types)
                temp_proj_ocpn = ocpn_project_factory.apply(
                    ocpn, variant="object_types", parameters=ot_proj_parameters)
            else:
                temp_proj_ocpn = ocpn

            if sp.transitions != None and len(sp.transitions) != 0:
                sp_proj_parameters = dict()
                sp_proj_parameters['selected_transitions'] = sp.transitions
                temp_proj_ocpn = ocpn_project_factory.apply(
                    temp_proj_ocpn, variant="hiding", parameters=sp_proj_parameters)
            et = time.time()
            print("End projection: {}".format(et-st))

            proj_ocpn = temp_proj_ocpn
            store_redis(proj_ocpn, proj_ocpn_id)

            vis_parameters = dict()
            vis_parameters['format'] = 'svg'
            proj_gviz = ocpn_vis_factory.apply(
                proj_ocpn, variant="control_flow", parameters=vis_parameters)
            proj_ocpn_dot = str(proj_gviz)
            return proj_ocpn_dot, dash.no_update, dash.no_update, dash.no_update
        # selecting transitions by clicking the visualization
        elif click_id == "perf-analysis-gv":
            tr_label = click_value
            if subprocess_proj_values is None:
                subprocess_proj_values = [tr_label]
            else:
                if tr_label not in subprocess_proj_values:
                    subprocess_proj_values.append(tr_label)
            return dash.no_update, dash.no_update, dash.no_update, subprocess_proj_values
    return no_update(4)


@app.callback(
    Output('perf-analysis-output-container-date-picker-range', 'children'),
    Output('perf-analysis-start', 'data'),
    Output('perf-analysis-end', 'data'),
    Input('perf-analysis-date-picker-range', 'start_date'),
    Input('perf-analysis-date-picker-range', 'end_date')
)
def select_date(start_date, end_date):
    string_prefix = 'You have selected: '
    start_date_string = ""
    end_date_string = ""
    if start_date is not None:
        # start_date_object = date.fromisoformat(start_date)
        # start_date_string = start_date_object.strftime('%B %d, %Y')
        start_date_object = date.fromisoformat(start_date)
        start_date_string = start_date_object.strftime('%Y-%m-%d')
        string_prefix = string_prefix + 'Start Date: ' + start_date_string + ' | '
    if end_date is not None:
        end_date_object = date.fromisoformat(end_date)
        end_date_string = end_date_object.strftime('%Y-%m-%d')
        string_prefix = string_prefix + 'End Date: ' + end_date_string
    if len(string_prefix) == len('You have selected: '):
        return 'Select a date to see it displayed here', start_date_string, end_date_string
    else:
        return string_prefix, start_date_string, end_date_string


@app.callback(
    Output('performance-output', 'children'),
    Output('performance-output', 'is_open'),
    Input(show_button_id(compute_button_title), 'n_clicks'),
    State('performance-metrics-dropdown', 'value'),
    State('aggregator-dropdown', 'value'),
    State('perf-analysis-start', 'data'),
    State('perf-analysis-end', 'data'),
)
def update_output(n, perf_metric_name, agg_name, start_date, end_date):
    if n is not None:
        perf_metric = PERF_METRIC_NAME_MAP[perf_metric_name]
        agg = AGG_NAME_MAP[agg_name]
        duration = parser.parse(end_date) - parser.parse(start_date)
        days, seconds = duration.days, duration.seconds
        hours = days * 24 + seconds // 3600
        print("Start performance analysis: {} and {}".format(perf_metric, agg))

        st = time.time()
        user = request.authorization['username']
        sp = get_redis_data(user, subprocess_id)
        proj_ocpn = get_redis_data(user, proj_ocpn_id)
        original_cegs = get_redis_data(user, original_cegs_id)

        perf_parameters = dict()
        perf_parameters['perf_metric'] = perf_metric
        perf_parameters['agg'] = agg
        perf_parameters['subprocess'] = sp
        result = performance_factory.apply(
            proj_ocpn, original_cegs, parameters=perf_parameters)
        et = time.time()
        print("End performance analysis: {}".format(et-st))

        return "Result: %s" % (result), True
    else:
        return "undefined", False
