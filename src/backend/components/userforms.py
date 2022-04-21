import datetime
from pandas.core.frame import DataFrame

import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from backend.components.misc import typed_id_maker, checklist_id_maker, collapse, collapse_id, input_id, tooltip_button
from backend.components.navbar import navbar
from backend.param.available import extract_title
from backend.param.constants import JOBS_KEY, JOB_ID_KEY, JOB_DATA_NAME_KEY, JOB_DATA_DATE_KEY, SEP, CSV_ATTRIBUTES_FST, \
    NA, CSV_ATTRIBUTES_SND, MEMORY_PERSISTENCE, OBJECTS, VALUES, CB_TYPE_DETECT, FORMTEXT_KEY, PLACEHOLDER_KEY, \
    ATTRIBUTE_CSV_TEXT, ATTRIBUTE_OCEL_TEXT
from dtween.available.available import extract_options, AvailableNormRanges
from dash.dependencies import Input, Output, State
from backend.param.colors import PRIMARY, PRIMARY_LIGHT
from backend.param.styles import BUTTON_STYLE, NO_DISPLAY, DETECTOR_STYLE, BUTTON_TOOLTIP_STYLE, BUTTON_TOOLTIP_HD_STYLE
import dash_daq as daq


def generate_deviation_form(detector, detector_helps):
    return html.Div(
        [
            html.H2(
                [
                    extract_title(detector),
                ] +
                [
                    tooltip_button(extract_title(detector),
                                   style=BUTTON_TOOLTIP_HD_STYLE)
                    if detector_helps[detector] else html.Div('')
                ]),
            dbc.Row(
                dbc.Col(
                    daq.BooleanSwitch(
                        id=checklist_id_maker(extract_title(detector)),
                        on=False,
                        style={'positioning': 'relative',
                               'left': '-10'},
                        color=PRIMARY_LIGHT,
                        persistence=True,
                        persistence_type='memory'),
                    align='start',
                    width=1),
                justify='start')
        ]
    )


def single_available_checklist(idx, title):
    return html.Div(dbc.Checklist(
        id=checklist_id_maker(extract_title(idx) + '-' + title),
        options=[{'label': '',
                  'value': 1}],
        value=[],
        style={'margin-left': '30px'},
        persistence=True,
        persistence_type='memory'
    ))


def generate_context_form_row(context, titles, context_helps):
    return [
        dbc.Row(
            [

                dbc.Col(
                    [
                        html.Div(
                            [
                                extract_title(context),
                            ] +
                            [
                                tooltip_button(extract_title(context),
                                               style={**BUTTON_TOOLTIP_STYLE,
                                                      **{'top': '-2px',
                                                         'positioning': 'relative'}})
                                if context_helps[context] else html.Div('')
                            ],
                            style={'font-weight': 'bold'}),

                    ]
                ),
                dbc.Col(
                    [
                        single_available_checklist(context, titles[0])
                    ]
                ),

                dbc.Col(
                    [
                        single_available_checklist(context, titles[1])
                    ]
                ),

                dbc.Col(
                    [
                        single_available_checklist(context, titles[2])
                    ]
                )
            ]
        )
    ]


def generate_deviation_param_form(detector):
    input_display = detector.value[extract_title(detector)].input_display
    if input_display is not None:
        return dbc.Collapse(
            dbc.Row([
                dbc.Col(
                    html.Div(
                        [
                            dbc.Label(param),
                            dbc.Input(placeholder=description[PLACEHOLDER_KEY],
                                      type="text",
                                      id=input_id(extract_title(
                                          detector) + SEP + param),
                                      persistence=True,
                                      persistence_type='memory'
                                      ),
                            dbc.FormText(description[FORMTEXT_KEY])
                        ]
                    ))
                for param, description in input_display.items()
            ]
            ), id=collapse_id(extract_title(detector)),
            is_open=False)
    else:
        return ''


def make_options(input_list):
    return [{'label': item, 'value': item} for item in input_list]


def make_job_option(jobs, log_hash):
    return [{'label': 'Job ID ' + str(jobs[JOBS_KEY][log_hash][JOB_ID_KEY]) + ':   ' +
                      jobs[JOBS_KEY][log_hash][JOB_DATA_NAME_KEY] + '  ' +
                      str(jobs[JOBS_KEY][log_hash][JOB_DATA_DATE_KEY]),
             'value': log_hash}]


