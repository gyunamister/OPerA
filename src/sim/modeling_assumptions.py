from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd
import pyemd

from sim import time_utils
from sim.utils import auto_str, FrozenDict


def rejection_sample(sampler, accepter, recoverer, max_trials=10):
    trials = 0
    run = True
    sample = None
    while run and trials < max_trials:
        sample = sampler()
        if accepter(sample):
            run = False
        trials += 1
    if run:
        sample = recoverer(sample)  # clip after giving up
    return sample


def rejection_sample_within_range(sampler, lower_bound, upper_bound, max_trials=100):
    return rejection_sample(sampler, lambda s: lower_bound <= s <= upper_bound,
                            lambda s: max(lower_bound, min(upper_bound, s)), max_trials=max_trials)


@auto_str
@dataclass(unsafe_hash=True)
class Guess:
    def get(self, enable_time, complete_time, total_duration): ...


@auto_str
@dataclass(unsafe_hash=True)
class RelativeFractionalGuess(Guess):
    fraction: float


@auto_str
@dataclass(unsafe_hash=True)
class AbsoluteQuantileGuess(Guess):
    quantile: float


@auto_str
@dataclass(unsafe_hash=True)
class ActivityAssumptions:
    delay_guess: Guess
    processing_guess: Guess


@auto_str
@dataclass(unsafe_hash=True)
class ResourceAssumptions:
    pass


@auto_str
@dataclass(unsafe_hash=True)
class ModelingAssumptions:
    activity_assumptions: FrozenDict  # [str, ActivityAssumptions]
    resource_assumptions: FrozenDict  # [str, ResourceAssumptions]
    load_factor: float

    def __init__(self, activity_assumptions: Dict[str, ActivityAssumptions],
                 resource_assumptions: Dict[str, ResourceAssumptions], load_factor: float) -> None:
        self.activity_assumptions = FrozenDict(activity_assumptions)
        self.resource_assumptions = FrozenDict(resource_assumptions)
        self.load_factor = load_factor

    @staticmethod
    def default(activities, resources):
        return ModelingAssumptions(
            {a: ActivityAssumptions(RelativeFractionalGuess(
                0.0), AbsoluteQuantileGuess(0.2)) for a in activities},
            # TODO be any more arbitrary, will ya?
            {r: ResourceAssumptions() for r in resources}, 1.0)


def quantile_guess(series, q):
    return series['total'].quantile(q)


def fractional_guess(totals, r):
    return totals * r


def absolute_clipped_totals(activity_measurements, absolute_guess):
    normal = np.random.normal(
        loc=absolute_guess.total_seconds(), size=len(activity_measurements))
    presumed_start = activity_measurements['completed'] - \
        pd.to_timedelta(normal.clip(min=0), unit='seconds')
    clipped_totals = activity_measurements['completed'] - activity_measurements['enabled'].mask(
        activity_measurements.enabled > presumed_start, presumed_start)
    clipped_totals = clipped_totals.dt.total_seconds()
    sum__fillna = clipped_totals.groupby(
        activity_measurements['resource']).sum().fillna(0)
    return pd.to_timedelta(sum__fillna, unit='seconds')


def normalize_total_assignment_durations(original_totals, original_timespan, original_case_count, simulated_totals,
                                         simulated_timespan, simulated_cases, correction_factor=1.0):
    return original_totals / original_timespan / original_case_count, simulated_totals / simulated_timespan / simulated_cases


def binary_search(v):
    # TODO max quantile to check should be median (50%). Not valid for relative fractional
    return np.floor(v / 2), np.floor((.5 + v) / 2)


def linear_search(step=.1):
    def wrapped(v):
        return max(0, v - step), min(1, v + step)

    return wrapped


def equidistant_matrix(size):
    a = np.ones((size, size))
    np.fill_diagonal(a, 0)
    return a


def call_pyemd(s1, s2):
    # return pyemd.emd(s1.to_numpy(copy=True, dtype=np.float), s2.to_numpy(copy=True, dtype=np.float),
    #                  equidistant_matrix(len(s1)))
    return 0


