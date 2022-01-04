import hashlib
import base64
import datetime
from datetime import date
import re
import sqlite3
import json

import subprocess

from backend.components.misc import container, single_row, button, show_title_maker, show_button_id, global_signal_id_maker, temp_jobs_store_id_maker, global_form_load_signal_id_maker
import dash_interactive_graphviz
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from backend.app import app
import dash_table
import dash
from backend.param.constants import DASHBOARD_TITLE, GLOBAL_FORM_SIGNAL, OVIEW_URL

from dtween.digitaltwin.digitaltwin.util import read_config
from dtween.util.util import DIAGNOSTICS_NAME_MAP

from backend import time_utils

from backend.util import run_task, read_global_signal_value, no_update, transform_config_to_datatable_dict
from backend.tasks.tasks import get_remote_data, store_redis_backend, generate_diagnostics
from dtween.available.available import AvailableTasks, AvailablePlaceDiagnostics, AvailableTransitionDiagnostics, AvailableFlowDiagnostics, AvailableDiagnostics, DefaultDiagnostics
from dtween.digitaltwin.digitaltwin.operation import factory as oper_factory
from flask import request
from dateutil import parser
from dtween.digitaltwin.ocel.objects.ocel.importer import factory as ocel_import_factory
from dtween.digitaltwin.ocel.objects.mdl.preprocessor import factory as mdl_preprocess_factory
from dtween.digitaltwin.digitaltwin.evaluation import factory as evaluation_factory
from dtween.digitaltwin.digitaltwin.visualization import visualizer as dt_vis_factory
from ocpa.visualization.oc_petri_net import factory as ocpn_vis_factory

import pickle
import redis
from time import sleep
from backend.param.settings import redis_pwd


load_ocpn_title = "Refresh operational view".title()
update_title = "update".title()
diagnostics_button_title = "show diagnostics".title()

available_diagonstics = [e.value for e in AvailableDiagnostics]
default_diagonstics = [e.value for e in DefaultDiagnostics]

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


buttons = [
    button(load_ocpn_title, show_title_maker, show_button_id),
]

tab1_content = dbc.Row(
    [
        dbc.Col(html.Div(id="selected-marking"), width=12),
        dbc.Col(html.Div(id='object-list'), width=12),
        dbc.Col(dash_table.DataTable(
            id='object-table',
            fixed_columns={'headers': True, 'data': 1},
            style_table={'minWidth': '100%'}
        ), width=12)
    ]

)

# diagnostics_input = dbc.FormGroup(
#     [
#         dbc.Label("Diagnostics"),
#         dcc.Dropdown(id='diagnostics-dropdown'),
#         dbc.FormText(
#             "Select diagnostics of your interest",
#             color="secondary",
#         ),
#     ]
# )

# comparator_input = dbc.FormGroup(
#     [
#         dbc.Label("Comparator"),
#         dcc.Dropdown(id='comp-operators-dropdown',
#                      options=[{'label': x, 'value': x} for x in COMP_OPERATORS]),
#         dbc.FormText(
#             "Select comparison operator to define condition",
#             color="secondary",
#         ),
#     ]
# )

# threshold_input = dbc.FormGroup(
#     [
#         dbc.Label("Threshold"),
#         html.Br(),
#         dcc.Input(id="threshold", type="number",
#                   placeholder="Threshold"),
#         dbc.FormText(
#             "Type threshold in number",
#             color="secondary",
#         ),
#     ]
# )

# name_input = dbc.FormGroup(
#     [
#         dbc.Label("Name"),
#         html.Br(),
#         dcc.Input(id="condition-specification", type="text",
#                   placeholder="Enter Condition name"),
#         dbc.FormText(
#             "Type a representative name of this condition",
#             color="secondary",
#         ),
#     ]
# )

diagnostics_date_picker = html.Div([
    dcc.Store(id='diagnostics-start', storage_type='session', data=""),
    dcc.Store(id='diagnostics-end', storage_type='session', data=""),
    dcc.Store(id='diagnostics-duration', storage_type='session'),
    dcc.Store(id='diagnostics-list', storage_type='session'),
    dbc.Checklist(
        id='diagnostics-checklist',
        options=[{'label': d, 'value': d} for d in available_diagonstics],
        value=[d for d in default_diagonstics],
        inline=True,
        switch=True
    ),
    html.Hr(),
    html.Div(id='output-container-date-picker-range'),
    dcc.DatePickerRange(
        id='my-date-picker-range',
        min_date_allowed=date(1995, 8, 5),
        max_date_allowed=date(2017, 9, 19),
        initial_visible_month=date(2017, 8, 5),
        end_date=date(2017, 8, 25),
        display_format='YYYY-MM-DD',
    ),
    html.Hr(),
])

diagnostics_tab_content = dbc.Row(
    dbc.Col(
        [
            dcc.ConfirmDialog(
                id='confirm-define-condition',
                message='A condition is defined.',
            ),
            diagnostics_date_picker,
            # dbc.Col(
            #     [
            #         html.H3("Define conditions"),
            #         html.Div(id="selected-diagnostics"),
            #         diagnostics_input,
            #         comparator_input,
            #         threshold_input,
            #         name_input,
            #         # button(define_condition_title,
            #         #        show_title_maker, show_button_id)
            #     ],
            #     width=4
            # ),
            # html.Div(id="selected-diagnostics"),
            button(diagnostics_button_title, show_title_maker, show_button_id)
        ]
    )
)

tabs = dbc.Tabs(
    [
        dbc.Tab(tab1_content, label="State"),
        dbc.Tab(diagnostics_tab_content, label="Diagnostics"),
    ]
)

