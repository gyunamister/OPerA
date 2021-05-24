import hashlib
import base64
import datetime
from datetime import date
import re

from backend.components.misc import container, single_row, button, show_title_maker, show_button_id, global_signal_id_maker, temp_jobs_store_id_maker, global_form_load_signal_id_maker
import dash_interactive_graphviz
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from backend.app import app
import pandas as pd
import dash_table
import dash
from collections import OrderedDict
from backend.param.constants import CVIEW_TITLE, DVIEW_TITLE, GLOBAL_FORM_SIGNAL, DVIEW_URL, HOME_TITLE
from dtwin.available.constants import COMP_OPERATORS

from dtwin.digitaltwin.ocpn.visualization import visualizer as ocpn_vis_factory
from backend.util import add_job, run_task, forget_all_tasks, get_job_id, check_existing_job, read_global_signal_value, read_active_attribute_form, write_global_signal_value, no_update
from backend.tasks.tasks import get_remote_data, generate_diagnostics
from dtwin.available.available import AvailableTasks, AvailablePlaceDiagnostics, AvailableTransitionDiagnostics, AvailableFlowDiagnostics

from dateutil import parser
from flask import request

define_condition_title = "Define Condition"

buttons = [
    button(DVIEW_TITLE, show_title_maker, show_button_id)
]

diagnostics_date_picker = html.Div([
    dcc.Store(id='diagnostics-start', storage_type='session', data=""),
    dcc.Store(id='diagnostics-end', storage_type='session', data=""),
    dcc.DatePickerRange(
        id='my-date-picker-range',
        min_date_allowed=date(1995, 8, 5),
        max_date_allowed=date(2017, 9, 19),
        initial_visible_month=date(2017, 8, 5),
        end_date=date(2017, 8, 25),
        display_format='YYYY-MM-DD',
    ),
    html.Div(id='output-container-date-picker-range')
])

diagnostics_view_content = dbc.Row(
    [
        dcc.ConfirmDialog(
            id='confirm-define-condition',
            message='A condition is defined.',
        ),
        dcc.Store(id='ocpn-diagnostics-dot', storage_type='session', data=""),
        dbc.Col(
            dash_interactive_graphviz.DashInteractiveGraphviz(id="gv-diagnostics"), width=8
        ),
        dbc.Col(
            [
                dbc.Row(
                    dbc.Col(html.H4("Define conditions"))
                ),
                dbc.Row(
                    dbc.Col(html.Div(id="selected-diagnostics"))
                ),
                dbc.Row(
                    dbc.Col(dcc.Dropdown(id='diagnostics-dropdown'))
                ),
                dbc.Row(
                    dbc.Col(dcc.Dropdown(id='comp-operators-dropdown',
                                         options=[{'label': x, 'value': x} for x in COMP_OPERATORS]))
                ),
                dbc.Row(
                    dbc.Col(dcc.Input(id="threshold", type="number",
                                      placeholder="Threshold"))
                ),
                dbc.Row(
                    dbc.Col(dcc.Input(id="condition-specification", type="text",
                                      placeholder="Enter Condition name"))
                ),
                dbc.Row(
                    dbc.Col(button(define_condition_title,
                                   show_title_maker, show_button_id))
                )
            ],
            width=4
        ),
    ],
    style=dict(position="absolute", height="100%",
               width="100%", display="flex"),
)

page_layout = container('Diagnostics View',
                        [
                            diagnostics_date_picker,
                            single_row(html.Div(buttons)),
                            diagnostics_view_content
                        ]
                        )


@app.callback(
    Output("gv-diagnostics", "dot_source"),
    Output("gv-diagnostics", "engine"),
    Input('url', 'pathname'),
    Input("ocpn-diagnostics-dot", "data")
)
def show_ocpn(pathname, value):
    if pathname == DVIEW_URL and value is not None:
        return value, "dot"
    return no_update(2)


