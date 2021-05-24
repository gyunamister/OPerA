import base64
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import hashlib
import uuid

from backend.app import app
from backend.components.misc import container, collapse_button_id, button, single_row, \
    collapse_title_maker, compute_title_maker, compute_button_id, card, global_signal_id_maker, \
    temp_jobs_store_id_maker, form_persistence_id_maker, global_form_load_signal_id_maker, goto_title_maker, \
    goto_button_id
from backend.components.tables import create_data_table
from backend.components.userforms import form_dropdown_row, make_job_option, empty_radio_item, \
    radio_item_id_maker, radio_items, create_attribute_forms, attribute_form_id
from backend.param.constants import CSV, JSON, DEFAULT_JOBS, CSV_ATTRIBUTES_FST, NA, CSV_ATTRIBUTES_SND, \
    JOBS_KEY, JOB_DATA_DATE_KEY, JOB_DATA_NAME_KEY, CSV_ATTRIBUTES_FST_MULT, CSV_ATTRIBUTES_SND_MULT, \
    JOB_DATA_TYPE_KEY, CORR_URL, CORR_TITLE, PARSE_TITLE, STORES_SIGNALS, FORMS, GLOBAL_FORM_SIGNAL, DEFAULT_FORM, \
    ATTRIBUTE_CSV_TEXT, ATTRIBUTE_OCEL_TEXT, SHOW_PREVIEW_ROWS, DEV_CTX_TITLE, MDL, CVIEW_TITLE, HOME_TITLE
from backend.param.styles import LINK_CONTENT_STYLE, CENTER_DASHED_BOX_STYLE, NO_DISPLAY, FONT_STYLE, BUTTON_LEFT_STYLE
from backend.tasks.tasks import store_redis_backend, parse_data, get_remote_data, db, user_log_key
from backend.util import add_job, run_task, forget_all_tasks, get_job_id, check_existing_job, \
    parse_contents, read_active_attribute_form, build_csv_param, write_global_signal_value, \
    set_special_attributes, get_attribute_form_dict, guarantee_list_input, no_update, build_json_param, \
    read_global_signal_value
from celery.result import AsyncResult
from dtwin.available.available import AvailableTasks, AvailableSelections
from dtwin.parsedata.objects.exporter.exporter import export_oc_data_events_to_dataframe
from dash.dependencies import Input, Output, State
from datetime import datetime

from flask import request
from pandas.core.frame import DataFrame
from time import sleep

jobs_title = "Variants"
jobs_title_hidden = "hidden-jobs"
upload_table_title = 'all rows'
parse_title = 'parse'
goto_title = 'Correlate'
remove_jobs_title = 'remove variants'
start_from_last_job = 'selected variant'
selected_attribute_form = 'selected-attribute-selection'

default_attribute_layout = [
    dbc.Row(
        dbc.Col(
            html.Div(id='output-messages'))),
    dbc.Collapse(
        [
            single_row(
                html.H2("Attribute Selection")
            ),
            dcc.Loading(
                id=f"loading-1",
                type="default",
                children=html.Div(
                    [

                    ], id='active-attribute-selection')
            ),
            html.Div(
                [

                ], id='nonactive-attribute-selection', style=NO_DISPLAY),
            single_row(
                html.Div(
                    [
                        button(parse_title,
                               compute_title_maker,
                               compute_button_id,
                               href=CORR_URL),
                        button(goto_title,
                               goto_title_maker,
                               goto_button_id,
                               href=CORR_URL,
                               style=BUTTON_LEFT_STYLE)
                    ]), 'end'),
            html.Hr(),
            single_row(
                html.H2("Data Preview")
            )
        ],
        id='show-upload-table',
        is_open=False),
    dbc.Row(dbc.Col(html.Div(id='output-data-upload')))]

session_id = str(uuid.uuid4())

