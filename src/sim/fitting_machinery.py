import datetime
import itertools
import json
from dataclasses import dataclass
from typing import Set, List, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pm4py
import seaborn as sns

import sim.model_configuration
from sim import log_similarity
from sim import petrinet_replay, time_utils
from sim import simple_parameter_extraction as spe
from sim.enums import AvailableLifecycles, ExecutionParameters
from sim.exporting import save_log
from sim.model_configuration import create_model_configuration, create_simplified_model_configuration, \
    ModelConfiguration
from sim.modeling_assumptions import ModelingAssumptions, ModelingAssumptionsIterator
from sim.simulation import simulate, create_simulation_model, default_execution_parameters
from sim.time_utils import filenameable_timestamp
from sim.utils import auto_str, FrozenDict


def score_log(original_log, test_log, original_replay_result, test_replay_result, evaluation_cache):
    if 'loglang' not in evaluation_cache:
        evaluation_cache['loglang'] = log_similarity.loglang(original_log)
    if 'casedurations' not in evaluation_cache:
        evaluation_cache['casedurations'] = log_similarity.case_durations(original_log)

    s1 = log_similarity.loglang_emd(evaluation_cache['loglang'], log_similarity.loglang(test_log))
    s2 = log_similarity.case_duration_emd(evaluation_cache['casedurations'], log_similarity.case_durations(test_log))
    s3 = log_similarity.arrivals_emd(original_replay_result, test_replay_result)

    original_df = original_replay_result.trace_tracker.measurements_df
    test_df = test_replay_result.trace_tracker.measurements_df
    dtype = pd.CategoricalDtype(categories=['original', 'simulated'])
    df = pd.concat([original_df.assign(log='original'), test_df.assign(log='simulated')])
    df.log = df.log.astype(dtype, copy=False)

    s4_dict = log_similarity.resource_completions_bh_emd(df)
    s5_dict = log_similarity.activity_sojourn_emd(df)
    s6_dict = log_similarity.resource_concurrent_on_completion_emd(df)
    s7 = log_similarity.activity_resource_assignments_emd(df)

    s4 = np.nanmean(list(s4_dict.values()))
    s5 = np.nanmean(list(s5_dict.values()))
    s6 = np.nanmean(list(s6_dict.values()))

    # TODO possibly weigh these
    s_ = [s1, s2, s3, s4, s5, s6, s7]
    s = np.nanmean(s_)
    return s, {'log language': s1, 'case durations': s2, 'arrival': s3, 'business hours': s4_dict,
               'total durations': s5_dict,
               'concurrent assignments': s6_dict, 'activity resource assignments': s7}


def save_scorelist_plot(scorelist, prefix=''):
    plt.plot(scorelist)
    plt.title('Score Progression While Fitting')
    plt.ylabel('score')
    plt.xlabel('iteration')
    plt.gcf().gca().xaxis.get_major_locator().set_params(integer=True)
    plt.savefig(prefix + '_scores/' + prefix + '_scorelist', dpi=300, bbox_inches="tight")


def save_subscorelists_plots(subscorelists, prefix=''):
    for k, vs in subscorelists.items():
        if isinstance(vs, dict):
            for kk, vss in vs.items():
                plt.plot(vss, label=kk)
            plt.legend()
        else:
            plt.plot(vs)
        plt.title(r'$score_{\mathrm{' + str.replace(k, ' ', r'\ ') + '}}$')
        plt.gcf().gca().xaxis.get_major_locator().set_params(integer=True)
        plt.ylabel('score')
        plt.xlabel('iteration')
        plt.savefig(prefix + '_scores/' + prefix + '_' + str.replace(k, ' ', ''), dpi=300, bbox_inches="tight")
        plt.show()


def permute_modeling_assumptions(modeling_assumptions: ModelingAssumptions,
                                 past_modeling_assumptions: Set[ModelingAssumptions]):
    return modeling_assumptions


def permute_model_config(model_config: ModelConfiguration, past_model_configs: List[ModelConfiguration]):
    return model_config


def change_resource_capacity(model_config, resource, change=1):
    new_resources = {r: (sim.model_configuration.ResourceConfig(rc.capacity + change, rc.business_hours,
                                                                rc.performance) if resource == r else rc) for r, rc in
                     model_config.resources.items()}
    return ModelConfiguration(model_config.arrivals, model_config.activities, new_resources, model_config.decisions,
                              model_config.mapping)


