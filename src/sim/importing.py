import os

import pm4py
from pm4py.discovery import discover_petri_net_inductive
from pm4py.objects.log.log import EventLog, Trace, Event
from pm4py.read import read_xes, read_petri_net
from pm4py.util import xes_constants

from sim.model_configuration import create_sim_graph
from sim.utils import PathConstants, AcceptingPetrinet


def event_wise_filter(log, event_filter):
    nl = EventLog()
    for trace in log:
        nt = Trace()
        for attr in trace.attributes:
            nt.attributes[attr] = trace.attributes[attr]
        for event in trace:
            if event_filter(event):
                nt.append(event)

        if len(nt) > 0:
            nl.append(nt)

    return nl


def event_transition_completion(log):
    nl = EventLog()
    for trace in log:
        nt = Trace()
        for attr in trace.attributes:
            nt.attributes[attr] = trace.attributes[attr]
        for event in trace:
            ne = event
            if xes_constants.DEFAULT_TRANSITION_KEY not in event:
                ne = Event(event)
                ne[xes_constants.DEFAULT_TRANSITION_KEY] = 'complete'
            nt.append(ne)
        nl.append(nt)
    return nl


def form_log_path(log_path):
    return os.path.join(PathConstants.base_event_log_path, log_path)


def prepare_petrinet(log, petrinet_path=None):
    if petrinet_path is not None:
        net, im, fm = read_petri_net(os.path.join(PathConstants.base_petrinet_path, petrinet_path))
    else:
        # TODO look at this again to support huge ugly input logs and models
        # sampled_log = pm4py.objects.log.util.sampling.sample_log(complete_only_log, 1000)
        # discovery_log = pm4py.filter_variants_percentage(complete_only_log, percentage=variant_percentage)
        discovery_log = log
        net, im, fm = discover_petri_net_inductive(discovery_log)
        pm4py.write_petri_net(net, im, fm,
                              os.path.join(PathConstants.base_petrinet_path, 'last_discovered_petrinet.pnml'))
    return AcceptingPetrinet(net, im, fm)


def prepare_input(log, petrinet_path=None, sample_size=None):
    if sample_size is not None:
        log = pm4py.objects.log.util.sampling.sample_log(log, sample_size)
    complete_only_log = log
    if any(xes_constants.DEFAULT_TRANSITION_KEY not in event for trace in log for event in trace):
        complete_only_log = event_transition_completion(log)
    elif any(event[xes_constants.DEFAULT_TRANSITION_KEY] == 'complete'
             for trace in log for event in trace):
        complete_only_log = event_wise_filter(log,
                                              lambda ev: ev[xes_constants.DEFAULT_TRANSITION_KEY] == 'complete')

    accepting_petrinet = prepare_petrinet(complete_only_log, petrinet_path)

    return complete_only_log, accepting_petrinet


def load_input(log_path, petrinet_path=None, return_original=False, sample_size=None):
    f"""
    Loads log from {PathConstants.base_event_log_path} folder and optionally petrinet from {PathConstants.base_petrinet_path} (otherwise IM is used for automated discovery).
    If necessary, the cases are projected down to complete-only lifecycle transitions.
    :param log_path: 
    :param petrinet_path: 
    :param return_original: for evaluation purposes the unprojected log with all lifecycles is returned as well 
    :return: log, (petrinet, initial marking, final marking)) [, original_log]
    """
    original_log = read_xes(form_log_path(log_path))
    prepared_log, prepared_petrinet = prepare_input(original_log, petrinet_path, sample_size)
    labels = {t.label for t in prepared_petrinet.net.transitions} # TODO remember to make proper decision
    prepared_log = event_wise_filter(prepared_log,
                      lambda ev: ev[xes_constants.DEFAULT_NAME_KEY] in labels)
    if return_original:
        return prepared_log, prepared_petrinet, original_log
    else:
        return prepared_log, prepared_petrinet


def prepare_simulation_graph(acc_petri: AcceptingPetrinet):
    graph = create_sim_graph(acc_petri)
    return graph