@app.callback(
    Output("my-date-picker-range", "min_date_allowed"),
    Output("my-date-picker-range", "max_date_allowed"),
    Output("my-date-picker-range", "initial_visible_month"),
    Output("my-date-picker-range", "end_date"),
    Input('url', 'pathname'),
    State(global_signal_id_maker(HOME_TITLE), 'children'),
    State('jobs-store', 'data'),
)
def update_date(pathname, value, data_jobs):
    if pathname == DVIEW_URL and value is not None:
        log_hash, date = read_global_signal_value(value)
        user = request.authorization['username']
        log = get_remote_data(user, log_hash, data_jobs,
                              AvailableTasks.UPLOAD.value)
        min_date = parser.parse(min(log['event_timestamp'])).date()
        max_date = parser.parse(max(log['event_timestamp'])).date()
        return min_date, max_date, max_date, max_date
    return no_update(4)


@app.callback(
    Output("selected-diagnostics", "children"),
    Output("diagnostics-dropdown", "options"),
    Input("gv-diagnostics", "selected")
)
def show_available_diagnostics(value):
    if value is not None:
        if "p" in value:
            available = [e.value for e in AvailablePlaceDiagnostics]
        elif "t" in value:
            available = [e.value for e in AvailableTransitionDiagnostics]
        else:
            available = [e.value for e in AvailableFlowDiagnostics]
        options = [{'label': x, 'value': x} for x in available]
        return html.Div("Current selection: {}".format(value)), options
    else:
        return html.Div("Current selection: {}".format(value)), []


@app.callback(
    Output(global_signal_id_maker(DVIEW_TITLE), 'children'),
    Output(temp_jobs_store_id_maker(DVIEW_TITLE), 'data'),
    Output('ocpn-diagnostics-dot', 'data'),
    Input(show_button_id(DVIEW_TITLE), 'n_clicks'),
    State(global_signal_id_maker(HOME_TITLE), 'children'),
    State('jobs-store', 'data'),
    State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    State(temp_jobs_store_id_maker(DVIEW_TITLE), 'data'),
    State('diagnostics-start', 'data'),
    State('diagnostics-end', 'data'),
)
def run_generate_diagnostics(n_show, value, data_jobs, control_jobs, temp_jobs, start_date, end_date):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']

    if button_value is not None:
        if button_id == show_button_id(DVIEW_TITLE):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            log = get_remote_data(user, log_hash, data_jobs,
                                  AvailableTasks.UPLOAD.value)
            dt = get_remote_data(user, log_hash, control_jobs,
                                 AvailableTasks.BUILD.value)
            task_id = run_task(
                control_jobs, log_hash, AvailableTasks.DIAGNIZE.value, generate_diagnostics, temp_jobs=temp_jobs, ocpn=dt.ocpn, data=log, start_date=start_date, end_date=end_date)
            diagnostics = get_remote_data(user, log_hash, control_jobs,
                                          AvailableTasks.DIAGNIZE.value)
            gviz = ocpn_vis_factory.apply(dt.ocpn, diagnostics=diagnostics,
                                          variant="annotated_with_diagnostics", parameters={"format": "svg"})
            ocpn_diagnostics_dot = str(gviz)
            return write_global_signal_value([log_hash, task_id]), control_jobs, ocpn_diagnostics_dot
    return no_update(3)


@app.callback(
    Output('output-container-date-picker-range', 'children'),
    Output('diagnostics-start', 'data'),
    Output('diagnostics-end', 'data'),
    Input('my-date-picker-range', 'start_date'),
    Input('my-date-picker-range', 'end_date')
)
def update_output(start_date, end_date):
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
    Output('confirm-define-condition', 'displayed'),
    Output('condition-repository', 'data'),
    Input(show_button_id(define_condition_title), 'n_clicks'),
    State('diagnostics-dropdown', 'value'),
    State('comp-operators-dropdown', 'value'),
    State('threshold', 'value'),
    State('condition-specification', 'value'),
    State('condition-repository', 'data'),
    State("gv-diagnostics", "selected")
)
def update_output(n, diag, operator, threshold, condition_name, condition_repo, selected):
    if n is not None:
        expression = "({}) {} {} {}".format(
            selected, diag, operator, threshold)
        condition_repo.append({"Name": condition_name,
                               "Diagnostics": diag, "Operators": operator, "Threshold": threshold, "Expression": expression})
        print(condition_repo)
        return True, condition_repo
    else:
        return False, condition_repo
