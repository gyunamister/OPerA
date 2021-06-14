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
from backend.param.constants import CVIEW_TITLE, DVIEW_TITLE, GLOBAL_FORM_SIGNAL, DVIEW_URL, HOME_TITLE, PARSE_TITLE
from dtwin.available.constants import COMP_OPERATORS

from dtwin.digitaltwin.ocpn.visualization import visualizer as ocpn_vis_factory
from backend.util import add_job, run_task, forget_all_tasks, get_job_id, check_existing_job, read_global_signal_value, read_active_attribute_form, write_global_signal_value, no_update
from backend.tasks.tasks import get_remote_data, generate_diagnostics
from dtwin.available.available import AvailableTasks, AvailablePlaceDiagnostics, AvailableTransitionDiagnostics, AvailableFlowDiagnostics
from dtwin.digitaltwin.ocel.objects.ocel.converter import factory as ocel_converter_factory

from dateutil import parser
from flask import request

define_condition_title = "Define Condition"

buttons = [
    button(DVIEW_TITLE, show_title_maker, show_button_id)
]

diagnostics_date_picker = html.Div([
    dcc.Store(id='diagnostics-start', storage_type='session', data=""),
    dcc.Store(id='diagnostics-end', storage_type='session', data=""),
    dcc.Store(id='diagnostics-duration', storage_type='session'),
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

diagnostics_input = dbc.FormGroup(
    [
        dbc.Label("Diagnostics"),
        dcc.Dropdown(id='diagnostics-dropdown'),
        dbc.FormText(
            "Select diagnostics of your interest",
            color="secondary",
        ),
    ]
)

comparator_input = dbc.FormGroup(
    [
        dbc.Label("Comparator"),
        dcc.Dropdown(id='comp-operators-dropdown',
                     options=[{'label': x, 'value': x} for x in COMP_OPERATORS]),
        dbc.FormText(
            "Select comparison operator to define condition",
            color="secondary",
        ),
    ]
)

threshold_input = dbc.FormGroup(
    [
        dbc.Label("Threshold"),
        html.Br(),
        dcc.Input(id="threshold", type="number",
                  placeholder="Threshold"),
        dbc.FormText(
            "Type threshold in number",
            color="secondary",
        ),
    ]
)

name_input = dbc.FormGroup(
    [
        dbc.Label("Name"),
        html.Br(),
        dcc.Input(id="condition-specification", type="text",
                  placeholder="Enter Condition name"),
        dbc.FormText(
            "Type a representative name of this condition",
            color="secondary",
        ),
    ]
)

diagnostics_view_content = dbc.Row(
    [
        dcc.ConfirmDialog(
            id='confirm-define-condition',
            message='A condition is defined.',
        ),
        dcc.Store(id='ocpn-diagnostics-dot', storage_type='session', data=""),
        dcc.Store(id='object-types', storage_type='session', data=[]),
        dcc.Store(id='selected', storage_type='session'),
        dbc.Col(
            dash_interactive_graphviz.DashInteractiveGraphviz(id="gv-diagnostics"), width=8
        ),
        dbc.Col(
            [
                html.H3("Define conditions"),
                html.Div(id="selected-diagnostics"),
                diagnostics_input,
                comparator_input,
                threshold_input,
                name_input,
                button(define_condition_title,
                       show_title_maker, show_button_id)

                # dbc.Row(
                #     dbc.Col(html.H3("Define conditions"))
                # ),
                # dbc.Row(
                #     dbc.Col(html.Div(id="selected-diagnostics"))
                # ),
                # dbc.Row(
                #     dbc.Col(dcc.Dropdown(id='diagnostics-dropdown'))
                # ),
                # dbc.Row(
                #     dbc.Col(dcc.Dropdown(id='comp-operators-dropdown',
                #                          options=[{'label': x, 'value': x} for x in COMP_OPERATORS]))
                # ),
                # dbc.Row(
                #     dbc.Col(dcc.Input(id="threshold", type="number",
                #                       placeholder="Threshold"))
                # ),
                # dbc.Row(
                #     dbc.Col(dcc.Input(id="condition-specification", type="text",
                #                       placeholder="Enter Condition name"))
                # ),
                # dbc.Row(
                #     dbc.Col(button(define_condition_title,
                #                    show_title_maker, show_button_id))
                # )
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


@ app.callback(
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
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(global_signal_id_maker(PARSE_TITLE), 'children'),
    State(temp_jobs_store_id_maker(PARSE_TITLE), 'data'),
)
def update_date(pathname, value, old_value, data_jobs):
    if pathname == DVIEW_URL and (value is not None or old_value is not None):
        if value is None:
            value = old_value
        log_hash, date = read_global_signal_value(value)
        user = request.authorization['username']
        data = get_remote_data(user, log_hash, data_jobs,
                               AvailableTasks.PARSE.value)
        eve_df, obj_df = ocel_converter_factory.apply(data)
        min_date = min(eve_df['event_timestamp']).to_pydatetime().date()
        max_date = max(eve_df['event_timestamp']).to_pydatetime().date()
        return min_date, max_date, max_date, max_date
    return no_update(4)


@app.callback(
    Output("selected-diagnostics", "children"),
    Output("diagnostics-dropdown", "options"),
    Output("selected", "data"),
    Input("gv-diagnostics", "selected_node"),
    Input("gv-diagnostics", "selected_edge"),
    State("object-types", "data")
)
def show_available_diagnostics(selected_node, selected_edge, object_types):
    if selected_node is not None:
        # if place
        for obj_type in object_types:
            if obj_type in selected_node:
                available = [e.value for e in AvailablePlaceDiagnostics]
                options = [{'label': x, 'value': x} for x in available]
                return html.Div("Current selection: {}".format(selected_node)), options, selected_node
        # otherwise transition
        available = [e.value for e in AvailableTransitionDiagnostics]
        options = [{'label': x, 'value': x} for x in available]
        return html.Div("Current selection: {}".format(selected_node)), options, selected_node

    elif selected_edge is not None:
        available = [e.value for e in AvailableFlowDiagnostics]
        options = [{'label': x, 'value': x} for x in available]
        return html.Div("Current selection: {}".format(selected_edge)), options, selected_edge
    else:
        return no_update(3)


@app.callback(
    Output(temp_jobs_store_id_maker(DVIEW_TITLE), 'data'),
    Output('ocpn-diagnostics-dot', 'data'),
    Output('object-types', 'data'),
    Input(show_button_id(DVIEW_TITLE), 'n_clicks'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(global_signal_id_maker(PARSE_TITLE), 'children'),
    State(temp_jobs_store_id_maker(PARSE_TITLE), 'data'),
    State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    State(temp_jobs_store_id_maker(DVIEW_TITLE), 'data'),
    State('diagnostics-start', 'data'),
    State('diagnostics-end', 'data'),
)
def run_generate_diagnostics(n_show, value, old_value, data_jobs, control_jobs, temp_jobs, start_date, end_date):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']
        if value is None:
            value = old_value

    if button_value is not None:
        if button_id == show_button_id(DVIEW_TITLE):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            data = get_remote_data(user, log_hash, data_jobs,
                                   AvailableTasks.PARSE.value)
            eve_df, obj_df = ocel_converter_factory.apply(data)
            dt = get_remote_data(user, log_hash, control_jobs,
                                 AvailableTasks.BUILD.value)
            # +1 day to consider the selected end date
            start_date = parser.parse(start_date).date()
            end_date = parser.parse(end_date).date()
            end_date += datetime.timedelta(days=1)

            object_types = dt.ocpn.object_types

            task_id = run_task(
                control_jobs, log_hash, AvailableTasks.DIAGNIZE.value, generate_diagnostics, temp_jobs=temp_jobs, ocpn=dt.ocpn, data=eve_df, start_date=start_date, end_date=end_date)
            diagnostics = get_remote_data(user, log_hash, control_jobs,
                                          AvailableTasks.DIAGNIZE.value)
            print(diagnostics)
            gviz = ocpn_vis_factory.apply(dt.ocpn, diagnostics=diagnostics,
                                          variant="annotated_with_diagnostics", parameters={"format": "svg"})
            ocpn_diagnostics_dot = str(gviz)
            print(ocpn_diagnostics_dot)
            return control_jobs, ocpn_diagnostics_dot, object_types
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
    State("selected", "data"),
    State('diagnostics-start', 'data'),
    State('diagnostics-end', 'data'),
)
def update_output(n, diag, operator, threshold, condition_name, condition_repo, selected, start_date, end_date):
    if n is not None:
        # if selected_node is not None:
        #     selected = selected_node
        # elif selected_edge is not None:
        #     selected = selected_node
        expression = "({}) {} {} {}".format(
            selected, diag, operator, threshold)
        duration = parser.parse(end_date) - parser.parse(start_date)
        days, seconds = duration.days, duration.seconds
        hours = days * 24 + seconds // 3600
        condition_repo.append({"Name": condition_name,
                               "Diagnostics": diag, "Operator": operator, "Threshold": threshold, "Expression": expression, "Element": selected, "Duration": hours})
        return True, condition_repo
    else:
        return False, condition_repo