def radio_items_label_unequal_value(labels, values, idx, value, persistence):
    return dbc.RadioItems(
        options=[
            {'label': label, 'value': value}
            for label, value in zip(labels, values)
        ],
        value=value,
        id=radio_item_id_maker(idx),
        persistence=persistence,
        persistence_type=MEMORY_PERSISTENCE
    )


def radio_items(options, idx, value, persistence, set_value=True, style={}):
    if set_value:
        return dbc.RadioItems(
            options=[
                {'label': option, 'value': option}
                for option in options
            ],
            value=value,
            id=radio_item_id_maker(idx),
            persistence=persistence,
            persistence_type=MEMORY_PERSISTENCE,
            style=style
        )
    else:
        return dbc.RadioItems(
            options=[
                {'label': option, 'value': option}
                for option in options
            ],
            id=radio_item_id_maker(idx),
            persistence=persistence,
            persistence_type=MEMORY_PERSISTENCE,
            style=style
        )


def empty_radio_item(idx, persistence):
    return dbc.RadioItems(
        options=[],
        id=radio_item_id_maker(idx),
        persistence=persistence,
        persistence_type=MEMORY_PERSISTENCE
    )


def dropdown(attributes, idx, multi=True, persistence=True, set_value=True, persisted=None):
    if set_value:
        return dcc.Dropdown(
            id=dropdown_id_maker(idx),
            options=[{"label": attribute, "value": attribute}
                     for attribute in attributes],
            value=persisted if persisted is not None else attributes[0],
            multi=multi,
            persistence=persistence,
            persistence_type=MEMORY_PERSISTENCE
        )
    else:
        return dcc.Dropdown(
            id=dropdown_id_maker(idx),
            options=[{"label": attribute, "value": attribute}
                     for attribute in attributes],
            multi=multi,
            persistence=persistence,
            persistence_type=MEMORY_PERSISTENCE
        )


def hidden_radio_item_id_maker(job_id, attribute):
    return 'radio-' + str(job_id) + attribute


def radio_item_id_maker(attribute):
    return 'radio-' + attribute


def dropdown_id_maker(attribute):
    return 'dropdown-' + attribute


def form_dropdown_row(data_attributes, attributes, multis, idx, persistence=False, set_value=True, persisted=None,
                      list=None, style=None):
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.Div(
                        [
                            dbc.Label(attribute),
                            dropdown(data_attributes,
                                     idx + attribute,
                                     multi,
                                     persistence,
                                     set_value,
                                     None if persisted is None else persisted[attribute] if attribute not in list else
                                     persisted[attribute].split(SEP))
                        ]
                    )
                ]
            )
            for attribute, multi in zip(attributes, multis)
        ],
        style=style if style is not None else {}
    )


def create_attribute_forms(jobs, dfs, form=None):
    return [
        html.Div(
            [
                radio_items([log_hash], log_hash, log_hash,
                            persistence=True, style=NO_DISPLAY),
                html.Br(id=log_hash + '-br'),
                html.P(
                    ATTRIBUTE_CSV_TEXT
                    if isinstance(df, DataFrame) else ATTRIBUTE_OCEL_TEXT,
                    id=log_hash + '-p'),
                form_dropdown_row(df.columns if isinstance(df, DataFrame) else [NA] + df.meta.attr_events,
                                  CSV_ATTRIBUTES_FST,
                                  [False, False, True, True],
                                  log_hash,
                                  True,
                                  persisted=form[log_hash] if log_hash in form else None,
                                  list=[OBJECTS.title(), VALUES.title()],
                                  style={} if isinstance(df, DataFrame) else NO_DISPLAY),
                form_dropdown_row(
                    [NA] + [col for col in df.columns] if isinstance(
                        df, DataFrame) else [NA] + df.meta.attr_events,
                    CSV_ATTRIBUTES_SND,
                    [False, False],
                    log_hash,
                    True,
                    persisted=form[log_hash] if form is not None and log_hash in form and OBJECTS.title(
                    ) in form[log_hash] else None,
                    list=[])
            ], id=attribute_form_id(log_hash))
        for log_hash, df in zip(jobs[JOBS_KEY], dfs) if df is not None
    ]


def attribute_form_id(log_hash):
    return log_hash + '-attribute-selection-form'
