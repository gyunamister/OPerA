import hashlib
import base64


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
from backend.param.constants import CVIEW_TITLE, GLOBAL_FORM_SIGNAL, CORR_TITLE, CVIEW_URL, HOME_TITLE, DVIEW_TITLE, JSON

from dtwin.digitaltwin.digitaltwin.visualization import visualizer as dt_vis_factory
from dtwin.digitaltwin.digitaltwin.util import guards_to_df, df_to_gaurds
from backend.util import add_job, run_task, forget_all_tasks, get_job_id, check_existing_job, read_global_signal_value, read_active_attribute_form, transform_to_guards, write_global_signal_value, no_update, parse_contents
from backend.tasks.tasks import get_remote_data, build_digitaltwin
from dtwin.available.available import AvailableTasks

from flask import request

discover_title = "Discover OCPN"
upload_guard_title = "Upload Guards"
upload_valve_title = "Upload Valves"

apply_guard_title = "Apply Guards"
apply_configuration_title = "Apply Configuration"
define_action_title = "Define Action"


buttons = dbc.Row(
    [
        dbc.Col(button(discover_title, show_title_maker,
                show_button_id), width="auto"),
        dbc.Col(dcc.Upload(id="upload-guard",
                children=button(upload_guard_title, show_title_maker, show_button_id)), width="auto"),
        dbc.Col(dcc.Upload(id="upload-valve",
                children=button(upload_valve_title, show_title_maker, show_button_id)), width="auto"),
    ], justify='start'
)

control_view_content = dbc.Row(
    [
        dcc.Store(id='guard-store', storage_type='session'),
        dcc.Store(id='valve-store', storage_type='session'),
        dcc.Store(id='ocpn-dot', storage_type='session', data=""),
        dcc.ConfirmDialog(
            id='confirm-guard-update',
            message='Guard information is updated.',
        ),
        dcc.ConfirmDialog(
            id='confirm-define-action',
            message='An action is defined.',
        ),
        dbc.Col(
            dash_interactive_graphviz.DashInteractiveGraphviz(id="gv"), width=8, style={'height': "100%"}
        ),
        dbc.Col(
            [
                dbc.Row(
                    dbc.Col(html.H3("Guards"))
                ),
                dbc.Row(
                    dbc.Col(dash_table.DataTable(
                        id='guard-table',
                        columns=[
                            {'id': 'transition', 'name': 'transition'},
                            {'id': 'guard', 'name': 'guard',
                             'presentation': 'dropdown'},
                        ],
                        editable=True
                    ))
                ),
                dbc.Row(
                    dbc.Col(button(apply_guard_title,
                                   show_title_maker, show_button_id))
                ),
                html.Hr(),
                dbc.Row(
                    dbc.Col(html.H3("Valves"))
                ),
                # dbc.Row(
                #     dbc.Col(button(apply_configuration_title,
                #                    show_title_maker, show_button_id)),
                # ),
                dbc.Row(
                    dbc.Col(dcc.Dropdown(id='valve-dropdown'))
                ),
                dbc.Row(
                    dbc.Col((dcc.Slider(id='valve-slider'))
                            ),
                ),
                dbc.Row(
                    dbc.Col(html.Div(id='current-valve-value')
                            ),
                ),
                dbc.Row(
                    dbc.Col(dcc.Input(id="action-specification", type="text",
                                      placeholder="Enter Action name"))
                ),
                dbc.Row(
                    [
                        dbc.Col(button(define_action_title,
                                       show_title_maker, show_button_id))
                    ]
                ),
            ],
            width=4
        ),
    ],
    style=dict(position="absolute", height="100%",
               width="100%", display="flex"),
)

page_layout = container('Control View',
                        [
                            buttons,
                            control_view_content
                        ]
                        )


@ app.callback(
    Output("gv", "dot_source"),
    Output("gv", "engine"),
    Input('url', 'pathname'),
    Input("ocpn-dot", "data")
)
def show_ocpn(pathname, value):
    if pathname == CVIEW_URL and value is not None:
        return value, "dot"
    return no_update(2)


# @app.callback(
#     [Output("gv", "dot_source"), Output("gv", "engine")],
#     [Input("input", "value"), Input("engine", "value")],
# )
# def display_output(value, engine):
#     return value, engine


@ app.callback(
    Output("selected", "children"),
    Input("gv", "selected")
)
def show_selected(value):
    return html.Div(value)


# @app.callback(
#     Output('confirm-guard-update', 'displayed'),
#     Output('ocpn-dot', 'data'),
#     Input('submit-button', 'n_clicks'),
#     Input('guard-table', 'data'),
#     State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
#     State('jobs-store', 'data'),
# )
# def display_confirm(n_clicks, value, jobs):
#     if n_clicks:
#         log_hash, date = read_global_signal_value(value)
#         user = request.authorization['username']
#         guards = transform_to_guards(data)
#         dt = get_remote_data(user, log_hash, jobs,
#                              AvailableTasks.BUILD.value)
#         dt = update_guards(dt, guards)
#         gviz = dt_vis_factory.apply(dt, parameters={"format": "svg"})
#         dt_dot = str(gviz)
#         return True, dt_dot
#     return False, dt_dot


# @app.callback(
#     [
#         Input('submit-button', 'n_clicks'),
#         Input('guard-table', 'data')
#     ],
#     [
#         State('submit-button', 'n_clicks')
#     ])
# def update_datatable(n_clicks):
#     if n_clicks:
#         print(data)

