from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats
import seaborn as sns
from pm4py.evaluation.earth_mover_distance import evaluator
from pm4py.util import xes_constants
from pyemd import emd_samples


def loglang(log):
    variants = defaultdict(float)
    l = len(log)
    for trace in log:
        if len(trace) > 0:  # no empty variants allowed
            variant = []
            for event in trace:
                activity = event['concept:name']
                lifecycle = event['lifecycle:transition']
                variant.append(f'{activity}-{lifecycle}')
            variants[tuple(variant)] += 1.0 / l
    return variants


def loglang_emd(loglang_1, loglang_2):
    return evaluator.apply(loglang_1, loglang_2)


def exact_emd(samples_1, samples_2):
    return scipy.stats.wasserstein_distance(samples_1, samples_2)


def relativize(samples_1, samples_2):
    high, low = max(max(samples_1), max(samples_2)), min(
        min(samples_1), min(samples_2))
    span = high - low
    return (samples_1 - low) / span, (samples_2 - low) / span


def normalized_emd(samples_1, samples_2):
    rg = max(max(samples_1), max(samples_2)) - \
        min(min(samples_1), min(samples_2))

    def normalized_distance(values):
        l = len(values)
        ret = np.tile(values.reshape((-1, 1)), (1, l)) - \
            np.tile(values.reshape((1, -1)), (l, 1))
        return np.abs(ret) / rg

    # np.histogram(bins='auto') over both samples at once
    return emd_samples(samples_1, samples_2, extra_mass_penalty=rg, distance=normalized_distance)


def arrivals_emd(replay_result_1, replay_result_2):
    df_1 = replay_result_1.arrival_tracker.arrival_history_df
    time_1 = df_1['time']
    df_2 = replay_result_2.arrival_tracker.arrival_history_df
    time_2 = df_2['time']
    earliest, latest = min(min(time_1), min(
        time_2)), max(max(time_1), max(time_2))
    span = latest - earliest
    rel_time_1 = time_1 - earliest
    rel_time_2 = time_2 - earliest
    return exact_emd(rel_time_1 / span,
                     rel_time_2 / span)  # normalized_emd(rel_time_1.dt.total_seconds(), rel_time_2.dt.total_seconds())


def case_duration_emd(case_durations_1, case_durations_2):
    return exact_emd(*relativize(case_durations_1, case_durations_2))


def activity_sojourn_emd(df, log_1_key='original', log_2_key='simulated'):
    result = dict()
    activities = sorted(set(df['activity']))
    log_1_mask = df['log'] == log_1_key
    log_2_mask = df['log'] == log_2_key
    for a in activities:
        activity_mask = df['activity'] == a
        total_seconds_1 = df.loc[log_1_mask & activity_mask, 'total_seconds']
        total_seconds_2 = df.loc[log_2_mask & activity_mask, 'total_seconds']
        result[a] = exact_emd(*relativize(total_seconds_1, total_seconds_2))
    return result


def resource_completions_bh_emd(df, log_1_key='original', log_2_key='simulated'):
    result = dict()
    resources = sorted(set(df['resource']))
    log_1_mask = df['log'] == log_1_key
    log_2_mask = df['log'] == log_2_key
    for r in resources:
        resource_mask = df['resource'] == r
        df_1 = df[log_1_mask & resource_mask]
        df_2 = df[log_2_mask & resource_mask]

        counts_1 = df_1.groupby([df_1['completed'].dt.dayofweek, df_1['completed'].dt.hour]).size().reindex(
            pd.MultiIndex.from_product((range(7), range(24))), fill_value=0).reset_index(drop=True)
        counts_2 = df_2.groupby([df_2['completed'].dt.dayofweek, df_2['completed'].dt.hour]).size().reindex(
            pd.MultiIndex.from_product((range(7), range(24))), fill_value=0).reset_index(drop=True)

        result[r] = modulo_emd(counts_1, counts_2, 168)
    return result


