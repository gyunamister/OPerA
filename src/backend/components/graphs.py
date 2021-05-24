import datetime
from math import floor

import plotly.graph_objs as go
import numpy as np
import dash
from backend.param.colors import SECONDARY_LIGHT, INTRINSIC_COLOR, PRIMARY, DETECTION_COLOR, \
    PRIMARY_VERY_LIGHT
from backend.param.constants import INTRINSIC_DEVIATION, EXTERNAL_DEVIATION, NEGATIVE_CONTEXT, DETECTION, FONTSIZE_VIZ, \
    UNKNOWN_CAUSE, EDGE_LBL_CAUSE, EDGE_LBL_DETECT, EDGE_LBL_CONTAIN, COLORSCALE, POSITIVE_CONTEXT, DP
from dtwin.available.available import AvailableGranularity
import graphviz as pgv
from dtwin.available.constants import HOURS_IN_DAY, SITUATION_AGG_KEY
from plotly.subplots import make_subplots

deviation_pos = 4
sum_nodes = 8


def make_pos_string(pos):
    return str(pos[0]) + "," + str(pos[1]) + "!"


def check_title_len(title):
    if len(title) > 20:
        words = title.split(" ")
        words = [word if index % 3 != 2 else word +
                 "\n" for index, word in enumerate(words)]
        return " ".join(words)
    else:
        return title


def generate_node_positions(classical, negative, positive, post_offset=None):
    if post_offset is None:
        max_n = max(len(positive) + len(negative),
                    len(classical) + len(negative))
        if len(negative) != 0:
            ys = [2 * i for i in range(max_n)]
            y_externals = [ys[i] for i in range(len(negative))]
            if len(y_externals) % 2 != 0:
                # Odd
                y_external = y_externals[floor(len(y_externals) / 2)]
            else:
                y_external = y_externals[int(len(y_externals) / 2)] - 1
            offset = len(negative)
        else:
            ys = [2 * i for i in range(max_n + 1)]
            y_externals = [ys[0]]
            y_external = ys[0]
            offset = 1
        max_intrinsic = max(len(positive), len(classical))
        y_intrinsics = [ys[i] for i in range(offset, offset + max_intrinsic)]
        if len(y_intrinsics) % 2 != 0:
            # Odd
            y_intrinsic = y_intrinsics[floor(len(y_intrinsics) / 2)]
        else:
            y_intrinsic = y_intrinsics[int(len(y_intrinsics) / 2)] - 1
        return y_external, y_externals, y_intrinsic, y_intrinsics
    else:
        max_n = max(len(positive) + len(negative),
                    len(classical) + len(negative), 2)
        if len(negative) != 0:
            ys = [2 * i for i in range(post_offset, post_offset + max_n)]
            y_externals = [ys[i] for i in range(len(negative))]
            if len(y_externals) % 2 != 0:
                # Odd
                y_external = y_externals[floor(len(y_externals) / 2)]
            else:
                y_external = y_externals[int(len(y_externals) / 2)] - 1
            offset = len(negative)
        else:
            ys = [
                2 * i for i in range(post_offset + 1, post_offset + max_n + 1)]
            y_externals = [ys[0]]
            y_external = ys[0]
            offset = 1
        max_intrinsic = max(len(positive), len(classical))
        y_intrinsics = [ys[i] for i in range(offset, offset + max_intrinsic)]
        if len(y_intrinsics) % 2 != 0:
            # Odd
            y_intrinsic = y_intrinsics[floor(len(y_intrinsics) / 2)]
        else:
            y_intrinsic = y_intrinsics[int(len(y_intrinsics) / 2)] - 1
        return y_external, y_externals, y_intrinsic, y_intrinsics


