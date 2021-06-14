import hashlib
import base64
import datetime
from datetime import date
import re
import sqlite3
import json

from dash_bootstrap_components._components.Col import Col

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
from backend.param.constants import CVIEW_TITLE, DVIEW_TITLE, GLOBAL_FORM_SIGNAL, DVIEW_URL, PARSE_TITLE, DASHBOARD_TITLE, DASHBOARD_URL, JOBS_KEY, JOB_TASKS_KEY

from backend.util import add_job, run_task, forget_all_tasks, get_job_id, check_existing_job, read_global_signal_value, read_active_attribute_form, write_global_signal_value, no_update, transform_config_to_datatable_dict
from backend.tasks.tasks import get_remote_data, store_redis_backend
from dtwin.available.available import AvailableTasks
from dtwin.digitaltwin.ocpn.visualization import visualizer as ocpn_vis_factory
from dtwin.digitaltwin.digitaltwin.operation import factory as oper_factory
from flask import request
from dateutil import parser
from dtwin.digitaltwin.ocel.objects.ocel.importer import factory as ocel_import_factory
from dtwin.digitaltwin.ocel.objects.mdl.preprocessor import factory as mdl_preprocess_factory
from dash.dependencies import Input, Output, State, MATCH, ALL
from dtwin.digitaltwin.digitaltwin.evaluation import factory as evaluation_factory
from dtwin.infosystem.process.config import factory as config_factory
from pm4pymdl.algo.mvp.utils import succint_mdl_to_exploded_mdl

connect_db_title = "Connect to Event Stream"
start_title = "start".title()
stop_title = "stop".title()
reset_title = "reset".title()

uploads = dbc.Row(
    [
        dbc.Col(dcc.Upload(id="connect-db",
                children=button(connect_db_title, show_title_maker, show_button_id)), width="auto"),
    ], justify='start'
)

bin_size_slider = dbc.FormGroup(
    [
        dbc.Label("Select Bin Size", html_for="range-slider"),
        dcc.RangeSlider(id='bin-size-slider', max=0, min=-120, value=[-24, 0]),
        dbc.FormText(id='output-bin-size-slider')
    ]
)

step_size_slider = dbc.FormGroup(
    [
        dbc.Label("Select Step Size", html_for="range-slider"),
        dcc.RangeSlider(id='step-size-slider', min=0, max=120, value=[0, 24]),
        dbc.FormText(id='output-step-size-slider')
    ]
)


sliders = dbc.Row(
    [
        dbc.Col(bin_size_slider),
        dbc.Col(step_size_slider)
    ]
)

buttons = [
    button(DASHBOARD_TITLE, show_title_maker, show_button_id),
    button(start_title, show_title_maker, show_button_id),
    button(stop_title, show_title_maker, show_button_id),
    button(reset_title, show_title_maker, show_button_id),
]

tab1_content = dbc.Row(
    dbc.Col(
        [
            html.Br(),
            dbc.Row(
                dbc.Col(html.Div(id="selected-marking"))
            ),
            # dbc.Row(
            #     dbc.Col(html.Div(id='live-marking-text'))
            # ),
            # dbc.Row(
            #     dbc.Col(html.Div(id='object-info'))
            # ),
            dbc.Row(
                dbc.Col(html.Div(id='object-list'))
            ),
            dbc.Row(
                dbc.Col(
                    dash_table.DataTable(
                        id='object-table'
                    )
                )
            )
        ]
    )
)

tab2_content = dbc.Row(
    [
        dbc.Col(
            [
                # dbc.Row(
                #     dbc.Col(html.H4(''))
                # ),
                dbc.Row(
                    dbc.Col(
                        dash_table.DataTable(
                            id='operation-table', columns=[]
                        )
                    )
                )
            ]
        ),
    ]
)

tab3_content = dbc.Row(
    [
        dbc.Col(
            [
                # dbc.Row(
                #     dbc.Col(html.H4('Live action'))
                # ),
                html.Br(),
                html.H3("Current Configuration"),
                dbc.Row(
                    dbc.Col(
                        dash_table.DataTable(
                            id='configuration-table',
                            columns=[
                                {'id': 'valve', 'name': 'Valve Name'},
                                {'id': 'value', 'name': 'Current Value'}
                            ]
                        )
                    )
                ),
                html.Br(),
                html.H3("Action Log"),
                dbc.Row(
                    dbc.Col(html.Div(id='action-log-list'))
                )

            ]
        ),
    ]
)

tabs = dbc.Tabs(
    [
        dbc.Tab(tab2_content, label="Operation"),
        dbc.Tab(tab1_content, label="State"),
        dbc.Tab(tab3_content, label="Action")
    ]
)

