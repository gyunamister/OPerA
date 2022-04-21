import plotly.express as px


def draw_gannt_chart(timeline_data, sim_count):
    # df = [
    #     dict(Task="Simulation", Start=1, Finish=10, IndexCol='TS'),
    #     dict(Task="Action 1", Start=2, Finish=8, IndexCol='TA1'),
    #     dict(Task="Action 1", Start=10, Finish=12, IndexCol='TA1'),
    # ]

    # df = [
    #     dict(Task='Task A', Description='Task A - 1', Start='2008-10-05',
    #          Finish='2009-04-15', IndexCol='TA'),
    #     dict(Task="Task B", Description='Task B - 1', Start='2008-12-06',
    #          Finish='2009-03-15', IndexCol='TB'),
    #     dict(Task="Task C", Description='Task C - 1', Start='2008-09-07',
    #          Finish='2009-03-15', IndexCol='TC'),
    #     dict(Task="Task C", Description='Task C - 2', Start='2009-05-08',
    #          Finish='2009-04-15', IndexCol='TC'),
    #     dict(Task="Task A", Description='Task A - 2', Start='2009-04-20',
    #          Finish='2009-05-30', IndexCol='TA')
    # ]
    # fig = FigureFactory.create_gantt(df, colors=dict(TA='rgb(220, 0, 0)', TB='rgb(170, 14, 200)', TC=(
    #     1, 0.9, 0.16)), show_colorbar=True, index_col='IndexCol', group_tasks=True)
    print(f'We are currently at {sim_count}')
    # fig = ff.create_gantt(timeline_data, colors='Viridis',
    #                       show_colorbar=True, index_col='IndexCol', group_tasks=True, title=None)
    fig = px.timeline(timeline_data, color='Task',
                      x_start="Start", x_end="Finish", y="Task", text="InstanceName")
    # fig.layout.xaxis.type = 'linear'
    # for d in fig.data:
    #     filt = df['color'] == d.name
    #     d.x = df[filt]['Delta'].tolist()
    # fig.data[0].x = [t['Delta'] for t in timeline_data]
    # print(fig.data[0])
    # fig['layout']['annotations'] = timeline_anno_data
    # for k in range(len(fig['data'])):
    #     fig['data'][k].update(text=timeline_data[k]
    #                           ['Task'], hoverinfo="text+x+y")
    fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    })
    fig.update_layout(yaxis={'visible': False, 'showticklabels': False})
    # fig.data[0].x = [9, 6, 2]
    return fig