upload_tab_content = card(
    [
        html.Div(
            [
                html.Br(),
                html.H2("Upload Data"),
                html.Br(),
                dcc.Markdown('''Please note that the format for CSV files with columns containing multiple entries (e.g 
                multiple object ids for a specific object type) needs to comply to the following: Each of those entries
                needs to be enclosed with ", e.g. "id1, id2, id3 ...". '''),
                html.Br(),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Upload(
                                id='upload-data',
                                children=html.Div([
                                    'Drag and Drop or ', html.A(
                                        'Select a CSV or OCEL JSON File')
                                ],
                                    style=LINK_CONTENT_STYLE),
                                style=CENTER_DASHED_BOX_STYLE,
                                multiple=False
                            ),
                            width={"size": 11})
                    ],
                    justify='start'
                ),
            ]
        ),
        html.Br(),
        html.Div(default_attribute_layout, id='outer-attribute-selection'),
        html.Br(),
        html.Br(),
        html.Div(id='signal-celery-upload', style=NO_DISPLAY),
        html.Div(id='signal-sync-form', style=NO_DISPLAY),
        html.Div(id='signal-reset', style=NO_DISPLAY),
        html.Div(id='signal', style=NO_DISPLAY),
        html.Div(session_id, id='session-id', style=NO_DISPLAY),
        html.Div(id='show-upload-rows', style=NO_DISPLAY, children='10')])

jobs_tab_content = card(
    [
        single_row(html.H2("Variants Dashboard")),
        dbc.Row([dbc.Col(button(start_from_last_job,
                                collapse_title_maker,
                                collapse_button_id)),
                 dbc.Col(button(remove_jobs_title,
                                compute_title_maker,
                                compute_button_id))]),
        html.Div(empty_radio_item(jobs_title, True), id='job-radio')
    ])

# Page layout
page_layout = container("Action-Oriented Process Mining using Action Patterns",
                        [
                            dbc.Tabs([
                                dbc.Tab(upload_tab_content,
                                        label="Upload", tab_id='upload'),
                                dbc.Tab(jobs_tab_content,
                                        label="Variants", tab_id='variants')
                            ], id='home-tabs')
                        ])

# Reset Stores and Attribute Selection on removing all jobs


@app.callback(Output('job-radio', 'children'),
              Output('outer-attribute-selection', 'children'),
              Input('jobs-store', 'clear_data'),
              State('init', 'data'))
def clear_radio(dummy, clear):
    if not clear:
        return [empty_radio_item(jobs_title, True)], default_attribute_layout
    else:
        return dash.no_update, dash.no_update


# Handle initializing jobs, uploading data and creating the jobs radio
@app.callback(
    Output('signal', 'children'),
    Output('jobs-store', 'data'),
    Output('output-messages', 'children'),
    Output(radio_item_id_maker(jobs_title), 'options'),
    Output(radio_item_id_maker(jobs_title), 'style'),
    Output(radio_item_id_maker(jobs_title), 'value'),

    Input('session-id', 'children'),
    Input('upload-data', 'contents'),

    State('upload-data', 'filename'),
    State('jobs-store', 'data'),
    State(radio_item_id_maker(jobs_title), 'options'),
    State('last-job', 'data')
)
def upload_data(session, content, name, jobs, options, last_job):
    if content is not None:
        date = datetime.now()
        # Check data format
        if CSV in name:
            data_format = CSV
        elif JSON in name:
            data_format = JSON
        elif MDL in name:
            data_format = MDL
        else:
            return dash.no_update, dash.no_update,
            html.Div(dbc.Alert("You have uploaded a log in the wrong format. Please only upload logs in csv "
                               "or json format.", color="warning")), \
                dash.no_update, dash.no_update, dash.no_update
        # compute value and send a signal when done
        content_type, content_string = content.split(',')
        log_hash = hashlib.md5(base64.b64decode(content_string)).hexdigest()
        if jobs is None:
            # Create default jobs dict for empty jobs-store
            jobs = DEFAULT_JOBS
        if check_existing_job(jobs, log_hash):
            # The dataset was already uploaded
            job_id = get_job_id(jobs, log_hash)
            return dash.no_update,
            dash.no_update, html.Div(dbc.Alert("You have uploaded this log already. Please look for job id "
                                               + str(job_id) + " under the jobs tab.", color="info")), \
                dash.no_update, dash.no_update, dash.no_update
        else:
            # Save new job
            add_job(data_format, date, jobs, log_hash, name)
            # Parse raw data
            out, success = parse_contents(content, data_format)
            if success:
                if data_format == CSV:
                    task_id = run_task(jobs, log_hash, AvailableTasks.UPLOAD.value,
                                       store_redis_backend, data=out)
                elif data_format == MDL:
                    task_id = run_task(jobs, log_hash, AvailableTasks.UPLOAD.value,
                                       store_redis_backend, data=out)
                else:
                    json_param = build_json_param(NA, NA)
                    task_id = run_task(jobs, log_hash, AvailableTasks.UPLOAD.value, parse_data,
                                       data=out,
                                       data_type=data_format,
                                       parse_param=json_param,
                                       resource=False,
                                       location=False)
                # return write_global_signal_value([session, log_hash, data_format, name, str(date)]), \
                    # jobs, \
                    #     '', \
                    #     options + make_job_option(jobs, log_hash), \
                    #     FONT_STYLE, \
                    #     log_hash
                return write_global_signal_value([session, log_hash, data_format, name, str(date)]), jobs, '', options + make_job_option(jobs, log_hash), FONT_STYLE, log_hash
            else:
                return dash.no_update, dash.no_update, dash.no_update, html.Div(
                    dbc.Alert("There was a problem processing the uploaded file. Please check the syntactic "
                              "correctness of the file with respect to pandas.read_csv "
                              "in case of csv and to json.loads in case of json after base64 encoding "
                              "and decoding", color='danger')), dash.no_update, dash.no_update, dash.no_update
    else:
        if jobs is not None and len(jobs[JOBS_KEY]) != 0:
            labels = [make_job_option(jobs, log_hash)
                      for log_hash in jobs[JOBS_KEY]]
            labels = [option for sublist in labels for option in sublist]
            return dash.no_update, dash.no_update, dash.no_update, labels, FONT_STYLE, last_job
        else:
            return tuple([dash.no_update] * 6)