def resource_concurrent_on_completion_emd(df, log_1_key='original', log_2_key='simulated'):
    result = dict()
    resources = sorted(set(df['resource']))
    log_1_mask = df['log'] == log_1_key
    log_2_mask = df['log'] == log_2_key
    for r in resources:
        resource_mask = df['resource'] == r
        df_1 = df.loc[log_1_mask & resource_mask, 'concurrent_by_resource']
        df_2 = df.loc[log_2_mask & resource_mask, 'concurrent_by_resource']
        result[r] = exact_emd(*relativize(df_1, df_2))
    return result


def activity_resource_assignments_emd(df, log_1_key='original', log_2_key='simulated'):
    ar_assignment_times = df.groupby(
        ['activity', 'resource', 'log']).size().unstack()
    ar_assignment_times /= ar_assignment_times.sum()
    return exact_emd(ar_assignment_times[log_1_key], ar_assignment_times[log_2_key])


def visual_loglang_emd(log_1, log_2):
    lang_1 = loglang(log_1)
    lang_2 = loglang(log_2)
    print('#lang1\t#lang2\tvariant')
    for var in set(lang_1.keys()).union(lang_2.keys()):
        print(
            f'{lang_1.get(var, 0.0) * 100:.2f}%\t{lang_2.get(var, 0.0) * 100:.2f}%\t{var}')
    result = loglang_emd(lang_1, lang_2)
    print('loglang emd:', result)
    return result


def visual_case_duration_emd(log_1, log_2, save_prefix=None):
    cd1 = case_durations(log_1)
    cd2 = case_durations(log_2)

    plt.boxplot([cd1, cd2], labels=['original log', 'simulated log'])
    plt.title('Boxplots of OCCase Durations')
    plt.ylabel('seconds')
    if save_prefix:
        plt.savefig(save_prefix + '_scores/' + save_prefix +
                    '_casedurations_viz', dpi=300, bbox_inches="tight")
    plt.show()
    print('original log')
    print(cd1.describe())
    print('simulated log')
    print(cd2.describe())
    print('case_duration_emd:', exact_emd(*relativize(cd1, cd2)))


def visual_sojourn_durations(replay_result_1, replay_result_2, by='activity'):
    m1 = replay_result_1.trace_tracker.measurements_df
    m2 = replay_result_2.trace_tracker.measurements_df
    df = pd.concat([m1.assign(log='original'), m2.assign(log='simulated')])
    sns.catplot(data=df, y=by, x='total_seconds', orient='h',
                dodge=True, hue='log', kind='violin', palette='Set2')
    plt.title('Total Activity Durations')
    plt.show()

    sns.displot(data=df, row=by, x='total_seconds', hue='log', palette='Set2', rug=True, kind='ecdf', stat='proportion',
                facet_kws=dict(sharex=False))
    plt.show()

    activities = sorted(set(df[by]))

    for a in activities:
        df_a = df.loc[df[by] == a]
        # sns.displot(x=df_a['total_seconds'], hue=df_a['log'], rug=True, palette='Set2')
        # plt.title(f'Histogram of total sojourn durations for {by} {a}')
        # plt.show()

        total_waits1 = df_a.loc[df_a['log'] == 'original', 'total_seconds']
        total_waits2 = df_a.loc[df_a['log'] == 'simulated', 'total_seconds']
        print(f'sojourn durations emd of {by} {a}:', exact_emd(
            *relativize(total_waits1, total_waits2)))


def visual_concurrent_on_completion(replay_result_1, replay_result_2, by='resource'):
    m1 = replay_result_1.trace_tracker.measurements_df
    m2 = replay_result_2.trace_tracker.measurements_df
    df = pd.concat([m1.assign(log='original'), m2.assign(log='simulated')])
    sns.catplot(data=df, y=by, x=f'concurrent_by_{by}', orient='h', dodge=True, hue='log', kind='violin',
                palette='Set2')
    plt.title('Concurrent Assignments Count')
    plt.show()

    sns.displot(data=df, x=f'concurrent_by_{by}', row=by, hue='log', palette='Set2', rug=True, kind='ecdf',
                stat='proportion', facet_kws=dict(sharex=False))
    plt.show()

    resources = sorted(set(m1['resource']).intersection(set(m2['resource'])))
    for r in resources:
        df_1 = m1.loc[m1[by] == r, f'concurrent_by_{by}']
        df_2 = m2.loc[m2[by] == r, f'concurrent_by_{by}']
        print(f'concurrent on completion emd by {by} {r}:', exact_emd(
            *relativize(df_1, df_2)))


