from typing import Tuple

from pm4py.objects.log.log import EventLog

from sim import fitting_machinery
from sim import model_configuration
from sim import petrinet_replay
from sim.petrinet_replay import ReplayResult
from sim.sim_graph import SimulationGraph
from sim.utils import AcceptingPetrinet


def pre_process_input(log: EventLog, petrinet_model: AcceptingPetrinet) -> Tuple[SimulationGraph, ReplayResult]:
    """
    Replays the log on the petrinet (using alignments) returning the simulation graph derived from the petrinet as well as condensed replay data.
    :param log:
    :param petrinet_model:
    :return:
    """
    replay_data = petrinet_replay.replay_log(log, petrinet_model)
    sim_graph = model_configuration.create_sim_graph(petrinet_model, replay_data.decision_points)
    return sim_graph, replay_data


def fit_preprocessed(log: EventLog, petrinet_model: AcceptingPetrinet, sim_graph: SimulationGraph,
                     replay_result: ReplayResult, old=True, **kwargs):
    return fitting_machinery.fit_to_log_old(log, petrinet_model, sim_graph, replay_result,
                                            **kwargs) if old else fitting_machinery.fit_to_log(log, petrinet_model,
                                                                                               sim_graph, replay_result,
                                                                                               **kwargs)


def fit(log: EventLog, petrinet_model: AcceptingPetrinet, **kwargs):
    simulation_graph, replay_result = pre_process_input(log, petrinet_model)
    return fit_preprocessed(log, petrinet_model, simulation_graph, replay_result, **kwargs)
