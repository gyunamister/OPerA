from datetime import datetime, date
from math import ceil, floor

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
from backend.tasks.tasks import get_remote_data
from flask import request

# https://dash.plotly.com/layout
from subprocess import check_call
from backend.app import app
import dash_table
import pandas as pd
from backend.components.misc import inspect_trace_button, log_header, use_log_button, tab_id, \
    interpretation_trace_button
from backend.param.available import extract_title, get_available_from_name
from backend.param.colors import SECONDARY_VERY_LIGHT, SECONDARY, INTRINSIC_COLOR_LIGHT, INTRINSIC_COLOR_VERY_LIGHT, \
    NORMAL_COLOR_VERY_LIGHT, NORMAL_COLOR_LIGHT
from backend.param.constants import RESULT_TITLE, TOP_KEY, DP, SUMMARY_KEY, NA, CONTEXT_KEY
from backend.param.styles import act_style, TABLE_ROW_STYLE, HTML_TABLE_CELL_STYLE, NO_DISPLAY
from backend.util import write_global_signal_value, display_time
from dtwin.available.available import AvailableTasks, AvailableSelections, AvailableGranularity
from dtwin.available.constants import HOURS_IN_DAY
from dtwin.parsedata.objects.exporter.exporter import export_to_pm4py, TID_KEY, EVENTS_KEY, COLOR_KEY, ACT_KEY, \
    export_log_to_dict, export_logs_to_dict, TIMESTAMP_KEY, export_trace_to_dataframe, \
    export_oc_data_events_to_dataframe, export_trace_to_dict, VALUES_KEY, OBJECTS_KEY
from dtwin.parsedata.objects.oclog import Trace, ObjectCentricLog


def generate_table_from_df(dataframe, max_rows=10):
    return html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in dataframe.columns])
        ),
        html.Tbody([
            html.Tr([
                html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))
        ])
    ])


def generate_log_statistics(log):
    from pm4py.statistics.traces.log import case_statistics
    from pm4py.statistics.traces.log import case_arrival
    from pm4py.statistics.start_activities.log.get import get_start_activities
    from pm4py.statistics.end_activities.log.get import get_end_activities
    from pm4py.algo.filtering.log.attributes import attributes_filter as log_attributes_filter
    import pandas as pd
    pm4py_log = export_to_pm4py(log)
    # Time
    median_case_duration = case_statistics.get_median_caseduration(pm4py_log, parameters={
        case_statistics.Parameters.TIMESTAMP_KEY: TIMESTAMP_KEY.title()
    })
    case_dispersion_ratio = case_arrival.get_case_dispersion_avg(pm4py_log, parameters={
        case_arrival.Parameters.TIMESTAMP_KEY: TIMESTAMP_KEY.title()})
    case_number = len(log.traces)
    case_metrics = {'Log Size': case_number,
                    'Median Trace Duration': display_time(median_case_duration, 4),
                    'Average Trace Arrival': display_time(case_dispersion_ratio, 4)}
    df_case_metrics = pd.DataFrame(case_metrics, index=[0])
    table_case_metrics = create_data_table(
        None, df_case_metrics, None, len(df_case_metrics))

    # Determine statistics for variants counts
    variants_count = case_statistics.get_variant_statistics(pm4py_log)
    variants_count = sorted(
        variants_count, key=lambda x: x['count'], reverse=True)
    average_trace_len = sum(
        [len(trace['variant'].split(',')) * trace['count'] for trace in variants_count]) / case_number
    df_variants_count = pd.DataFrame(variants_count)
    variants_table = create_data_table(None, df_variants_count, None, 10)

    # Start and end
    start_activities = get_start_activities(pm4py_log)
    start_activities = {k: v for k, v in sorted(
        start_activities.items(), key=lambda item: item[1], reverse=True)}
    df_start_activities = pd.DataFrame(start_activities, index=[0])
    table_start_activities = create_data_table(
        None, df_start_activities, None, len(df_start_activities))
    end_activities = get_end_activities(pm4py_log)
    end_activities = {k: v for k, v in sorted(
        end_activities.items(), key=lambda item: item[1], reverse=True)}
    df_end_activities = pd.DataFrame(end_activities, index=[0])
    table_end_activities = create_data_table(
        None, df_end_activities, None, len(df_end_activities))

    # Activity frequencies
    act_freq = log_attributes_filter.get_attribute_values(
        pm4py_log, "concept:name")
    act_freq = {k: v for k, v in sorted(
        act_freq.items(), key=lambda item: item[1], reverse=True)}
    df_act_freq = pd.DataFrame(act_freq, index=[0])
    act_freq_table = create_data_table(
        None, df_act_freq, None, len(df_act_freq))
    return [
        html.H3('Log Statistics'),
        html.H4('Top 10 Most Frequent Trace Variants'),
        variants_table,
        html.Br(),
        html.H4('Trace Metrics'),
        table_case_metrics,
        html.Br(),
        html.H4('Activity Statistics'),
        html.H5('Activity Frequencies'),
        act_freq_table,
        html.Br(),
        html.H5('Start Activities'),
        table_start_activities,
        html.Br(),
        html.H5('End Activities'),
        table_end_activities,
        html.Br()
    ]