def visual_arrivals(replay_result_1, replay_result_2, save_prefix=None):
    df1 = replay_result_1.arrival_tracker.arrival_history_df
    time1 = df1['time']
    sns.lineplot(x=time1, y=range(len(df1)), label='original log')
    df2 = replay_result_2.arrival_tracker.arrival_history_df
    time2 = df2['time']
    sns.lineplot(x=time2, y=range(len(df2)), label='simulated log')
    plt.legend()
    plt.gcf().autofmt_xdate()
    plt.title('Arrival Process')
    plt.ylabel('cumulative case count')
    if save_prefix:
        plt.savefig(save_prefix + '_scores/' + save_prefix +
                    '_arrivals_viz', dpi=300, bbox_inches="tight")
    plt.show()
    earliest, latest = min(min(time1), min(time2)), max(max(time1), max(time2))
    span = latest - earliest
    rel_time1 = time1 - earliest
    rel_time2 = time2 - earliest
    print('arrivals emd:', exact_emd(rel_time1 / span, rel_time2 / span))


def visual_completions_bh(replay_result_1, replay_result_2, by='activity', save_prefix=None):
    m1 = replay_result_1.trace_tracker.measurements_df
    m2 = replay_result_2.trace_tracker.measurements_df
    df = pd.concat([m1.assign(log='original'), m2.assign(log='simulated')])

    activities = sorted(set(df[by]))

    for a in activities:
        df_a = df.loc[df[by] == a]
        df_a_1 = df_a.loc[df_a['log'] == 'original']
        df_a_2 = df_a.loc[df_a['log'] == 'simulated']

        counts_1 = df_a_1.groupby([df_a_1['completed'].dt.dayofweek, df_a_1['completed'].dt.hour]).size().reindex(
            pd.MultiIndex.from_product((range(7), range(24))), fill_value=0).reset_index(drop=True)
        counts_2 = df_a_2.groupby([df_a_2['completed'].dt.dayofweek, df_a_2['completed'].dt.hour]).size().reindex(
            pd.MultiIndex.from_product((range(7), range(24))), fill_value=0).reset_index(drop=True)

        plt.bar(range(168), counts_1 / counts_1.sum(), label='original log')
        plt.bar(range(168), counts_2 / counts_2.sum(), label='simulated log')
        plt.title(
            f'Histogram of Business Hours Over hours-of-week of {str.capitalize(by)} {a}')
        plt.legend()
        plt.ylabel('score')
        plt.xlabel('hour-of-week')
        if save_prefix:
            plt.savefig(save_prefix + '_scores/' + save_prefix +
                        f'_bh_{a}_viz', dpi=300, bbox_inches="tight")
        plt.show()
        print(f'normalized modulo emd for {a}:',
              modulo_emd(counts_1, counts_2, 168))


def modulo_emd(samples_1, samples_2, n):
    max_dist = n // 2
    return emd_samples(samples_1, samples_2, extra_mass_penalty=max_dist, distance=modulo_distance(n, normalize=True))


def modulo_distance(n, normalize=True):
    def fu(values):
        l = len(values)
        lmr = np.tile(values.reshape((-1, 1)), (1, l)) - \
            np.tile(values.reshape((1, -1)), (l, 1))
        mod = [np.mod(lmr, n), np.mod(-lmr, n)]
        result = np.min(mod, axis=0)
        r = (result / (n // 2)) if normalize else result
        return r

    return fu


def case_durations(log):
    durations = []
    for trace in log:
        if len(trace) > 0:
            earliest = trace[0][xes_constants.DEFAULT_TIMESTAMP_KEY]
            latest = trace[len(trace) - 1][xes_constants.DEFAULT_TIMESTAMP_KEY]
            durations.append(latest - earliest)
    return pd.Series(durations)