# Update Attribute Selection and Data Preview based on new job or selected job
@app.callback(
    Output('show-upload-table', 'is_open'),
    Output('output-data-upload', 'children'),
    Output('nonactive-attribute-selection', 'children'),
    Output('active-attribute-selection', 'children'),
    Output('init', 'data'),
    Output(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    Output('last-job', 'data'),
    Output(global_signal_id_maker(HOME_TITLE), 'children'),

    Input(collapse_button_id(start_from_last_job), 'n_clicks'),
    Input('signal', 'children'),

    State(radio_item_id_maker(jobs_title), 'value'),
    State("home-tabs", "active_tab"),
    State('jobs-store', 'data'),
    State('nonactive-attribute-selection', 'children'),
    State('active-attribute-selection', 'children'),
    State('init', 'data'),
    State(form_persistence_id_maker(PARSE_TITLE), 'data'))
def update_home_output(n, value, radio_value, at, jobs, nonactive, active, init, form):
    user = request.authorization['username']
    if init and len(jobs[JOBS_KEY]) != 0:
        # Initialize
        dfs = [get_remote_data(user, log_hash, jobs, AvailableTasks.UPLOAD.value)
               for log_hash in jobs[JOBS_KEY]]
        forms = create_attribute_forms(jobs, dfs, form)
        if radio_value is None:
            return dash.no_update, dash.no_update, forms, dash.no_update, False, \
                dash.no_update, dash.no_update, dash.no_update
        return dash.no_update, dash.no_update, forms, dash.no_update, False, \
            write_global_signal_value(
                [radio_value, str(datetime.now())]), dash.no_update, write_global_signal_value(
                [radio_value, str(datetime.now())])

    else:
        rows = SHOW_PREVIEW_ROWS
        if value is not None and at == 'upload':
            # Newly uploaded data --> new job
            session, log_hash, data_format, name, date = read_global_signal_value(
                value)
            if data_format == CSV or data_format == MDL:
                data = get_remote_data(
                    user, log_hash, jobs, AvailableTasks.UPLOAD.value)
                return True, \
                    create_data_table(date, data, name, rows), \
                    nonactive + active, \
                    [html.Div(
                        [
                            radio_items([log_hash], log_hash, log_hash,
                                        persistence=True, style=NO_DISPLAY),
                            html.Br(),
                            html.P(ATTRIBUTE_CSV_TEXT),
                            form_dropdown_row(data.columns, CSV_ATTRIBUTES_FST,
                                              CSV_ATTRIBUTES_FST_MULT,
                                              log_hash,
                                              True),
                            form_dropdown_row([NA] + [col for col in data.columns],
                                              CSV_ATTRIBUTES_SND,
                                              CSV_ATTRIBUTES_SND_MULT,
                                              log_hash,
                                              True)
                        ], id=attribute_form_id(log_hash)
                    )], \
                    dash.no_update, \
                    dash.no_update, \
                    log_hash, \
                    dash.no_update
            else:
                oc_data = get_remote_data(
                    user, log_hash, jobs, AvailableTasks.UPLOAD.value)
                df_events = export_oc_data_events_to_dataframe(
                    oc_data.raw.events, oc_data.raw.objects, rows)
                return True, \
                    create_data_table(date, df_events, name, rows), \
                    nonactive + active, \
                    [html.Div(
                        [
                            radio_items([log_hash], log_hash, log_hash,
                                        persistence=True, style=NO_DISPLAY),
                            html.Br(),
                            html.P(ATTRIBUTE_OCEL_TEXT),
                            form_dropdown_row([NA] + oc_data.meta.attr_events, CSV_ATTRIBUTES_FST,
                                              CSV_ATTRIBUTES_FST_MULT,
                                              log_hash,
                                              True,
                                              style=NO_DISPLAY),
                            form_dropdown_row([NA] + oc_data.meta.attr_events,
                                              CSV_ATTRIBUTES_SND,
                                              CSV_ATTRIBUTES_SND_MULT,
                                              log_hash,
                                              True)
                        ], id=attribute_form_id(log_hash)
                    )], \
                    dash.no_update, \
                    dash.no_update, \
                    log_hash, \
                    dash.no_update
        else:
            # User selected a different job from all jobs --> change focus
            if n is not None and nonactive is not None:
                if len(nonactive) == 0:
                    return no_update(8)
                data = get_remote_data(
                    user, radio_value, jobs, AvailableTasks.UPLOAD.value)
                all_forms = nonactive + active
                new_active = []
                new_nonactive = []
                for child in all_forms:
                    if 'id' in child['props'] and child['props']['id'] == attribute_form_id(radio_value):
                        new_active.append(child)
                    else:
                        new_nonactive.append(child)
                if isinstance(data, DataFrame):
                    return True, \
                        create_data_table(jobs[JOBS_KEY][radio_value][JOB_DATA_DATE_KEY],
                                          data,
                                          jobs[JOBS_KEY][radio_value][JOB_DATA_NAME_KEY],
                                          rows), \
                        new_nonactive, \
                        new_active, \
                        dash.no_update, \
                        write_global_signal_value([radio_value, str(datetime.now())]), \
                        radio_value, \
                        write_global_signal_value(
                            [radio_value, str(datetime.now())])
                else:
                    df_events = export_oc_data_events_to_dataframe(
                        data.raw.events, data.raw.objects, rows)
                    return True, \
                        create_data_table(jobs[JOBS_KEY][radio_value][JOB_DATA_DATE_KEY],
                                          df_events,
                                          jobs[JOBS_KEY][radio_value][JOB_DATA_NAME_KEY],
                                          rows), \
                        new_nonactive, \
                        new_active, \
                        dash.no_update, \
                        write_global_signal_value([radio_value, str(datetime.now())]), \
                        radio_value, write_global_signal_value(
                            [radio_value, str(datetime.now())])
            else:
                # Empty jobs don't need initialization
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, False, \
                    dash.no_update, dash.no_update, dash.no_update


# Start job reset
@app.callback(
    [
        Output('jobs-store', 'clear_data'),
        Output('last-job', 'clear_data'),
        Output('upload-data', 'contents')
    ] +
    [
        Output(temp_jobs_store_id_maker(title), 'clear_data') for title in STORES_SIGNALS
    ] +
    [
        Output(form_persistence_id_maker(title), 'clear_data') for title in FORMS
    ],
    Input(compute_button_id(remove_jobs_title), 'n_clicks'),
    [
        State('jobs-store', 'data')
    ] +
    [
        State(temp_jobs_store_id_maker(title), 'data') for title in STORES_SIGNALS
    ]
)
def init_jobs(n, jobs, jobs1, jobs2, jobs3, jobs4, jobs5, jobs6, jobs7, jobs8, jobs9, jobs10, job11, job12, job13, job14):
    jobs_list = [jobs, jobs1, jobs2, jobs3,
                 jobs4, jobs5, jobs6, jobs7, jobs8, jobs9, jobs10, job11, job12, job13, job14]
    if n is not None and any([job is not None for job in jobs_list]):
        # Forget all the celery task results in the redis results backend associated with a stored job
        for job in jobs_list:
            forget_all_tasks(jobs)
        return tuple([True, True, None] + [True] * 15)
    else:
        return tuple([dash.no_update] * 23)

#
