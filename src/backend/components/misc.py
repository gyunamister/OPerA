import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from backend.components.navbar import navbar
from backend.param.constants import CB_TYPE_INSPECT, CB_TYPE_LOG, FORM_PREFIX, SIGNAL_PREFIX, CB_TYPE_INTERPRETATION
from backend.param.styles import BUTTON_STYLE, BUTTON_TOOLTIP_STYLE


def log_header(log_title):
    return [html.H2(log_title),
            html.Br()]


def typed_id_maker(typ, index):
    return {'type': typ, 'index': index}


def global_form_load_signal_id_maker(title):
    return FORM_PREFIX + title


def global_signal_id_maker(title):
    return SIGNAL_PREFIX + title


def global_url_signal_id_maker(title):
    return 'url-global-signal-' + title


def global_refresh_signal_id_maker(title):
    return f'refresh-global-signal-{title}'


def temp_jobs_store_id_maker(title):
    return 'temp-' + title + '-jobs-store'


def form_persistence_id_maker(title):
    return 'form-persistence-' + title


def markdown_text(introduction):
    return dbc.Row(dbc.Col(dcc.Markdown(introduction)))


def container(title, children, idx='home-title'):
    return dbc.Container(
        [navbar(),
         html.Br(),
         html.H1(title, id=idx),
         html.Hr(),
         html.Br()] + children, fluid=True)


def return_button_id(title):
    return title + "return-button"


def return_title_maker(title):
    return "Go Back"


def goto_button_id(title):
    return title + "goto-button"


def goto_title_maker(title):
    return "Go to " + title


def tooltip_button_id(target):
    return target + "tooltip-button"


def compute_button_id(title):
    return title + "compute-button"


def compute_title_maker(title):
    return title.title()


def collapse_id(title):
    return title + '-collapse'


def input_id(title):
    return title + '-input'


def collapse_button_id(title):
    return title + "collapse-button"


def collapse_title_maker(title):
    return "Show " + title


def checklist_id_maker(title):
    return title + '-checklist'


def modal_id(title):
    return title + "-modal"


def selected_node_id(title):
    return title + "-selected-node"


def modal_close_button_id(title):
    return title + '-close-modal'


def viz_id(title):
    return title + '-gv'


def tab_id(title):
    return title + '-tab'


def tooltip_button(target, style=BUTTON_TOOLTIP_STYLE):
    return dbc.Badge(
        "?",
        id=tooltip_button_id(target),
        className="mr-1",
        style=style
    )


def interpretation_trace_button(index, target, style=BUTTON_TOOLTIP_STYLE):
    return dbc.Badge(
        "?",
        id={"type": CB_TYPE_INTERPRETATION,
            "index": index,
            "target": target
            },
        className="mr-1",
        style=style
    )


def inspect_trace_button(index, style=BUTTON_STYLE, suffix='', version=True, result=''):
    if version:
        return dbc.Button(
            f"Inspect {suffix}",
            id={"type": CB_TYPE_INSPECT,
                "index": index},
            className="mb-3",
            style=style
        )
    else:
        return dbc.Button(
            f"Inspect {suffix}",
            id={"type": CB_TYPE_INSPECT,
                "index": index,
                "result": result},
            className="mb-3",
            style=style
        )


def use_log_button(index, style=BUTTON_STYLE):
    return [dbc.Button(
        "Use Log",
        id={"type": CB_TYPE_LOG,
            "index": index},
        className="mb-3",
        style=style
    )]


def button(title, title_maker, id_maker, style=BUTTON_STYLE, href=None):
    if href is not None:
        return dbc.Button(
            title_maker(title),
            id=id_maker(title),
            className="mb-3",
            style=style,
            href=href
        )
    else:
        return dbc.Button(
            title_maker(title),
            id=id_maker(title),
            className="mb-3",
            style=style
        )


def collapse(title, content):
    return html.Div(
        [
            button(title, collapse_title_maker, collapse_button_id),
            dbc.Collapse(
                content,
                id=title,
            ),
        ]
    )


def single_row(item, justify='start'):
    return dbc.Row(dbc.Col(item), justify=justify)


def card(children):
    return dbc.Card(dbc.CardBody(children))


def toast_id(title):
    return 'toast-' + title


def ps_context_tab_id(title):
    return 'typ-' + title


def ng_context_tab_id(title):
    return 'ng-' + title


def container_id(title):
    return 'container-' + title


def graph_id(title):
    return 'graph-' + title


def placeholder_id(title):
    return f'placeholder-{title}'


def result_details_toast_id(detector_title):
    return f'{detector_title}-details'


def show_button_id(title):
    return title + "show-button"


def show_title_maker(title):
    return title.title()