# https://gist.github.com/bendichter/d7dccacf55c7d95aec05c6e7bcf4e66e
# z = np.random.randint(2, size=(500,))
#
# display_years(z, (2019, 2020))
def display_year(z,
                 year: int = None,
                 month_lines: bool = True,
                 fig=None,
                 row: int = None,
                 color: bool = False):
    if year is None:
        year = datetime.datetime.now().year

    data = np.ones(365) * np.nan
    data[:len(z)] = z

    d1 = datetime.date(year, 1, 1)
    d2 = datetime.date(year, 12, 31)

    delta = d2 - d1

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May',
                   'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    month_positions = (np.cumsum(month_days) - 15) / 7

    dates_in_year = [d1 + datetime.timedelta(i) for i in
                     range(delta.days + 1)]  # gives me a list with datetimes for each day a year
    weekdays_in_year = [i.weekday() for i in
                        dates_in_year]  # gives [0,1,2,3,4,5,6,0,1,2,3,4,5,6,…] (ticktext in xaxis dict translates this to weekdays

    weeknumber_of_dates = [int(i.strftime("%V")) if not (int(i.strftime("%V")) == 1 and i.month == 12) else 53
                           for i in dates_in_year]  # gives [1,1,1,1,1,1,1,2,2,2,2,2,2,2,…] name is self-explanatory
    text = [str(round(data[i], 4) if i < data.shape[0] and data[i] is not np.nan else 'NA') + ' on ' + str(date)
            for i, date in enumerate(dates_in_year)]  # gives something like list of strings like ‘2018-01-25’ for each date. Used in data trace to make good hovertext.
    # 4cc417 green #347c17 dark green
    colorscale = COLORSCALE

    # handle end of year

    data = [
        go.Heatmap(
            x=weeknumber_of_dates,
            y=weekdays_in_year,
            z=data,
            text=text,
            hoverinfo='text',
            xgap=3,  # this
            ygap=3,  # and this is used to make the grid-like apperance
            showscale=True,
            colorscale='Greens' if not color else colorscale,
            colorbar=dict(title='Anomaly Level',
                          thickness=10),
            zmin=0,
            zmax=1
        )
    ]

    if month_lines:
        kwargs = dict(
            mode='lines',
            line=dict(
                color='#9e9e9e',
                width=1
            ),
            hoverinfo='skip'

        )
        for date, dow, wkn in zip(dates_in_year,
                                  weekdays_in_year,
                                  weeknumber_of_dates):
            if date.day == 1:
                data += [
                    go.Scatter(
                        x=[wkn - .5, wkn - .5],
                        y=[dow - .5, 6.5],
                        **kwargs
                    )
                ]
                if dow:
                    data += [
                        go.Scatter(
                            x=[wkn - .5, wkn + .5],
                            y=[dow - .5, dow - .5],
                            **kwargs
                        ),
                        go.Scatter(
                            x=[wkn + .5, wkn + .5],
                            y=[dow - .5, -.5],
                            **kwargs
                        )
                    ]

    layout = go.Layout(
        # title='activity chart',
        height=250,
        yaxis=dict(
            showline=False, showgrid=False, zeroline=False,
            tickmode='array',
            ticktext=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            tickvals=[0, 1, 2, 3, 4, 5, 6],
            autorange="reversed"
        ),
        xaxis=dict(
            showline=False, showgrid=False, zeroline=False,
            tickmode='array',
            ticktext=month_names,
            tickvals=month_positions
        ),
        font={'size': 10, 'color': '#9e9e9e'},
        plot_bgcolor=('#fff'),
        margin=dict(t=40),
        showlegend=False
    )

    if fig is None:
        fig = go.Figure(data=data, layout=layout)
    else:
        fig.add_traces(data, rows=[(row + 1)] *
                       len(data), cols=[1] * len(data))
        fig.update_layout(layout)
        fig.update_xaxes(layout['xaxis'])
        fig.update_yaxes(layout['yaxis'])

    return fig


def display_years(z, years, color=False):
    fig = make_subplots(rows=len(years), cols=1, subplot_titles=years)
    for i, year in enumerate(years):
        data = z[i * 365: (i + 1) * 365]
        display_year(data, year=year, fig=fig, row=i, color=color)
        fig.update_layout(height=250 * len(years))
    return fig
