import hashlib
import base64

from graphviz import Digraph

from backend.components.misc import container, single_row, button, show_title_maker, show_button_id, global_signal_id_maker, temp_jobs_store_id_maker, global_form_load_signal_id_maker
from dash.dependencies import Input, Output, State
import dash_interactive_graphviz
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from backend.app import app
import pandas as pd
import dash_table
import dash

from backend.param.constants import CVIEW_TITLE, GLOBAL_FORM_SIGNAL, CORR_TITLE, CVIEW_URL, HOME_TITLE, DVIEW_TITLE, JSON, PATTERN_URL, PATTERN_TITLE
from backend.util import add_job, run_task, forget_all_tasks, get_job_id, check_existing_job, read_global_signal_value, read_active_attribute_form, transform_to_guards, write_global_signal_value, no_update, parse_contents
from backend.tasks.tasks import get_remote_data, build_digitaltwin
from dtwin.available.available import AvailableTasks

from flask import request

add_pattern_title = "Add Pattern"

buttons = [
    button(PATTERN_TITLE, show_title_maker, show_button_id),
]

dbc.Row(
    dbc.Col(html.H4("Condition Repository"))
),

table_name = dbc.Row(
    [
        dbc.Col(html.H4("Action Repository")),
        dbc.Col(html.H4("Condition Repository")),
    ]
)

action_pattern_content = dbc.Row(
    [
        dcc.ConfirmDialog(
            id='confirm-action-pattern-update',
            message='Action pattern is added.',
        ),
        dcc.Store(id='action-pattern-repository',
                  storage_type='session', data=[]),
        dcc.Store(id='action-pattern-dot', storage_type='session'),
        dbc.Col(
            dash_table.DataTable(
                id='condition-table',
                columns=[
                    # {'id': 'index', 'name': 'index'},
                    {'id': 'Name', 'name': 'Name'},
                    {'id': 'Expression', 'name': 'Expression'}
                ],
                editable=True)
        ),
        dbc.Col(
            dash_table.DataTable(
                id='action-table',
                columns=[
                    # {'id': 'index', 'name': 'index'},
                    {'id': 'Name', 'name': 'Name'},
                    {'id': 'Valve', 'name': 'Valve'},
                    {'id': 'Value', 'name': 'Value'},
                ],
                editable=True
            )
        )
    ]
)

# pattern_name_input = dbc.FormGroup(
#     [
#         dbc.Label("Pattern Name", html_for="example-email"),
#         dcc.Input(id="pattern-specification",
#                   type="text", placeholder="Enter pattern name"),
#         dbc.FormText(
#             "Are you on email? You simply have to be these days",
#             color="secondary",
#         ),
#     ]
# )

action_input = dbc.FormGroup(
    [
        dbc.Label("Select condition", html_for="example-password"),
        dcc.Dropdown(id='condition-dropdown', multi=True),
        dbc.FormText(
            "You can select multiple conditions.", color="secondary"
        ),
    ]
)

condition_input = dbc.FormGroup(
    [
        dbc.Label("Select action", html_for="example-password"),
        dcc.Dropdown(id='action-dropdown', multi=True),
        dbc.FormText(
            "You can select multiple actions.", color="secondary"
        ),
    ]
)

pattern_content = dbc.Row(
    [
        dbc.Col(action_input),
        dbc.Col(condition_input),

    ]
)

pattern_add = dbc.Row(
    [
        dbc.Col(
            dcc.Input(id="pattern-specification",
                      type="text", placeholder="Enter pattern name"), width="auto"
        ),
        dbc.Col(
            button(add_pattern_title, show_title_maker, show_button_id), width="auto"
        )
    ]
)

page_layout = container('Action Pattern',
                        [
                            table_name,
                            action_pattern_content,
                            html.Hr(),
                            pattern_content,
                            pattern_add,
                            html.Hr(),
                            # dash_interactive_graphviz.DashInteractiveGraphviz(
                            #     id="gv-action-pattern")
                            dash_interactive_graphviz.DashInteractiveGraphviz(
                                id="gv-action-pattern")
                        ]
                        )


@app.callback(
    Output("action-table", "data"),
    Output("condition-table", "data"),
    Input('url', 'pathname'),
    State('action-repository', 'data'),
    State('condition-repository', 'data'),
)
def load_tables(pathname, actions, conditions):
    if pathname == PATTERN_URL:
        return actions, conditions
    return no_update(2)


@app.callback(
    Output('condition-dropdown', 'options'),
    Output('action-dropdown', 'options'),
    Input('url', 'pathname'),
    State('action-repository', 'data'),
    State('condition-repository', 'data'),
)
def update_dropdowns(pathname, actions, conditions):
    if pathname == PATTERN_URL:
        if actions is not None:
            action_options = [{'label': d['Name'],
                               'value': d['Name']} for d in actions]
        else:
            action_options = []
        if conditions is not None:
            condition_options = [{'label': d['Name'],
                                  'value': d['Name']} for d in conditions]
        else:
            condition_options = []
        return condition_options, action_options
    return no_update(2)


# @app.callback(
#     Input('url', 'pathname'),
#     State('action-repository', 'data'),
#     State('condition-repository', 'data'),
# )
# def add_pattern(pathname, actions, conditions):
#     if pathname == PATTERN_URL:
#         return actions, conditions
#     return no_update(2)

@ app.callback(
    Output('confirm-action-pattern-update', 'displayed'),
    Output('action-pattern-repository', 'data'),
    Input(show_button_id(add_pattern_title), 'n_clicks'),
    State('action-pattern-repository', 'data'),
    State('action-dropdown', 'value'),
    State('condition-dropdown', 'value'),
)
def update_output(n, action_pattern_repo, actions, conditions):
    if n is not None:
        print("update output")
        for a in actions:
            for c in conditions:
                action_pattern_repo.append(
                    {'source': c, 'target': a})
        print(action_pattern_repo)
        return True, action_pattern_repo
    else:
        return False, dash.no_update


@ app.callback(
    Output('action-pattern-dot', 'data'),
    Input('action-pattern-repository', 'data'),
)
def update_graph(action_pattern_repo):
    if action_pattern_repo is not None:
        print("update graph")
        g = Digraph("", engine='dot')
        g.graph_attr['rankdir'] = 'LR'
        for ap in action_pattern_repo:
            source = ap['source']
            target = ap['target']
            g.node(source, source)
            g.node(target, target)
            g.edge(source, target)
        return str(g.source)
    else:
        return dash.no_update


@ app.callback(
    Output("gv-action-pattern", "dot_source"),
    Output("gv-action-pattern", "engine"),
    Input('url', 'pathname'),
    Input("action-pattern-dot", "data")
)
def show_ocpn(pathname, value):
    if pathname == PATTERN_URL and value is not None:
        print("show ocpn")
        print(value)
        print(type(value))
        dot_source = """digraph  {
            node[style="filled"]
            a ->b->d
            a->c->d
            }
            """
        print(value)
        return value, "dot"
    return no_update(2)
