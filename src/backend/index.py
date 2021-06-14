import json
import os
from datetime import datetime

import dash
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
from backend.app import app
from backend.components.misc import global_signal_id_maker, temp_jobs_store_id_maker, form_persistence_id_maker, \
    global_url_signal_id_maker, global_form_load_signal_id_maker, global_refresh_signal_id_maker
from backend.pages.about import page_layout as about_layout
from backend.pages.control_view import page_layout as controlview_layout
from backend.pages.diagnostics_view import page_layout as diagnosticsview_layout
from backend.pages.dashboard import page_layout as dashboard_layout
from backend.pages.action_pattern import page_layout as pattern_layout
from backend.pages.home import page_layout as home_layout
from backend.param.constants import DEFAULT_JOBS, CORR_URL, ABOUT_URL, \
    DEFAULT_FORM, STORES_SIGNALS, CORR_OUT_URL, FORMS, TRACE_SIGNAL, TRACE_URL, DEV_CTX_URL, MULTI_PAGE_URLS, \
    GLOBAL_FORM_SIGNAL, RESULT_URL, TRACE_RESULT_SIGNAL, MULTI_PAGE_REFRESH, CVIEW_URL, DVIEW_URL, DASHBOARD_URL, PATTERN_URL
from backend.param.styles import GLOBAL_STYLE, NO_DISPLAY
from backend.util import read_global_signal_value, no_update
from dash.dependencies import Input, Output

from dotenv import load_dotenv

load_dotenv()

with open('username_pwd.json') as json_file:
    data = json.load(json_file)


app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),
    dcc.Store(id='init', storage_type='memory', data=True),
    dcc.Store(id='last-job', storage_type='session'),
    dcc.Store(id='jobs-store', storage_type='session', data=DEFAULT_JOBS),
    dcc.Store(id='action-repository', storage_type='session', data=[]),
    dcc.Store(id='condition-repository', storage_type='session', data=[]),
    dcc.Store(id='action-pattern-repository',
              storage_type='session', data=[]),
    dcc.Interval(id='interval-component', disabled=True,
                 interval=24*1000, n_intervals=0),
] + [
    dcc.Store(id=temp_jobs_store_id_maker(title),
              storage_type='session', data=DEFAULT_JOBS)
    for title in STORES_SIGNALS
] + [
    dcc.Store(id=form_persistence_id_maker(
        title), storage_type='session', data=DEFAULT_FORM)
    for title in FORMS
] + [
    html.Div(id=global_signal_id_maker(
        title), style=NO_DISPLAY)
    for title in STORES_SIGNALS
] + [
    html.Div(id=global_signal_id_maker(
        TRACE_SIGNAL), style=NO_DISPLAY),
    html.Div(id=global_signal_id_maker(
        TRACE_RESULT_SIGNAL), style=NO_DISPLAY)
] + [
    html.Div(id=global_url_signal_id_maker(
        title), style=NO_DISPLAY)
    for title in MULTI_PAGE_URLS
] + [
    html.Div(id=global_refresh_signal_id_maker(
        title), style=NO_DISPLAY)
    for title in MULTI_PAGE_REFRESH
] + [
    html.Div(id=global_form_load_signal_id_maker(
        GLOBAL_FORM_SIGNAL), style=NO_DISPLAY)
],
    style=GLOBAL_STYLE
)


@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == ABOUT_URL:
        return about_layout
    elif pathname == CVIEW_URL:
        return controlview_layout
    elif pathname == DVIEW_URL:
        return diagnosticsview_layout
    elif pathname == DASHBOARD_URL:
        return dashboard_layout
    elif pathname == PATTERN_URL:
        return pattern_layout
    else:
        return home_layout


@app.callback(
    [
        Output('url', 'pathname')
    ] + [
        Output(global_refresh_signal_id_maker(title), 'children')
        for title in MULTI_PAGE_REFRESH
    ],
    [
        Input(global_url_signal_id_maker(title), 'children') for title in MULTI_PAGE_URLS
    ] + [
        Input('url', 'pathname')
    ]

)
def multi_page_urls(*args):
    args = args[:-1]
    # Necessary, since only a single callback with output to Output('url', 'pathname') is allowed and
    # for wildcard callbacks, buttons with href do not work, since the page_layout is changed before the wildcard
    # callback is called
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if 'url' == trigger_id:
        return no_update(1 + len(MULTI_PAGE_REFRESH))
    else:
        if not all([i is None for i in args]):
            candidates = []
            for index, arg in enumerate(args):
                if arg is not None:
                    candidates.append(read_global_signal_value(arg))
            url = max(candidates, key=lambda t: t[1])[0]
            return tuple([url] + [
                str(datetime.now())
                if url == refresh_url else dash.no_update
                for refresh_url in MULTI_PAGE_REFRESH
            ])
        else:
            return no_update(1 + len(MULTI_PAGE_REFRESH))


auth = dash_auth.BasicAuth(
    app,
    data['VALID_USERNAME_PASSWORD_PAIRS']
)

app.scripts.config.serve_locally = True

localhost_or_docker = os.getenv('LOCALHOST_OR_DOCKER', "Value does not exist")
debug_mode = os.getenv('DEBUG_MODE', "Value does not exist")

if __name__ == '__main__':
    if debug_mode == 'true':
        debug = True
    else:
        debug = False
    if localhost_or_docker == 'localhost':
        app.run_server(
            debug=debug,
            port=8050,
            dev_tools_hot_reload=False, use_reloader=False
        )
    else:
        app.run_server(
            host='0.0.0.0',
            debug=debug,
            port=8050,
            dev_tools_hot_reload=True, use_reloader=False
        )
