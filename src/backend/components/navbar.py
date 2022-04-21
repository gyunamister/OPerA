import dash_bootstrap_components as dbc
from backend.param.constants import ABOUT_URL, CVIEW_URL, DVIEW_URL, DASHBOARD_URL, PATTERN_URL, PERF_ANALYSIS_URL, DESIGN_URL, OVIEW_URL

from backend.param.styles import LINK_DARK_CONTENT_STYLE
from backend.param.colors import PRIMARY_DARK


def navbar():
    return dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Home", href="/home",
                        style=LINK_DARK_CONTENT_STYLE)),
            dbc.NavItem(dbc.NavLink("Design", href=DESIGN_URL,
                        style=LINK_DARK_CONTENT_STYLE)),
            # dbc.NavItem(dbc.NavLink("Dashboard & Impact Analysis", href=DASHBOARD_URL,
            #             style=LINK_DARK_CONTENT_STYLE)),
            # dbc.NavItem(dbc.NavLink("Control-View", href=CVIEW_URL,
            #             style=LINK_DARK_CONTENT_STYLE)),
            # dbc.NavItem(dbc.NavLink("Diagnostics-View", href=DVIEW_URL,
            #             style=LINK_DARK_CONTENT_STYLE)),
            dbc.NavItem(dbc.NavLink("Performance-Analysis",
                        href=PERF_ANALYSIS_URL, style=LINK_DARK_CONTENT_STYLE)),
            # dbc.NavItem(dbc.NavLink("Action-Pattern", href=PATTERN_URL,
            #             style=LINK_DARK_CONTENT_STYLE)),
            # dbc.NavItem(dbc.NavLink("Operational-View", href=OVIEW_URL,
            #             style=LINK_DARK_CONTENT_STYLE)),
            # dbc.NavItem(dbc.NavLink("About", href=ABOUT_URL,
            #             style=LINK_DARK_CONTENT_STYLE))
        ],
        id="navbar",
        brand="OPerA",
        brand_href="/home",
        sticky="top",
        color=PRIMARY_DARK,
        dark=True,
        fluid=True,
        style={"width": "100%",
               "margin": "0",
               "padding": "0"}
    )
