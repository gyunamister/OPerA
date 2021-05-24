import hashlib
import base64
import datetime
from datetime import date
import re
import sqlite3
import json

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
from backend.param.constants import CVIEW_TITLE, DVIEW_TITLE, GLOBAL_FORM_SIGNAL, DVIEW_URL, HOME_TITLE, DASHBOARD_TITLE, DASHBOARD_URL, JOBS_KEY

from backend.util import add_job, run_task, forget_all_tasks, get_job_id, check_existing_job, read_global_signal_value, read_active_attribute_form, write_global_signal_value, no_update
from backend.tasks.tasks import get_remote_data, store_redis_backend
from dtwin.available.available import AvailableTasks
from dtwin.digitaltwin.ocpn.visualization import visualizer as ocpn_vis_factory
from dtwin.digitaltwin.digitaltwin.operation import factory as oper_factory

from dateutil import parser
from flask import request

connect_db_title = "Connect to Event Stream"
start_title = "start".title()
stop_title = "stop".title()

uploads = dbc.Row(
    [
        dbc.Col(dcc.Upload(id="connect-db",
                children=button(connect_db_title, show_title_maker, show_button_id)), width="auto"),
    ], justify='start'
)

buttons = [
    button(DASHBOARD_TITLE, show_title_maker, show_button_id),
    button(start_title, show_title_maker, show_button_id),
    button(stop_title, show_title_maker, show_button_id),
]

tab1_content = dbc.Row(
    dbc.Col(
        [
            dbc.Row(
                dbc.Col(html.Div(id="selected-dashboard"))
            ),
            dbc.Row(
                dbc.Col(html.Div(id='live-marking-text'))
            ),
            dbc.Row(
                dbc.Col(html.H4("Current configuration"))
            ),
        ]
    )
)

tab2_content = dbc.Row(
    [
        dbc.Col(
            [
                dbc.Row(
                    dbc.Col(html.H4('Live operation'))
                ),
                dbc.Row(
                    dbc.Col(html.Div(id='live-operation-text'))
                )
            ]
        ),
    ]
)

tab3_content = dbc.Row(
    [
        dbc.Col(
            [
                dbc.Row(
                    dbc.Col(html.H4('Live action'))
                ),
                dbc.Row(
                    dbc.Col(html.Div(id='live-action-text'))
                )
            ]
        ),
    ]
)

tabs = dbc.Tabs(
    [
        dbc.Tab(tab1_content, label="State"),
        dbc.Tab(tab2_content, label="Operation"),
        dbc.Tab(tab3_content, label="Action")
    ]
)

dashboard_view_content = dbc.Row(
    [
        dcc.Store(id='ocpn-dashboard-dot', storage_type='session', data=""),
        dcc.Store(id='token-map', storage_type='session'),
        dcc.Store(id='db-dir', storage_type='session'),
        dcc.Interval(id='interval-component', disabled=True,
                     interval=10*1000, n_intervals=0),
        dbc.Col(
            dash_interactive_graphviz.DashInteractiveGraphviz(
                id="gv-dashboard"), width=8
        ),
        # dbc.Col(
        #     [
        #         dbc.Row(
        #             dbc.Col(html.H3("Show current status"))
        #         ),
        #         dbc.Row(
        #             dbc.Col(html.Div(id="selected-dashboard"))
        #         ),
        #         dbc.Row(
        #             dbc.Col(html.Div(id='live-marking-text'))
        #         ),
        #         dbc.Row(
        #             dbc.Col(html.H3("Show current status"))
        #         ),

        #     ],
        #     width=4
        # )
        dbc.Col(
            tabs, width=4
        )
    ],
    style=dict(position="absolute", height="100%",
               width="100%", display="flex"),
)


# operation_view_content = dbc.Row(
#     [
#         dbc.Col(
#             [
#                 dbc.Row(
#                     dbc.Col(html.H4('Live operation'))
#                 ),
#                 dbc.Row(
#                     dbc.Col(html.Div(id='live-operation-text'))
#                 )
#             ], width=6
#         ),
#         dbc.Col(
#             [
#                 dbc.Row(
#                     dbc.Col(html.H4('Live action'))
#                 ),
#                 dbc.Row(
#                     dbc.Col(html.Div(id='live-action-text'))
#                 )
#             ], width=6
#         )
#     ],
#     style=dict(position="absolute", height="100%",
#                width="100%", display="flex"),
# )

page_layout = container('Dashboard',
                        [
                            uploads,
                            single_row(html.Div(buttons)),
                            html.Hr(),
                            dashboard_view_content,
                            # html.Hr(),
                            # operation_view_content
                        ]
                        )


@app.callback(
    Output("gv-dashboard", "dot_source"),
    Output("gv-dashboard", "engine"),
    Input('url', 'pathname'),
    Input("ocpn-dashboard-dot", "data")
)
def show_ocpn(pathname, value):
    if pathname == DASHBOARD_URL and value is not None:
        return value, "dot"
    return no_update(2)


@app.callback(
    Output('ocpn-dashboard-dot', 'data'),
    Input(show_button_id(DASHBOARD_TITLE), 'n_clicks'),
    State(global_signal_id_maker(HOME_TITLE), 'children'),
    State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    State('ocpn-dashboard-dot', 'data')
)
def load_ocpn(n, value, control_jobs, old_dot):
    if n is not None:
        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        dt = get_remote_data(user, log_hash, control_jobs,
                             AvailableTasks.BUILD.value)
        gviz = ocpn_vis_factory.apply(dt.ocpn, parameters={"format": "svg"})
        ocpn_dot = str(gviz)
        return ocpn_dot
    return old_dot


