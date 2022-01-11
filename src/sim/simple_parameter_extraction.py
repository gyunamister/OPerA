from typing import Dict, Set

import numpy as np
import pandas as pd

import sim.parameter_implementations as pimpls
from sim.time_utils import Weekdays


def resource_assignment_freqs(df):
    return (df.groupby(['activity', 'resource']).size() / df.groupby('activity').size()).to_dict()


# a - r factor of mean total duration (resource skills)
def resource_skills(df):
    return (df.groupby(['activity', 'resource'])['total'].agg(pd.Series.mean) / df.groupby('activity')['total'].agg(
        pd.Series.mean)).to_dict()


# r - wise utilization assuming total duration
def resource_utilization(df):
    return (df.groupby('resource')['total'].sum() / (max(df['completed']) - min(df['enabled']))).to_dict()


def resource_capacity_quantiles(df, resources, k=3):
    return {r: (df.loc[df['resource'] == r, 'concurrent_by_resource'].quantile(q=np.linspace(0, 1, k)).astype(
        int) + 1).values for r
            in resources}


def resource_capacity_fraction(df, resources, k=3):
    return {r: [int(s) + 1 for s in np.linspace(0, df.loc[df['resource'] == r, 'concurrent_by_resource'].max(), k)] for
            r in
            resources}


def resource_capacity_log_fraction(df, resources, k=3):
    return {r: [int(s) for s in
                np.logspace(0, max(0, np.log2(df.loc[df['resource'] == r, 'concurrent_by_resource'].max()) + 1), num=k,
                            base=2)] for r in
            resources}


def activity_total_duration_quantiles(df, activities, k=3):
    return {a: df.loc[df['activity'] == a, 'total_seconds'].quantile(q=np.linspace(0, 1, k)).astype(int).values for a in
            activities}


def activity_total_duration_fraction(df, activities, k=3):
    return {a: [int(s) for s in np.linspace(0, df.loc[df['activity'] == a, 'total_seconds'].max(), k)] for a in
            activities}


def activity_total_duration_geom_fraction(df, activities, k=3):
    return {a: [int(s) for s in np.geomspace(1, max(1, df.loc[df['activity'] == a, 'total_seconds'].max()), k)] for a in
            activities}


def activity_total_duration_log_fraction(df, activities, k=3):
    return {a: [int(s) for s in
                np.logspace(0, np.log2(max(1, df.loc[df['activity'] == a, 'total_seconds'].max())), num=k, base=2)] for
            a in
            activities}


def restrict_to_low_concurrency(df, by='activity', limit=1):
    return df[df[f'concurrent_by_{by}'] <= limit - 1]


def queueing_discipline():
    return pimpls.Fifo


def queue_business_hours():
    return pimpls.AlwaysInBusiness


def processing_time_sampler(seconds):
    if seconds < 1:
        return pimpls.ZeroSampler
    else:
        return pimpls.ExpSampler(seconds / 60)


def arrival_sampler(inter_arrival_times):
    # sorted by timestamp index

    dailied = inter_arrival_times.groupby(
        [inter_arrival_times.time.dt.year, inter_arrival_times.time.dt.dayofyear]).pipe(
        lambda g: g.time.diff()).reset_index(
        drop=True)
    mean = dailied.dt.total_seconds().mean()
    return pimpls.ExpSampler(mean / 60)


def corr(df):
    return df[['concurrent_by_activity', 'total']].corr()


def resource_capacity(count):
    return int(count)


def resource_business_hours(df, r, bias_offset=pd.Timedelta(0)):
    bh = {}
    dfr = df[df['resource'] == r].reset_index(drop=True)
    length = len(dfr)
    alldayeveryday = True
    for dayofweek, indices in dfr.groupby(dfr['completed'].dt.dayofweek)['completed'].groups.items():
        group = dfr.loc[indices, 'completed'] - bias_offset
        group_length = len(group)
        if group_length / length > .1:  # only days with at least 10% of total assignment occurrences
            day = Weekdays(dayofweek)
            # two sided 90% interval of earliest/latest each day
            time_sort_values = group.dt.time.sort_values()
            if max(time_sort_values).hour - min(time_sort_values).hour < 23:
                alldayeveryday = False
            tup = tuple(time_sort_values.iloc[[int(0.05 * group_length), int(.95 * group_length)]])
            bh[day] = tup
    if alldayeveryday:
        return pimpls.AlwaysInBusiness
    else:
        return pimpls.WorkweekBusinessHours(bh)


def resource_performance(df, r):
    return pimpls.PeakPerformance


def activity_resource_mapping(df) -> Dict[str, Set[str]]:
    sizes = df.groupby(['activity', 'resource']).size()
    ar = dict()
    for (a, r) in sizes[sizes > 0].to_dict():
        if a not in ar:
            ar[a] = set()
        ar[a].add(r)
    return ar


def activity_resource_propensities(df) -> Dict[str, Dict[str, float]]:
    sizes = df.groupby(['activity', 'resource']).size() / df.groupby('activity').size()
    ar = dict()
    for (a, r), s in sizes[sizes > 0].to_dict().items():
        if a not in ar:
            ar[a] = dict()
        ar[a][r] = s
    return ar