def fit_to_log(log, petrinet_model, sim_graph, replay_result, max_iterations=20,
               time_limit=datetime.timedelta(minutes=1)):
    trace_tracker = replay_result.trace_tracker
    df = trace_tracker.measurements_df

    activities = sorted(set(df['activity']))
    resources = sorted(set(df['resource']))

    mai = ModelingAssumptionsIterator(df, ModelingAssumptions.default(activities, resources))

    evaluation_cache = {}
    scores = []
    score_dicts = []
    intermediate_results = []

    past_model_configs = []

    t_pre_fitting = time_utils.now()
    max_end_time = time_utils.add(t_pre_fitting, time_limit)
    iteration = 0
    while iteration < max_iterations and time_utils.now() <= max_end_time:
        modeling_assumptions = mai.current_modeling_assumptions

        print(f'Selecting modeling assumptions {modeling_assumptions}')

        t_start = time_utils.now()
        activity_trackers, resource_pool = trace_tracker.re_replay(mai.get_imputer())
        t_post_re_replay = time_utils.now()
        model_config = create_model_configuration(activity_trackers, replay_result.decision_trackers,
                                                  replay_result.arrival_tracker,
                                                  resource_pool)
        t_post_model_config = time_utils.now()
        print(model_config)

        simulation_model = create_simulation_model(sim_graph, model_config, default_execution_parameters())

        print(f'Simulating hyper-iteration={iteration}')

        t_pre_sim = time_utils.now()

        simulated_log = simulate(simulation_model,
                                 simulation_log_filename=f'iterative1_{iteration}_{filenameable_timestamp()}.log') \
            .get_log(allowed_lifecycles=trace_tracker.available_lifecycle_map)

        t_post_sim = time_utils.now()

        simulated_replay_result = petrinet_replay.replay_log(simulated_log, petrinet_model)

        t_post_replay = time_utils.now()

        score, score_dict = score_log(log, simulated_log, replay_result, simulated_replay_result, evaluation_cache)

        t_post_scoring = time_utils.now()

        print(f'Overall score:\t{score}\nDetailed scores:\t{score_dict}')
        print(
            f'Timings:\nRe-Replay\t{t_post_re_replay - t_start}\nModel Config\t{t_post_model_config - t_post_re_replay}\nSimulation:\t{t_post_sim - t_pre_sim}\nReplay simlog:\t{t_post_replay - t_post_sim}\nScoring:\t{t_post_scoring - t_post_replay}')

        scores.append(score)
        score_dicts.append(score_dict)
        intermediate_results.append((modeling_assumptions, model_config, simulated_log))

        past_model_configs.append(model_config)

        iteration += 1
        if not mai.iterate_modeling_assumptions(simulated_replay_result.trace_tracker.measurements_df, score_dict):
            print('All possible modeling assumptions have already been tried.')
            break

    order = np.argsort(scores)

    t_post_fitting = time_utils.now()

    fitting_duration = t_post_fitting - t_pre_fitting
    print(
        f'Iterating {iteration} times finished in {fitting_duration} ({datetime.timedelta(seconds=fitting_duration.total_seconds() // len(scores))}/it)')

    print('Top 2 models:')
    for k, i in enumerate(order[:2]):
        (modeling_assumptions, model_config, simulated_log) = intermediate_results[i]
        score, score_dict = scores[i], score_dicts[i]
        print(f'#{k} iteration={i} score={score}:')
        print(f'Detailed: {score_dict}')
        print(modeling_assumptions)
        print(model_config)
        # log_similarity.visual_loglang_emd(log, simulated_log)
        # log_similarity.visual_arrivals(replay_result, simulated_replay_result)
        # log_similarity.visual_case_duration_emd(log, simulated_log)
        # log_similarity.visual_sojourn_durations(replay_result, simulated_replay_result)
        # log_similarity.visual_concurrent_on_completion(replay_result, simulated_replay_result)
        # log_similarity.visual_completions_bh(replay_result, simulated_replay_result)
        print('#########')

    min_idx = order[0]
    return intermediate_results[min_idx], scores[min_idx], scores, trans_scores(scores, score_dicts)


@auto_str
@dataclass(unsafe_hash=True)
class HyperParameters:
    activity_hyper: FrozenDict
    resource_hyper: FrozenDict

    def __init__(self, activity_hyper: Dict[str, int], resource_hyper: Dict[str, int]) -> None:
        super().__init__()
        self.activity_hyper = FrozenDict(activity_hyper)
        self.resource_hyper = FrozenDict(resource_hyper)


def make_unique(d):
    result = dict()
    for k, v in d.items():
        result[k] = np.unique(v)
    return result


