from __future__ import annotations

import datetime
from collections import defaultdict
from typing import Dict, Set, Tuple
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import scipy.stats

import sim.parameter_implementations as pimpls
import sim.time_utils
from sim.replay_tracking import ProcessingModel, QueueModel, ResourcePool, DecisionTracker, ArrivalTracker, DelayModel
from sim.time_utils import Weekdays

if TYPE_CHECKING:
    import sim.model_parameters as params


def queueing_discipline(queue_model: QueueModel, log_df=None) -> params.QueueingDiscipline:
    df = queue_model.queueing_history_df
    df_interesting = df[df['queue_length'] > 1]
    if len(df_interesting) == 0:
        return pimpls.Fifo
    else:
        cont_deq = df_interesting['index'] / df_interesting['queue_length']
        deq_mean = cont_deq.mean()
        counts = cont_deq.groupby(pd.cut(cont_deq, np.linspace(0, 1, 10), right=False)).count()
        entropy = scipy.stats.entropy(counts.values)
        rel_entropy = entropy / np.log(10)
        if deq_mean <= .1 and rel_entropy <= .5:
            return pimpls.Fifo
        elif deq_mean >= .9 and rel_entropy <= .5:
            return pimpls.Lifo
        elif rel_entropy <= .5:
            return pimpls.FixedRelative(deq_mean)
        else:
            return pimpls.Random


def delay_sampler(delay_model: DelayModel):
    return pimpls.ExpSampler(delay_model.delay_df.delay.mean().total_seconds() / 60, unit='m')


def processing_time_sampler(processing_model: ProcessingModel, log_df=None) -> params.ProcessingTimeSampler:
    df = processing_model.processing_history_df
    # norms = {}
    # length = len(df)
    # for group in df.groupby('resource')['duration'].groups:
    #     params = scipy.stats.norm.fit(group.values)
    #     ratio = len(group) / length
    #     norm = scipy.stats.norm(*params)
    #     norms[group.name] = norm
    # TODO change back!
    mean = df.duration.mean()
    if pd.isna(mean):
        mean = pd.Timedelta(0)
    return pimpls.ExpSampler(mean.total_seconds() / 60,
                             unit='m')  # defaults.EmpiricalSampler(df['duration'], k=20)


def business_hours(df, time_column) -> params.BusinessHours:
    bh = {}
    length = len(df)
    alldayeveryday = True
    for dayofweek, g_indices in df.groupby(df[time_column].dt.dayofweek)[time_column].groups.items():
        group = df.loc[g_indices, time_column]
        group_length = len(group)
        if group_length / length > .1:  # only days with at least 10% of total assignment occurrences
            day = Weekdays(dayofweek)
            # two sided 90% interval of earliest/latest each day
            time_sort_values = group.dt.time.sort_values()
            if max(time_sort_values).hour - min(time_sort_values).hour < 23:
                alldayeveryday = False
            tup = tuple(time_sort_values.iloc[[int(0.05 * group_length), int(.95 * group_length)]])
            if tup[0] == tup[1]:  # tODO nonono
                bh[day] = sim.time_utils.add(sim.time_utils.set_time(datetime.datetime.today(), tup[0]),
                                             datetime.timedelta(seconds=-1)).time(), sim.time_utils.add(
                    sim.time_utils.set_time(datetime.datetime.today(), tup[0]),
                    datetime.timedelta(seconds=1)).time()  # TODO this hurts
            else:
                bh[day] = tup
    if alldayeveryday:
        return pimpls.AlwaysInBusiness
    else:
        return pimpls.WorkweekBusinessHours(bh)


def arrival_business_hours(arrival_tracker: ArrivalTracker, log_df=None) -> params.BusinessHours:
    return business_hours(arrival_tracker.arrival_history_df, 'time')


def arrival_span(arrival_tracker: ArrivalTracker, log_df=None) -> Tuple[datetime.datetime, datetime.datetime]:
    return arrival_tracker.arrival_history_df.time.min(), arrival_tracker.arrival_history_df.time.max()


def queue_business_hours(queue_model: QueueModel, log_df=None) -> params.BusinessHours:
    df = queue_model.queueing_history_df
    return business_hours(df, 'time')


def resource_business_hours(resource_pool: ResourcePool, log_df=None) -> Dict[str, params.BusinessHours]:
    df = resource_pool.resource_history_df
    result = {}
    for res, group_indices in df.groupby('resource').groups.items():
        result[res] = business_hours(df.loc[group_indices].reset_index(drop=True), 'assignment_time')
    return result


def resource_capacities(resource_pool: ResourcePool, log_df=None) -> Dict[str, int]:
    df = resource_pool.assignment_counts_df
    max_count = df.groupby('resource')['count'].max()
    return dict(max_count)


def resource_performances(resource_pool: ResourcePool, log_df=None) -> Dict[str, params.ResourcePerformance]:
    df = resource_pool.resource_history_df
    return {r: pimpls.PeakPerformance for r in resource_pool.observed_resources}


def activity_resource_mapping(resource_pool: ResourcePool, log_df=None) -> Dict[str, Set[str]]:
    df = resource_pool.resource_history_df
    propensities = df.groupby(['activity', 'resource']).size() / df.groupby('activity').size()
    activity_resource = defaultdict(set)
    for a, r in propensities.index:
        activity_resource[a].add(r)
    return activity_resource


def activity_resource_propensities(resource_pool: ResourcePool, log_df=None) -> Dict[str, Dict[str, float]]:
    df = resource_pool.resource_history_df
    propensities = df.groupby(['activity', 'resource']).size() / df.groupby('activity').size()
    activity_resource = dict()
    for a, r in propensities.index:
        if a not in activity_resource:
            activity_resource[a] = dict()
        activity_resource[a][r] = propensities.loc[(a, r)]
    return activity_resource


def inter_arrival_time_sampler(arrival_tracker: ArrivalTracker, log_df=None) -> params.InterArrivalSampler:
    iat = arrival_tracker.arrival_history_df  # sorted by timestamp index
    dailied = iat.groupby([iat.time.dt.year, iat.time.dt.dayofyear]).pipe(lambda g: g.time.diff()).reset_index(
        drop=True)
    # TODO dont always simply assume exponential
    mean = dailied.mean()
    iat_mean = iat.time.diff().mean()
    sampler = pimpls.ExpSampler(iat_mean.total_seconds() / 60, unit='m')
    return pimpls.EmpiricalSampler(iat.time.diff(), k=10, use_linear_combination=False)


def decision_classifier(decision_tracker: DecisionTracker, log_df=None) -> params.CaseClassifier:
    df = decision_tracker.decisions_df
    reindex = (df.groupby('decision').size() / len(df)).sort_index()
    return pimpls.StochasticClassifier(reindex)