dashboard_view_content = dbc.Row(
    [
        dcc.Store(id='ocpn-dashboard-dot', storage_type='session', data=""),
        dcc.Store(id='token-map', storage_type='session'),
        dcc.Store(id='db-dir', storage_type='session'),
        dcc.Store(id='start-time', storage_type='session'),
        dcc.Store(id='bin-size', storage_type='session'),
        dcc.Store(id='action-log', storage_type='session', data=[]),
        dbc.Col(
            dash_interactive_graphviz.DashInteractiveGraphviz(
                id="gv-dashboard"), width=6
        ),
        dbc.Col(
            [
                html.Div(id='current-timestamp'),
                tabs
            ], width=6
        )
    ],
    style=dict(position="absolute", height="100%",
               width="100%", display="flex"),
)

page_layout = container('Dashboard',
                        [
                            uploads,
                            sliders,
                            single_row(html.Div(buttons)),
                            html.Hr(),
                            dashboard_view_content
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
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(global_signal_id_maker(PARSE_TITLE), 'children'),
    State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    State('ocpn-dashboard-dot', 'data')
)
def load_ocpn(n, value, old_value, control_jobs, old_dot):
    if n is not None:
        if value is None:
            value = old_value
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
    Output('start-time', 'data'),
    Output('interval-component', 'n_intervals'),
    Input(show_button_id(start_title), 'n_clicks'),
    Input(show_button_id(stop_title), 'n_clicks'),
    Input(show_button_id(reset_title), 'n_clicks'),
    State("interval-component", "disabled")
)
def start_operation(n_start, n_stop, n_reset, disabled):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']
    if button_id == show_button_id(start_title):
        return False, str(datetime.datetime.now()), dash.no_update
    elif button_id == show_button_id(stop_title):
        return True, dash.no_update, dash.no_update
    elif button_id == show_button_id(reset_title):
        return True, str(datetime.datetime.now()), 0
    else:
        return disabled, no_update(2)


def group_item(name, index):
    return dbc.ListGroupItem(name, id={"type": "object-item", "index": index}, n_clicks=0, action=True)