@app.callback(
    Output('interval-component', 'disabled'),
    Input(show_button_id(start_title), 'n_clicks'),
    Input(show_button_id(stop_title), 'n_clicks'),
    State("interval-component", "disabled")
)
def start_operation(n_start, n_stop, disabled):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']
    if button_id == show_button_id(start_title):
        return False
    elif button_id == show_button_id(stop_title):
        return True
    else:
        return disabled


@app.callback(
    Output("selected-dashboard", "children"),
    Output("live-marking-text", "children"),
    Input("gv-dashboard", "selected"),
    State('token-map', 'data'),
)
def show_selected(value, token_map):
    if value is not None and token_map is not None:
        # selected_tokens = [[pl, oi]
        #                    for pl, oi in tokens if str(value) == str(pl)]
        token_map = json.loads(token_map)
        print(token_map)
        if token_map[value] is not None:
            buttons = [
                dbc.Button(x, outline=True, color="info", className="mr-1") for x in token_map[value]
            ]
            return html.Div("Marking at {}".format(value)), \
                html.Div(buttons)
        else:
            return html.Div("Marking at {}".format(value)), \
                dash.no_update
    else:
        return no_update(2)


# @app.callback(
#     Output(global_signal_id_maker(DVIEW_TITLE), 'children'),
#     Output(temp_jobs_store_id_maker(DVIEW_TITLE), 'data'),
#     Output('ocpn-diagnostics-dot', 'data'),
#     Input(show_button_id(DVIEW_TITLE), 'n_clicks'),
#     State(global_signal_id_maker(HOME_TITLE), 'children'),
#     State('jobs-store', 'data'),
#     State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
#     State(temp_jobs_store_id_maker(DVIEW_TITLE), 'data'),
#     State('diagnostics-start', 'data'),
#     State('diagnostics-end', 'data'),
# )
# def run_generate_diagnostics(n_show, value, data_jobs, control_jobs, temp_jobs, start_date, end_date):
#     ctx = dash.callback_context
#     if not ctx.triggered:
#         button_id = 'No clicks yet'
#     else:
#         button_id = ctx.triggered[0]['prop_id'].split('.')[0]
#         button_value = ctx.triggered[0]['value']

#     if button_value is not None:
#         if button_id == show_button_id(DVIEW_TITLE):
#             log_hash, date = read_global_signal_value(value)
#             user = request.authorization['username']
#             log = get_remote_data(user, log_hash, data_jobs,
#                                   AvailableTasks.UPLOAD.value)
#             dt = get_remote_data(user, log_hash, control_jobs,
#                                  AvailableTasks.BUILD.value)
#             task_id = run_task(
#                 control_jobs, log_hash, AvailableTasks.DIAGNIZE.value, generate_diagnostics, temp_jobs=temp_jobs, ocpn=dt.ocpn, data=log, start_date=start_date, end_date=end_date)
#             diagnostics = get_remote_data(user, log_hash, control_jobs,
#                                           AvailableTasks.DIAGNIZE.value)
#             print("Use diagnostics: {}".format(diagnostics))
#             gviz = ocpn_vis_factory.apply(dt.ocpn, diagnostics=diagnostics,
#                                           variant="annotated_with_diagnostics", parameters={"format": "svg"})
#             ocpn_diagnostics_dot = str(gviz)
#             return write_global_signal_value([log_hash, task_id]), control_jobs, ocpn_diagnostics_dot
#     return no_update(3)


@app.callback(
    Output('live-operation-text', 'children'),
    Output(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    Output('token-map', 'data'),
    Input('interval-component', 'disabled'),
    Input('interval-component', 'n_intervals'),
    State(global_signal_id_maker(HOME_TITLE), 'children'),
    State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data')
)
def run_operation(disabled, n, value, control_jobs, dashboard_jobs):
    print(disabled)
    if disabled == False:
        conn = sqlite3.connect(
            "/Users/gyunam/Documents/DigitalTwin/src/dtwin/infosystem/database/eventstream.sqlite")
        cur = conn.cursor()
        limit = 200
        log = oper_factory.analyze_events(conn, cur, limit)
        oper_factory.delete_events(conn, cur, 5)
        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        if log_hash not in dashboard_jobs[JOBS_KEY]:
            dt = get_remote_data(user, log_hash, control_jobs,
                                 AvailableTasks.BUILD.value)
        else:
            dt = get_remote_data(user, log_hash, dashboard_jobs,
                                 AvailableTasks.OPERATE.value)
        dt.marking = oper_factory.apply(dt.ocpn, log, dt.marking)
        token_map = {}
        for pl, oi in dt.marking.tokens:
            if pl.name not in token_map.keys():
                token_map[pl.name] = [oi]
            else:
                token_map[pl.name].append(oi)
        print(token_map)
        task_id = run_task(control_jobs, log_hash, AvailableTasks.OPERATE.value,
                           store_redis_backend, temp_jobs=dashboard_jobs, data=dt)
        # oper_str = ""
        # for i, row in log.iterrows():
        #     oper_str += "event_id{}"
        result = log.to_json(orient="records")
        parsed = json.loads(result)
        return html.Div([
                        html.P(json.dumps(parsed, indent=4))
                        ]), control_jobs, json.dumps(token_map)

    return no_update(3)


@ app.callback(
    Output('db-dir', 'data'),
    Input('connect-db', 'filename')
)
def upload_guards(filename):
    print(filename)
    return dash.no_update