class ModelingAssumptionsIterator:

    def __init__(self, original_measurements_df: pd.DataFrame,
                 initial_modeling_assumptions: ModelingAssumptions) -> None:
        self.original_measurements_df = original_measurements_df
        self.activities = set(
            initial_modeling_assumptions.activity_assumptions)
        self.resources = set(initial_modeling_assumptions.resource_assumptions)
        self.past_modeling_assumptions = {initial_modeling_assumptions}
        self.current_modeling_assumptions = initial_modeling_assumptions

        self.cache = {
            'original_span': max(original_measurements_df['completed']) - min(original_measurements_df['enabled']),
            'original_case_count': original_measurements_df['case_id'].nunique(),
            'original_assignment_totals': original_measurements_df.groupby(['activity', 'resource'])[
                'total'].sum().fillna(pd.Timedelta(0))}

    def get_imputer(self):
        activity_assumptions = self.current_modeling_assumptions.activity_assumptions

        limit = 10  # TODO arbitrarily restrict here or not?
        low = self.original_measurements_df[self.original_measurements_df['concurrent_by_activity'] <= limit - 1]
        filtered_measurements = self.original_measurements_df
        cached_delay_guesses = {
            a: quantile_guess(filtered_measurements[filtered_measurements.activity == a],
                              a_ass.delay_guess.quantile) for a, a_ass in activity_assumptions.items() if
            isinstance(a_ass.delay_guess, AbsoluteQuantileGuess)}
        cached_processing_guesses = {
            a: quantile_guess(filtered_measurements[filtered_measurements.activity == a],
                              a_ass.processing_guess.quantile) for a, a_ass in activity_assumptions.items()
            if isinstance(a_ass.processing_guess, AbsoluteQuantileGuess)}
        print('cached_processing_guesses', cached_processing_guesses)

        def guess(activity, enable_time, complete_time, total_duration):
            g = activity_assumptions[activity].delay_guess
            delay = pd.Timedelta(0)
            if isinstance(g, AbsoluteQuantileGuess):
                delay = min(cached_delay_guesses[activity], total_duration)
            elif isinstance(g, RelativeFractionalGuess):
                delay = fractional_guess(total_duration, g.fraction)
            schedule_time = time_utils.add(enable_time, delay)
            g = activity_assumptions[activity].processing_guess
            processing = pd.Timedelta(0)
            if isinstance(g, AbsoluteQuantileGuess):
                processing = pd.to_timedelta(
                    max(0, np.random.normal(
                        loc=cached_processing_guesses[activity].total_seconds())),
                    unit='seconds')
            elif isinstance(g, RelativeFractionalGuess):
                processing = fractional_guess(total_duration, g.fraction)
            start_time = max(time_utils.subtract(
                complete_time, processing), schedule_time)
            return schedule_time, start_time

        return guess

    def iterate_modeling_assumptions(self, simulated_measurements_df, score_dict, strat=linear_search(.1)):
        by_emd = sorted(filter(lambda t: not np.isnan(t[1]), score_dict['activity_sojourn'].items()),
                        key=lambda t: t[1], reverse=True)

        df1 = self.original_measurements_df
        df2 = simulated_measurements_df

        new_assumptions = None
        i = 0
        while i < len(by_emd) and (new_assumptions is None or new_assumptions not in self.past_modeling_assumptions):
            a = by_emd[i][0]
            m1 = df1.loc[df1.activity == a, 'total_seconds'].median()
            m2 = df2.loc[df2.activity == a, 'total_seconds'].median()
            std2 = df2.loc[df2.activity == a, 'total_seconds'].std()
            assumptions = self.current_modeling_assumptions.activity_assumptions[a]
            guess = assumptions.processing_guess
            if isinstance(guess, AbsoluteQuantileGuess):
                v = guess.quantile
            elif isinstance(guess, RelativeFractionalGuess):
                v = guess.fraction
            z = abs(m1 - m2) / std2
            if z > 1:
                f_name = 'binary'
                f = binary_search
            else:
                f_name = 'linear(.05)'
                f = linear_search(.05)
            l, h = f(v)
            new_v = l if m1 <= m2 else h
            new_guess = AbsoluteQuantileGuess(new_v) if isinstance(guess,
                                                                   AbsoluteQuantileGuess) else RelativeFractionalGuess(
                new_v)
            activity_assumptions = dict(
                self.current_modeling_assumptions.activity_assumptions)
            activity_assumptions[a] = ActivityAssumptions(
                activity_assumptions[a].delay_guess, new_guess)
            modeling_assumptions = ModelingAssumptions(activity_assumptions,
                                                       dict(
                                                           self.current_modeling_assumptions.resource_assumptions),
                                                       self.current_modeling_assumptions.load_factor)
            # could be optimized by checking actual derived(cached) guesses if quantile values are duplicates
            if modeling_assumptions not in self.past_modeling_assumptions:
                print(
                    f'*****Changing {a} {v:.3f} to {new_v:.3f} ({m1:.2f}<={m2:.2f}? {l:.3f} : {h:.3f}) with {f_name} (z={z:.3f})')
                new_assumptions = modeling_assumptions
            else:
                print(
                    f'*****Failed Changing {a} {v:.3f} to {new_v:.3f} ({m1:.2f}<={m2:.2f}? {l:.3f} : {h:.3f}) with {f_name} (z={z:.3f})')

            i += 1

        self.current_modeling_assumptions = new_assumptions
        self.past_modeling_assumptions.add(new_assumptions)
        return self.current_modeling_assumptions is not None

        # span_1 = self.cache['original_span']
        # cases_1 = self.cache['original_case_count']
        # assignment_totals_1 = self.cache['original_assignment_totals']
        #
        # span_2 = max(df2['completed']) - min(df2['enabled'])
        # cases_2 = df2['case_id'].nunique()
        # assignment_totals_2 = df2.groupby(['activity', 'resource'])['total_seconds'].sum().fillna(0)
        # assignment_totals_2 = pd.to_timedelta(assignment_totals_2, unit='seconds')
        #
        # do_normalize = True
        #
        # neighborhood = {}
        # for a, a_ass in self.current_modeling_assumptions.activity_assumptions.items():
        #     original_activity_measurements = df1[df1.activity == a]
        #     simulated_activity_measurements = df2[df2.activity == a]
        #     original_assignment_totals = assignment_totals_1.xs(a)
        #     simulated_assignment_totals = assignment_totals_2.xs(a)
        #     processing_guess = a_ass.processing_guess
        #     if isinstance(processing_guess, AbsoluteQuantileGuess):
        #         p = processing_guess.quantile
        #         l, h = strat(p)
        #         dist_if_lower = absolute_clipped_totals(simulated_activity_measurements,
        #                                                 quantile_guess(simulated_activity_measurements, l))
        #         dist_currently = absolute_clipped_totals(simulated_activity_measurements,
        #                                                  quantile_guess(simulated_activity_measurements, p))
        #         dist_if_higher = absolute_clipped_totals(simulated_activity_measurements,
        #                                                  quantile_guess(simulated_activity_measurements, h))
        #         dist_base = absolute_clipped_totals(original_activity_measurements,
        #                                             quantile_guess(original_activity_measurements, p))
        #     elif isinstance(processing_guess, RelativeFractionalGuess):
        #         r = processing_guess.fraction
        #         l, h = strat(r)
        #         dist_if_lower = fractional_guess(original_assignment_totals, l)
        #         dist_currently = fractional_guess(simulated_assignment_totals, r)
        #         dist_if_higher = fractional_guess(original_assignment_totals, h)
        #         dist_base = fractional_guess(original_assignment_totals, r)
        #     if do_normalize:
        #         args_currently = normalize_total_assignment_durations(dist_base, span_1, cases_1, dist_currently,
        #                                                               span_2,
        #                                                               cases_2)
        #         args_if_lower = normalize_total_assignment_durations(dist_base, span_1, cases_1, dist_if_lower, span_2,
        #                                                              cases_2)
        #         args_if_higher = normalize_total_assignment_durations(dist_base, span_1, cases_1, dist_if_higher,
        #                                                               span_2,
        #                                                               cases_2)
        #     else:
        #         args_currently = dist_base, dist_currently
        #         args_if_lower = dist_base, dist_if_lower
        #         args_if_higher = dist_base, dist_if_higher
        #     emd_if_lower = call_pyemd(*args_if_lower)
        #     emd_currently = call_pyemd(*args_currently)
        #     emd_if_higher = call_pyemd(*args_if_higher)
        #     neighborhood[a, l] = emd_currently - emd_if_lower
        #     neighborhood[a, h] = emd_currently - emd_if_higher
        #
        # sorted_neighborhood = [(a, v, d) for ((a, v), d) in
        #                        sorted(neighborhood.items(), key=lambda t: t[1], reverse=True)]
        # print(sorted_neighborhood)
        # print()
        # print(by_emd)
        # print('-' * 10)
        #
        # new_assumptions = None
        # i = 0
        # while i < len(sorted_neighborhood) and (
        #         new_assumptions is None or new_assumptions in self.past_modeling_assumptions):
        #     ac, val, improv = sorted_neighborhood[i]
        #     activity_assumptions = dict(self.current_modeling_assumptions.activity_assumptions)
        #     new_guess = AbsoluteQuantileGuess(val) if isinstance(activity_assumptions[ac].processing_guess,
        #                                                          AbsoluteQuantileGuess) else RelativeFractionalGuess(
        #         val)
        #
        #     activity_assumptions[ac] = ActivityAssumptions(activity_assumptions[ac].delay_guess, new_guess)
        #     new_assumptions = ModelingAssumptions(activity_assumptions,
        #                                           dict(self.current_modeling_assumptions.resource_assumptions),
        #                                           self.current_modeling_assumptions.load_factor)
        #     i += 1
        #
        # self.current_modeling_assumptions = new_assumptions
        #
        # return self.current_modeling_assumptions is not None