@app.callback(
    Output("selected-marking", "children"),
    # Output("live-marking-text", "children"),
    # Output('object-info', 'children'),
    Output('object-list', 'children'),
    Output('object-table', 'columns'),
    Output('object-table', 'data'),
    Input("gv-dashboard", "selected"),
    State('token-map', 'data'),
    State('db-dir', 'data'),
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
            object_table_columns = [{"name": i, "id": i}
                                    for i in object_df.columns]
            object_table_data = object_df.to_dict('records')
            object_list = [
                dbc.Button(x, id={
                    'type': 'object-button',
                    'index': x
                }, name=x, outline=True, color="info", className="mr-1") for x in token_map[value]
            ]
            object_list_group = dbc.ListGroup(
                [group_item(name, index)
                 for index, name in enumerate(token_map[value])],
                horizontal=True,
                className="mb-2"
            )
            object_info_list = []
            for index, name in enumerate(token_map[value]):
                object_info_list.append(
                    html.Div(
                        id={
                            'type': 'dynamic-output',
                            'index': index
                        }
                    )
                )

            return html.Div("Marking at {}".format(value)), \
                html.Div(object_list), \
                object_table_columns, \
                object_table_data
            # html.Div(object_list_group), \
            # html.Div(object_info_list), \

        else:
            return html.Div("Marking at {}".format(value)), \
                no_update(3)

    else:
        return no_update(4)


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
    # Output('live-operation-text', 'children'),
    Output('operation-table', 'columns'),
    Output('operation-table', 'data'),
    Output('configuration-table', 'data'),
    Output(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    Output('token-map', 'data'),
    Output('current-timestamp', 'children'),
    Output('action-log', 'data'),
    Output('action-log-list', 'children'),
    Input('interval-component', 'disabled'),
    Input('interval-component', 'interval'),
    Input('interval-component', 'n_intervals'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(global_signal_id_maker(PARSE_TITLE), 'children'),
    State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    # State(temp_jobs_store_id_maker(DASHBOARD_TITLE), 'data'),
    State('start-time', 'data'),
    State('db-dir', 'data'),
    State('bin-size', 'data'),
    State('action-pattern-repository', 'data'),
    State('action-log', 'data'),
)
def run_operation(disabled, interval, n_intervals, value, old_value, control_jobs, start_time, filename, bin_size, action_pattern_repo, action_log):
    if disabled == False and (old_value is not None or value is not None):
        if value is None:
            value = old_value
        # conn = sqlite3.connect(
        #     "/Users/gyunam/Documents/DigitalTwin/src/dtwin/infosystem/database/eventstream.sqlite")
        # cur = conn.cursor()
        # limit = 200
        print("streaming from {}".format(filename))
        data = ocel_import_factory.apply(filename)
        event_df = data[0]
        start_timestamp = parser.parse(
            start_time) + datetime.timedelta(hours=interval/1000*n_intervals-bin_size)
        end_timestamp = parser.parse(
            start_time) + datetime.timedelta(hours=interval/1000*n_intervals)
        sublog = mdl_preprocess_factory.filter_by_timestamp(
            event_df, start_timestamp=start_timestamp, end_timestamp=end_timestamp)
        if len(sublog) == 0:
            print("no events")
        # log = oper_factory.analyze_events(conn, cur, limit)
        # oper_factory.delete_events(conn, cur, 5)

        # read digitial twin
        user = request.authorization['username']
        log_hash, date = read_global_signal_value(value)
        # if log_hash not in dashboard_jobs[JOBS_KEY]:
        #     dt = get_remote_data(user, log_hash, control_jobs,
        #                          AvailableTasks.BUILD.value)
        # else:
        #     dt = get_remote_data(user, log_hash, dashboard_jobs,
        #                          AvailableTasks.OPERATE.value)
        if AvailableTasks.OPERATE.value not in control_jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY]:
            dt = get_remote_data(user, log_hash, control_jobs,
                                 AvailableTasks.BUILD.value)
        else:
            dt = get_remote_data(user, log_hash, control_jobs,
                                 AvailableTasks.OPERATE.value)

        # update marking
        dt.marking = oper_factory.apply(dt.ocpn, sublog, dt.marking)
        token_map = {}
        for pl, oi in dt.marking.tokens:
            if pl.name not in token_map.keys():
                token_map[pl.name] = [oi]
            else:
                token_map[pl.name].append(oi)

        # store digital twin
        task_id = run_task(control_jobs, log_hash, AvailableTasks.OPERATE.value,
                           store_redis_backend, data=dt)
        operation_table_columns = [{"name": i, "id": i}
                                   for i in sublog.columns]
        operation_table_data = sublog.to_dict('records')

        # interval/1000 since dash uses milliseconds
        event_df = succint_mdl_to_exploded_mdl.apply(event_df)
        action_log_at_t, exp_log = evaluation_factory.evaluate(
            action_pattern_repo, dt, event_df, end_timestamp, interval/1000, n_intervals)
        if len(action_log_at_t) != 0:
            action_log += action_log_at_t

        # maintain X action events
        if len(action_log) > 10:
            action_log = action_log[-10:]

        action_log_list = dbc.ListGroup(
            [dbc.ListGroupItem(event)
             for event in reversed(action_log)],
            className="mb-2"
        )

        # result = log.to_json(orient="records")
        # parsed = json.loads(result)
        # return html.Div([
        #                 html.P(json.dumps(parsed, indent=4))
        #                 ]), \
        #     control_jobs, json.dumps(token_map), \
        #     end_timestamp.strftime("%Y-%m-%d, %H:%M:%S")

        config = config_factory.read_config()
        configuration_table_data = transform_config_to_datatable_dict(
            config)

        return operation_table_columns, \
            operation_table_data, \
            configuration_table_data, \
            control_jobs, json.dumps(token_map), \
            end_timestamp.strftime("%Y-%m-%d, %H:%M:%S"), \
            action_log, \
            html.Div(action_log_list)

    return no_update(8)


@ app.callback(
    Output('db-dir', 'data'),
    Input('connect-db', 'filename')
)
def connect_to_db(filename):
    _filename = "/Users/gyunam/Documents/DigitalTwin/src/dtwin/infosystem/simulation/simulated-logs.jsonocel"
    return _filename


@app.callback(
    Output('output-bin-size-slider', 'children'),
    Output('bin-size', 'data'),
    Input('bin-size-slider', 'value')
)
def update_output(value):
    return 'The operation and state will consider previous {} hours.'.format(abs(value[0])), abs(value[0])


@app.callback(
    Output('output-step-size-slider', 'children'),
    Output('interval-component', 'interval'),
    Input('step-size-slider', 'value')
)
def update_output(value):
    return 'The operation and state will be updated every {} hours'.format(abs(value[1])), abs(value[1])*1000


# @app.callback(
#     Output('object-info', 'children'),
#     Input({'type': 'object-button', 'index': ALL}, 'value')
# )
# def display_output(value):
#     print(value)
#     return value

@app.callback(
    Output({"type": "dynamic-output", "index": MATCH}, "children"),
    # Output({"type": "object-item", "index": MATCH}, "children"),
    Input({"type": "object-item", "index": MATCH}, "n_clicks"),
    State({"type": "object-item", "index": MATCH}, "children")
)
def clicked(n_click, children):
    print(children)
    return children