def generate_log_output(log, log_hash, task_id, method, multiple):
    if multiple:
        log_exports = export_logs_to_dict(log)
        return [
            html.Div(

                log_header('Log from Object Path Combination ' + log_name) +
                use_log_button(write_global_signal_value([log_name, log_hash, task_id, method])) +
                generate_log_statistics(log[log_name]) +
                [html.H3('Log Preview'),
                 html.Br()] +
                generate_table_from_log(log_exports[log_name], log_hash, task_id, log_name) +
                [html.Br()]
            )
            for log_name in log_exports]
    else:
        log_export = export_log_to_dict(log)
        return log_header('Log from Event Correlation ' + method) + \
            use_log_button(write_global_signal_value([log_hash, task_id, method])) + \
            generate_log_statistics(log) + \
            [html.H3('Log Preview'),
             html.Br()] + \
            generate_table_from_log(log_export, log_hash, task_id)


def generate_table_from_log(log_export, log_hash, task_id, log_name=''):
    return [html.Table([
        html.Thead(
            html.Tr([html.Th(col)
                    for col in ['TraceID', 'Events', '']], style=TABLE_ROW_STYLE)
        ),
        html.Tbody([
            html.Tr(
                [html.Td(log_export[tid][TID_KEY])] +
                [html.Td(
                    html.Div([html.Div([html.Div(style=act_style(event[COLOR_KEY])),
                                        event[ACT_KEY]], style=HTML_TABLE_CELL_STYLE) if index != 7 else
                              html.Div("...", style=HTML_TABLE_CELL_STYLE) if len(log_export[tid][EVENTS_KEY]) > 7 else
                              html.Div([html.Div(style=act_style(event[COLOR_KEY])),
                                        event[ACT_KEY]], style=HTML_TABLE_CELL_STYLE)
                              for index, event in enumerate(log_export[tid][EVENTS_KEY]) if index <= 7],
                             style={'overflow': 'hidden'})
                )] +
                [html.Td(inspect_trace_button(write_global_signal_value([log_name, log_hash, task_id, str(tid)])))], style=TABLE_ROW_STYLE)
            for tid in range(len(log_export)) if tid <= 20]
        )
    ], style=TABLE_ROW_STYLE)]


def get_background_color(label):
    return NORMAL_COLOR_LIGHT


def create_data_table(date, df, name, rows, header_color=SECONDARY, header_weight='bold', minWidth='180px',
                      maxWidth='180px',
                      width='180px'):
    if name is not None:
        header = [html.H5(name),
                  html.H6(date)]
    else:
        header = []
    return html.Div(header + [
        dash_table.DataTable(
            style_table={'overflowX': 'auto'},
            style_cell={
                'height': 'auto',
                # all three widths are needed
                'minWidth': minWidth, 'width': width, 'maxWidth': maxWidth,
                'whiteSpace': 'normal',
                'textAlign': 'left',
                'textOverflow': 'ellipsis'
            },
            data=df[:rows].to_dict('records'),
            columns=[{'name': i, 'id': i} for i in df.columns],
            css=[{
                'selector': '.dash-spreadsheet td div',
                'rule': '''
                            line-height: 15px;
                            max-height: 30px; min-height: 30px; height: 30px;
                            display: block;
                            overflow-y: hidden;
                        '''
            }],
            tooltip_data=[
                {
                    column: {'value': str(value), 'type': 'markdown'}
                    for column, value in row.items()
                } for row in df.to_dict('records')
            ],
            tooltip_duration=None,
            style_as_list_view=True,
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': SECONDARY_VERY_LIGHT
                }
            ],
            style_header={
                'backgroundColor': header_color,
                'fontWeight': header_weight,
                'color': 'white' if header_color == SECONDARY else 'black'
            }
        ),
    ])