@ app.callback(
    Output(global_signal_id_maker(CVIEW_TITLE), 'children'),
    Output(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    Output('ocpn-dot', 'data'),
    Input(show_button_id(discover_title), 'n_clicks'),
    Input(show_button_id(apply_guard_title), 'n_clicks'),
    # Input(show_button_id(apply_configuration_title), 'n_clicks'),
    State('guard-table', 'data'),
    State('valve-store', 'data'),
    State(global_signal_id_maker(HOME_TITLE), 'children'),
    State('jobs-store', 'data'),
    State(temp_jobs_store_id_maker(CVIEW_TITLE), 'data'),
    prevent_initial_call=True
)
def run_build_digitaltwin(n_discover, n_guard, guards, valves, value, data_jobs, temp_jobs):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_value = ctx.triggered[0]['value']

    if button_value is not None:
        if button_id == show_button_id(discover_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            df = get_remote_data(user, log_hash, data_jobs,
                                 AvailableTasks.UPLOAD.value)
            task_id = run_task(
                data_jobs, log_hash, AvailableTasks.BUILD.value, build_digitaltwin, temp_jobs=temp_jobs, data=df)
            dt = get_remote_data(user, log_hash, data_jobs,
                                 AvailableTasks.BUILD.value)
            gviz = dt_vis_factory.apply(dt, parameters={"format": "svg"})
            dt_dot = str(gviz)
            return write_global_signal_value([log_hash, task_id]), data_jobs, dt_dot
        elif button_id == show_button_id(apply_guard_title):
            log_hash, date = read_global_signal_value(value)
            user = request.authorization['username']
            guards = transform_to_guards(guards)
            dt = get_remote_data(user, log_hash, temp_jobs,
                                 AvailableTasks.BUILD.value)
            dt.guards = guards
            gviz = dt_vis_factory.apply(dt, parameters={"format": "svg"})
            dt_dot = str(gviz)
            return dash.no_update, temp_jobs, dt_dot
        # elif button_id == show_button_id(apply_configuration_title):
        #     log_hash, date = read_global_signal_value(value)
        #     user = request.authorization['username']
        #     dt = get_remote_data(user, log_hash, temp_jobs,
        #                          AvailableTasks.BUILD.value)
        #     config = {}
        #     for name, spec in valves.items():
        #         config[name] = spec['cur']
        #     dt.config = config
        #     gviz = dt_vis_factory.apply(dt, parameters={"format": "svg"})
        #     dt_dot = str(gviz)
        #     return dash.no_update, temp_jobs, dt_dot

    # df = mdl_importer.apply(
    #     "/Users/gyunam/Documents/DigitalTwin/example_logs/mdl/order_management.mdl")
    # ocpn = discovery_factory.apply(df)

    # dt = get_digital_twin(ocpn, [], [])

    # df = get_remote_data(user, log_hash, jobs, AvailableTasks.UPLOAD.value)
    # print(df)
    # loc, res = set_special_attributes(location, resource)
    # task_id = run_task(jobs, log_hash, AvailableTasks.PARSE.value, parse_data, temp_jobs,
    #                    data=df,
    #                    data_type=CSV,
    #                    resource=res,
    #                    location=loc)
    return no_update(3)


@ app.callback(
    Output('guard-table', 'data'),
    Output('guard-table', 'dropdown'),
    Input('guard-store', 'data'),
)
def update_guard_table(guards):
    # df = guards_to_df(guards)
    # guards = [{'transition': 'notify', 'guard': 'g1'}, {'transition': 'split', 'guard': 'g2'}, {
    #     'transition': 'retry', 'guard': 'g3'}, {'transition': 'create', 'guard': 'g4'}]
    if guards is not None:
        dropdown = {
            # 'guard': {
            #     'options': [{'label': value, 'value': value} for key, value in guards.items()]
            # }
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
    print("upload1")
    if content is not None:
        data, success = parse_contents(content, JSON)
        guards = data['guards']
        return guards
    else:
        print(old_guards)
        return old_guards


@ app.callback(
    Output('valve-store', 'data'),
    Input('upload-valve', 'contents'),
    State('valve-store', 'data')
)
def upload_valves(content, old_valves):
    print("upload2")
    if content is not None:
        data, success = parse_contents(content, JSON)
        valves = data['valves']
        print(valves)
        return valves
    else:
        print(old_valves)
        return old_valves


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
        cur = valves[selected]['cur']
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
def change_valve(value):
    return "Set value to: {}".format(value)


@ app.callback(
    Output('valve-dropdown', 'options'),
    Output('valve-dropdown', 'value'),
    Input('valve-store', 'data')
)
def update_valve(valves):
    print("valve updating", valves)
    if valves is not None:
        options = [{'label': name, 'value': name}
                   for name, value in valves.items()]
        print("dropdown updated", options)
        return options, options[0]['value']
    else:
        return no_update(2)


@ app.callback(
    Output('confirm-define-action', 'displayed'),
    Output('action-repository', 'data'),
    Input(show_button_id(define_action_title), 'n_clicks'),
    State('valve-slider', 'value'),
    State('valve-dropdown', 'value'),
    State('action-specification', 'value'),
    State('action-repository', 'data'),
)
def update_output(n, value, valve_name, action_name, action_repo):
    if n is not None:
        action_repo.append(
            {'Name': action_name, 'Valve': valve_name, "Value": value})
        print(action_repo)
        return True, action_repo
    else:
        return False, action_repo