def select_next_hyper_parameters(replay_result, replay_result_simulation, hyper_parameters, model_config, score_dict,
                                 quantile_dicts, past_hyper_parameters):
    activity_total_duration_quantile_dict, resource_concurrent_quantile_dict = quantile_dicts
    sorted_scores = sorted(
        itertools.chain(score_dict['total durations'].items(), score_dict['concurrent assignments'].items()),
        key=lambda t: t[1], reverse=True)

    df = replay_result.trace_tracker.measurements_df
    df_simulation = replay_result_simulation.trace_tracker.measurements_df

    new_activity_hyper, new_resource_hyper = dict(hyper_parameters.activity_hyper), dict(
        hyper_parameters.resource_hyper)

    new_hyper = None
    for tup in sorted_scores:
        key = tup[0]
        if key in activity_total_duration_quantile_dict:
            typ, metric = 'activity', 'total_seconds'
            targets = list(model_config.mapping.assignable_resources[key])
            other_typ, other_metric = 'resource', 'concurrent_by_resource'
            other_hyper = new_resource_hyper
            quant_dic = activity_total_duration_quantile_dict
            other_dic = resource_concurrent_quantile_dict
            relevant_hyper = new_activity_hyper
        elif key in resource_concurrent_quantile_dict:
            typ, metric = 'resource', 'concurrent_by_resource'
            targets = [a for (a, s) in model_config.mapping.assignable_resources.items() if key in s]
            other_typ, other_metric = 'activity', 'total_seconds'
            other_hyper = new_activity_hyper
            quant_dic = resource_concurrent_quantile_dict
            other_dic = activity_total_duration_quantile_dict
            relevant_hyper = new_resource_hyper

        means = [df.loc[df[other_typ] == target, other_metric].mean() for target in targets]
        index = np.argmin(means) if other_typ == 'resource' else np.argmax(means)
        print(means)
        selected_target = targets[index]
        other_i = other_hyper[selected_target]

        i = relevant_hyper[key]
        real_median = df.loc[df[typ] == key, metric].mean()
        real_std = df.loc[df[typ] == key, metric].std()
        simulated_median = df_simulation.loc[df_simulation[typ] == key, metric].mean()
        quants = len(quant_dic[key]) - 1
        if real_median < simulated_median:
            new_i = i // 2
            new_other_i = other_i // 2 if other_typ == 'activity' else (other_i + len(other_dic[selected_target])) // 2
        else:
            new_i = (i + quants + 1) // 2
            new_other_i = (other_i + len(other_dic[selected_target])) // 2 if other_typ == 'activity' else other_i // 2
        # change = 1 if real_median > simulated_median else -1
        j = np.clip(new_i, 0, quants)
        if i != j:
            print(
                f'{typ} {key} was selected to change from q={i / quants * 100:.1f}%->{j / quants * 100:.1f}% (value={quant_dic[key][i]:.2f}->{quant_dic[key][j]:.2f}) (individual score: {tup[1]:.4f})')
            print(f'targets should be', targets, 'selected', selected_target, other_i, new_other_i)
            # other_hyper[selected_target] = new_other_i
            relevant_hyper[key] = j
            new_hyper = HyperParameters(new_activity_hyper, new_resource_hyper)

            f, (ax1, ax2) = plt.subplots(1, 2, sharey=True, sharex=True)
            sns.histplot(df.loc[df[typ] == key, metric], discrete=(typ == 'resource'), ax=ax1, stat='probability')
            ax1.axvline(x=real_median, color='red', linewidth=.5, linestyle='--', label='median')
            ax1.set_title('original')
            sns.histplot(df_simulation.loc[df_simulation[typ] == key, metric], discrete=(typ == 'resource'), ax=ax2,
                         stat='probability')
            ax2.axvline(x=simulated_median, color='red', linewidth=.5, linestyle='--', label='median')
            ax2.set_title('simulation')
            plt.suptitle(f'{str.capitalize(typ)} {key} {metric} Distribution')
            plt.show()

        if new_hyper is not None:
            if new_hyper not in past_hyper_parameters:
                return new_hyper
            else:
                print('Next hyper parameters were already tried')

    return None


def trans(list_of_dict):
    trans_dic = {}
    for dic in list_of_dict:
        for k, v in dic.items():
            if k not in trans_dic:
                trans_dic[k] = []
            trans_dic[k].append(v)
    return trans_dic


def trans_scores(scores, score_dicts):
    transposed_scores = trans(score_dicts)
    transposed_scores['total'] = scores
    for key in transposed_scores:
        if isinstance(transposed_scores[key], list):
            if len(transposed_scores[key]) > 0 and isinstance(transposed_scores[key][0], dict):
                transposed_scores[key] = trans(transposed_scores[key])
    return transposed_scores