def create_oc_data_dfs(oc_data):
    meta = oc_data.meta
    # Unfortunately, need to fix it this way, since in Celery only
    df_acts = pd.DataFrame(columns=list(meta.acts))
    df_ots = pd.DataFrame(columns=meta.obj_types)
    # df_act_ot = pd.DataFrame(meta.act_obj)
    df_vals = pd.DataFrame(columns=meta.attr_names)
    df_valt = pd.DataFrame(columns=meta.attr_types)
    df_valtt = pd.DataFrame(meta.attr_typ, index=[0])
    df_act_val = pd.DataFrame(meta.act_attr)
    df_events = export_oc_data_events_to_dataframe(
        oc_data.raw.events, oc_data.raw.objects, rows=20)
    if len(meta.ress) > 0:
        df_res = pd.DataFrame(columns=list(meta.ress))
        res_out = [html.H3('Resources'),
                   create_data_table(None, df_res, None, len(df_res), SECONDARY_VERY_LIGHT, 'medium')]
    else:
        res_out = dash.no_update
    if len(meta.locs) > 0:
        df_loc = pd.DataFrame(columns=list(meta.locs))
        loc_out = [html.H3('Locations'),
                   create_data_table(None, df_loc, None, len(df_loc), SECONDARY_VERY_LIGHT, 'medium')]
    else:
        loc_out = dash.no_update
    return df_act_val, df_acts, df_ots, df_vals, df_valt, df_valtt, loc_out, meta, res_out, df_events


def generate_events_table(events, event_to_traces, log_hash, objects,
                          vmap_params, values):
    event_df = pd.DataFrame()
    sit_len = len(events)
    rows = ceil(sit_len / 12)
    row_indices = [r * 12 for r in range(rows + 2)]
    i = 0
    inspect_trace_buttons = []
    for index, event in enumerate(sorted(events,
                                         key=lambda item: item.time)):
        # TODO possibly add omap and vmap here
        event_df[event.id] = [values[index],
                              event.act,
                              ','.join(
                                  list({objects[oid].type for oid in event.omap})),
                              event.vmap[vmap_params[AvailableSelections.RESOURCE]]
                              if AvailableSelections.RESOURCE in vmap_params else NA,
                              event.vmap[vmap_params[AvailableSelections.LOCATION]]
                              if AvailableSelections.LOCATION in vmap_params else NA,
                              event.time]
        if row_indices[i] <= index < row_indices[i + 1]:
            if index % 12 == 0:
                row_buttons = [dbc.Col(inspect_trace_button(write_global_signal_value([RESULT_TITLE,
                                                                                       log_hash,
                                                                                       str(event_to_traces[
                                                                                           event.id]),
                                                                                       str(datetime.now())]),
                                                            suffix=str(
                                                                event.id),
                                                            version=False,
                                                            result=CONTEXT_KEY))]
            else:
                row_buttons.append(dbc.Col(inspect_trace_button(write_global_signal_value([RESULT_TITLE,
                                                                                           log_hash,
                                                                                           str(event_to_traces[
                                                                                               event.id]),
                                                                                           str(
                                                                                               datetime.now())]),
                                                                suffix=str(
                                                                    event.id),
                                                                version=False,
                                                                result=CONTEXT_KEY)))
        else:
            i += 1
            inspect_trace_buttons.append(dbc.Row(row_buttons))
            row_buttons = [dbc.Col(inspect_trace_button(write_global_signal_value([RESULT_TITLE,
                                                                                   log_hash,
                                                                                   str(event_to_traces[
                                                                                       event.id]),
                                                                                   str(datetime.now())]),
                                                        suffix=str(event.id),
                                                        version=False,
                                                        result=CONTEXT_KEY))]
    remainder = sit_len % 12
    if remainder != 0:
        for i in range(12 - remainder):
            row_buttons.append(dbc.Col())
        inspect_trace_buttons.append(dbc.Row(row_buttons))
    event_df.index = ['Context', 'Activity',
                      'Object Types', 'Resource', 'Location', 'Date']
    event_df.reset_index(inplace=True)
    event_df.rename(columns={'index': 'EventID'}, inplace=True)
    width = '100px'
    event_table = create_data_table(None, event_df, None, len(event_df),
                                    minWidth=width,
                                    width=width,
                                    maxWidth=width)
    return event_table, inspect_trace_buttons
