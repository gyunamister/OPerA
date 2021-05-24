from datetime import datetime

import dash

from backend.components.misc import collapse_button_id, tooltip_button_id, modal_id, modal_close_button_id, \
    checklist_id_maker, collapse_id, toast_id, temp_jobs_store_id_maker, global_signal_id_maker, \
    global_form_load_signal_id_maker
from backend.components.tables import generate_interpretation_for_trace
from backend.param.constants import RESULT_TITLE, GLOBAL_FORM_SIGNAL, RESULT_INIT, CB_TYPE_INTERPRETATION
from backend.util import read_global_signal_value, no_update
from dash.dependencies import Output, Input, State, ALL


def collapse_button_callback(app, title):
    @app.callback(
        Output(title, "is_open"),
        Input(collapse_button_id(title), "n_clicks"),
        State(title, "is_open"),
    )
    def toggle_collapse(n, is_open):
        if n:
            return not is_open
        return is_open


def tab_callback(app, idx, ids, output, output_val):
    @app.callback(
        output,
        [Input(idx, "active_tab")]
    )
    def on_switch_tab(at):
        if at == ids[0]:
            return output_val
        else:
            return output_val


def modal_callback(app, title):
    @app.callback(
        Output(modal_id(title), 'is_open'),
        Input(tooltip_button_id(title), "n_clicks"),
        Input(modal_close_button_id(title), "n_clicks"),
        State(modal_id(title), "is_open")
    )
    def toggle_modal(n1, n2, is_open):
        if n1 or n2:
            return not is_open
        return is_open


def toast_summary_graph_callback(app, title, det):
    @app.callback(
        Output(toast_id(title), 'is_open'),
        Output(toast_id(title), 'children'),
        Input(title, 'clickData'),
        State(global_signal_id_maker(RESULT_TITLE), 'children'),
        State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
        State(temp_jobs_store_id_maker(RESULT_TITLE), 'data')
    )
    def init_toggle_toast(click, value, form_value, jobs):
        if click is None:
            return no_update(2)
        log_hash = read_values(form_value, value)
        # if log_hash is None: return no_update(2)
        hover = 'hovertext'
        if hover not in click['points'][0]:
            # No trace selected
            return no_update(2)
        tid = click['points'][0]['hovertext']
        ps_ctx_val = float(click['points'][0]['x'])
        ng_ctx_val = float(click['points'][0]['y'])
        start = click['points'][0]['customdata'][2]
        end = click['points'][0]['customdata'][3]
        interpretation = generate_interpretation_for_trace(end, jobs, log_hash, ng_ctx_val, ps_ctx_val, start, tid, det)
        return True, interpretation


def read_values(form_value, value):
    if value is not None and form_value is not None:
        log_hash_global, date_global = read_global_signal_value(form_value)
        log_hash_local, task_id, date_local = read_global_signal_value(value)
        date_global = datetime.strptime(date_global, '%Y-%m-%d %H:%M:%S.%f')
        date_local = datetime.strptime(date_local, '%Y-%m-%d %H:%M:%S.%f')
        if date_global < date_local:
            log_hash = log_hash_local
        else:
            log_hash = log_hash_global
    elif value is not None:
        log_hash, task_id, date = read_global_signal_value(value)
    elif form_value is not None:
        log_hash, date = read_global_signal_value(form_value)
    else:
        log_hash = None
    return log_hash