def fit_to_log_old(log, petrinet_model, sim_graph, replay_result, cases_per_iteration=1000, use_logscale=True,
                   use_quantiles=False,
                   max_iterations=50, time_limit=datetime.timedelta(minutes=5)):
    df = replay_result.trace_tracker.measurements_df

    activity_steps, resource_steps = 32, 32

    activities, resources = sorted(set(df['activity'])), sorted(set(df['resource']))

    if use_quantiles:
        activity_total_duration_quantile_dict = spe.activity_total_duration_quantiles(
            df,
            activities,
            k=activity_steps)
    else:
        activity_total_duration_quantile_dict = spe.activity_total_duration_log_fraction(
            df,
            activities,
            k=activity_steps) if use_logscale else spe.activity_total_duration_fraction(
            df,
            activities,
            k=activity_steps)
        activity_total_duration_quantile_dict = make_unique(activity_total_duration_quantile_dict)

    if use_quantiles:
        resource_concurrent_quantile_dict = spe.resource_capacity_quantiles(
            df,
            resources,
            k=resource_steps)
    else:
        resource_concurrent_quantile_dict = spe.resource_capacity_log_fraction(
            df,
            resources,
            k=resource_steps) if use_logscale else spe.resource_capacity_fraction(
            df,
            resources,
            k=resource_steps)
        resource_concurrent_quantile_dict = make_unique(resource_concurrent_quantile_dict)

    base_hyper_parameters = [
        HyperParameters({a: len(qs) // 2 for a, qs in activity_total_duration_quantile_dict.items()},
                        {r: len(qs) // 2 for r, qs in resource_concurrent_quantile_dict.items()})]

    start = time_utils.now()
    max_end_time = start + time_limit
    print(
        f'Starting fitting with {max_iterations} max iterations and initial hyper parameters={base_hyper_parameters[0]} @{start}')

    evaluation_cache = {}
    scores = []
    score_dicts = []
    intermediate_results = []

    past_hyper_parameters = set()
    # past_model_configs = set()

    iteration = 0
    while len(base_hyper_parameters) > 0 and iteration < max_iterations and time_utils.now() <= max_end_time:
        print('Starting iteration ', iteration)
        hyper_parameters = base_hyper_parameters.pop()

        past_hyper_parameters.add(hyper_parameters)

        model_config = create_simplified_model_configuration(df, (
            activity_total_duration_quantile_dict, resource_concurrent_quantile_dict), hyper_parameters,
                                                             replay_result)
        # print(model_config)
        execution_parameters = default_execution_parameters()
        execution_parameters[ExecutionParameters.CasesToGenerate] = cases_per_iteration
        execution_parameters[ExecutionParameters.RealtimeLimit] = datetime.timedelta(minutes=2)

        sim_model = create_simulation_model(sim_graph, model_config, execution_parameters)
        simulator = simulate(sim_model,
                             simulation_log_filename=f'iterative2_{iteration}_{filenameable_timestamp()}.log')
        print(f'Simulation took {simulator.duration}')
        simulated_log = simulator.get_log(allowed_lifecycles=AvailableLifecycles.CompleteOnly)

        replay_result_simulation = petrinet_replay.replay_log(simulated_log, petrinet_model)
        score, score_dict = score_log(log, simulated_log, replay_result, replay_result_simulation,
                                      evaluation_cache)

        print('score:', score, 'individual scores:', score_dict)

        scores.append(score)
        score_dicts.append(score_dict)

        intermediate_results.append((hyper_parameters, model_config, simulated_log))

        new_hyper = select_next_hyper_parameters(replay_result, replay_result_simulation, hyper_parameters,
                                                 model_config, score_dict, (activity_total_duration_quantile_dict,
                                                                            resource_concurrent_quantile_dict),
                                                 past_hyper_parameters)

        iteration += 1
        if new_hyper is not None:
            base_hyper_parameters.append(new_hyper)

    fitting_duration = time_utils.now() - start
    print(
        f'Finished fitting with {iteration} iterations in {fitting_duration} ({datetime.timedelta(seconds=fitting_duration.total_seconds() // iteration)}/it)')

    min_idx = np.argmin(scores)

    return intermediate_results[min_idx], scores[min_idx], scores, trans_scores(scores, score_dicts)


def save_fitting_results(simulated_log, scorelist, subscorelists, prefix=''):
    with open(prefix + '_results/' + prefix + '_scorelist.json', 'w') as f_scorelist:
        json.dump(scorelist, f_scorelist)
    with open(prefix + '_results/' + prefix + '_subscorelists.json', 'w') as f_subscorelists:
        json.dump(subscorelists, f_subscorelists)
    pm4py.write_xes(simulated_log, prefix + '_results/' + prefix + '_simulated_log')
