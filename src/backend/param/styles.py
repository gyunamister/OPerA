from backend.param.colors import PRIMARY_DARK, PRIMARY, SECONDARY_LIGHT

GLOBAL_STYLE = {
    'width': '98%',
    'padding-left': '1%',
    'font-size': 'medium',
    'font-family': "Roboto, sans-serif"
}

DETECTOR_STYLE = {
    'font-size': 'larger',
    'font-weight': 'bold'
}

MODAL_HEADER_STYLE = {
    "font-size": "x-large",
    "font-weight": "bolder"
}

MODAL_BODY_STYLE = {
    "font-size": "medium",
    "text-align": "justify",
    "text-justify": "inter-word"
}

FONT_STYLE = {
    'font-size': 'medium',
    'font-family': "Roboto, sans-serif",
    'color': 'black'
}

LINK_CONTENT_STYLE = {
    "font-weight": "bolder",
    'color': PRIMARY,
    'align-items': 'center',
    'justify-content': 'center'
}

LINK_DARK_CONTENT_STYLE = {
    'color': 'white'
}

CENTER_BOX_STYLE = {
    'width': '100%',
    'height': '60px',
    'lineHeight': '60px',
    'borderWidth': '1px',
    'borderRadius': '5px',
    'textAlign': 'center',
    'margin': '10px'
}

CENTER_DASHED_BOX_STYLE = {'width': '50%',
                           'height': '60px',
                           'lineHeight': '60px',
                           'borderWidth': '1px',
                           'borderStyle': 'dashed',
                           'borderRadius': '5px',
                           'textAlign': 'center',
                           'margin-right': '5%',
                           'padding-right': "50px"}
CENTER_DASHED_BOX_STYLE.update(CENTER_BOX_STYLE)

HTML_TABLE_CELL_STYLE = {'float': 'left',
                         'margin-right': '20px'}

TABLE_COLOR_CELL_STYLE = {'margin-right': '4px'}

BUTTON_STYLE = {
    "font-family": "Roboto,sans-serif",
    "font-weight": "400",
    "color": "white",
    "text-align": "center",
    "transition": "all 0.2s",
    "background-color": PRIMARY
}

TAB_STYLE = {
    "font-family": "Roboto,sans-serif",
    "font-weight": "400",
    "color": PRIMARY,
    "text-align": "center",
    "transition": "all 0.2s"
}

BUTTON_LEFT_STYLE = {
    "font-family": "Roboto,sans-serif",
    "font-weight": "400",
    "color": "white",
    "text-align": "center",
    "transition": "all 0.2s",
    "background-color": PRIMARY,
    "margin-left": "10px"
}

TABLE_ROW_STYLE = {'width': '100%'}
NO_DISPLAY = {'display': 'none'}

BUTTON_TOOLTIP_STYLE = {
    "cursor": "pointer",
    "color": "white",
    "background-color": SECONDARY_LIGHT,
    "margin-left": "5px",
    "bottom": "5px"
}

BUTTON_TOOLTIP_HD_STYLE = {
    "cursor": "pointer",
    "color": "white",
    "background-color": SECONDARY_LIGHT,
    "margin-left": "5px",
    "bottom": "5px",
    'top': '-2px',
    'positioning': 'relative'
}


def act_style(color):
    return {
        "display": "inline-block",
        "background-color": color,
        "padding": "5px",
        "margin-right": "4px"}


toast_style = {"maxWidth": "10000px",
               'font-family': "Roboto, sans-serif",
               'font-size': 'medium'}