operational_view_content = dbc.Row(
    [
        dcc.Store(id='ocpn-operational-view-dot',
                  storage_type='session', data=""),
        dcc.Store(id='object-types', storage_type='session', data=[]),
        dbc.Col(
            dash_interactive_graphviz.DashInteractiveGraphviz(
                id="gv-operational-view"), width=6
        ),
        dbc.Col(
            [
                html.Div(id='current-timestamp'),
                tabs
            ], width=6
        )
    ],
    # style=dict(position="absolute", height="100%",
    #            width="100%", display="flex"),
    style={'height': '100vh'}
)

page_layout = container('Digital Twin Interface Model: Operational View',
                        [
                            single_row(html.Div(buttons)),
                            html.Hr(),
                            operational_view_content
                        ]
                        )


@app.callback(
    Output("gv-operational-view", "dot_source"),
    Output("gv-operational-view", "engine"),
    Input('url', 'pathname'),
    Input("ocpn-operational-view-dot", "data")
)
def show_ocpn(pathname, value):
    if pathname == OVIEW_URL and value is not None:
        return value, "dot"
    return no_update(2)


@app.callback(
    Output('ocpn-operational-view-dot', 'data'),
    Output('object-types', 'data'),
    Output("my-date-picker-range", "min_date_allowed"),
    Output("my-date-picker-range", "max_date_allowed"),
    Output("my-date-picker-range", "initial_visible_month"),
    Output("my-date-picker-range", "end_date"),
    Input(show_button_id(load_ocpn_title), 'n_clicks'),
    Input(show_button_id(diagnostics_button_title), 'n_clicks'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    State('diagnostics-start', 'data'),
    State('diagnostics-end', 'data'),
    State('diagnostics-checklist', 'value'),
    State('log-dir', 'data'),
)
def load_ocpn(n_load, n_diagnosis, value, dashboard_jobs, start_date, end_date, diagnostics_list, log_dir):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']

    if button_id == show_button_id(load_ocpn_title):
        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        dt = get_remote_data(user, log_hash, dashboard_jobs,
                             AvailableTasks.SIMULATE.value)
        gviz = dt_vis_factory.apply(dt, parameters={"format": "svg"})
        dt_dot = str(gviz)

        print("streaming event data from {}".format(log_dir))
        data = ocel_import_factory.apply(log_dir)
        event_df = data[0]
        min_date = min(event_df['event_timestamp']).to_pydatetime().date()
        max_date = max(event_df['event_timestamp']).to_pydatetime().date()
        return dt_dot, dash.no_update, min_date, max_date, max_date, max_date

    elif button_id == show_button_id(diagnostics_button_title):
        print("streaming event data from {}".format(log_dir))
        data = ocel_import_factory.apply(log_dir)
        event_df = data[0]
        # +1 day to consider the selected end date
        start_date = parser.parse(start_date).date()
        end_date = parser.parse(end_date).date()
        end_date += datetime.timedelta(days=1)

        log_hash, date = read_global_signal_value(value)
        user = request.authorization['username']
        dt = get_remote_data(user, log_hash, dashboard_jobs,
                             AvailableTasks.SIMULATE.value)

        object_types = dt.ocpn.object_types

        print(dt)
        print(event_df)
        task_id = run_task(
            dashboard_jobs, log_hash, AvailableTasks.DIAGNIZE.value, generate_diagnostics, ocpn=dt.ocpn, data=event_df, start_date=start_date, end_date=end_date)
        diagnostics = get_remote_data(user, log_hash, dashboard_jobs,
                                      AvailableTasks.DIAGNIZE.value)
        print(diagnostics)
        parameters = dict()
        for d in diagnostics_list:
            parameters[DIAGNOSTICS_NAME_MAP[d]] = True
        parameters['format'] = 'svg'
        gviz = ocpn_vis_factory.apply(
            dt.ocpn, diagnostics=diagnostics, variant="annotated_with_diagnostics", parameters=parameters)
        ocpn_diagnostics_dot = str(gviz)
        return ocpn_diagnostics_dot, object_types, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    return no_update(6)


def awrite(writer, data):
    writer.write(data)
    # await writer.drain()
    writer.flush()


def group_item(name, index):
    return dbc.ListGroupItem(name, id={"type": "object-item", "index": index}, n_clicks=0, action=True)


@app.callback(
    Output("selected-marking", "children"),
    Output('object-list', 'children'),
    Output('object-table', 'columns'),
    Output('object-table', 'data'),
    Input("gv-operational-view", "selected"),
    State('token-map', 'data'),
    State('log-dir', 'data'),
)
def show_selected(value, token_map, filename):
    if value is not None and token_map is not None:
        # selected_tokens = [[pl, oi]
        #                    for pl, oi in tokens if str(value) == str(pl)]
        token_map = json.loads(token_map)
        if value in token_map:
            object_ids = token_map[value]
            data = ocel_import_factory.apply(filename)
            object_df = data[1]
            object_df = mdl_preprocess_factory.filter_object_df_by_object_ids(
                object_df, object_ids)
            object_df.dropna(how='all', axis=1, inplace=True)
            object_table_columns = [{"name": i, "id": i}
                                    for i in object_df.columns]
            object_table_data = object_df.to_dict('records')
            object_list = [
                dbc.Button(x, id={
                    'type': 'object-button',
                    'index': x
                }, name=x, outline=True, color="info", className="mr-1") for x in token_map[value]
            ]
            return html.Div("Marking at {}".format(value)), \
                html.Div(object_list), \
                object_table_columns, \
                object_table_data

        else:
            return html.Div("Marking at {}".format(value)), dash.no_update, dash.no_update, dash.no_update

    else:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update


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
