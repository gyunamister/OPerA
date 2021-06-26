from dtween.digitaltwin.digitaltwin.objects.obj import DigitalTwin
from dtween.digitaltwin.ocpn.objects.obj import Marking
from enum import Enum


def get_digital_twin(ocpn, valves=None, guards=None, marking=None, config=None, omap=None):
    """
    Finds the performance spectrum provided a log/dataframe
    and a list of activities

    Parameters
    -------------
    type
        Type to be used (see Variants Enum)
    parameters
        Parameters of the algorithm, including:
            - Parameters.MIN_KEY
            - Parameters.MAX_KEY

    Returns
    -------------
    ps
        Performance spectrum object (dictionary)
    """
    if valves is None:
        valves = []

    if guards is None:
        guards = {}

    if marking is None:
        marking = Marking()

    if config is None:
        config = {}

    if omap is None:
        omap = {}
    return DigitalTwin(ocpn, valves, guards, marking, config, omap)


def update_guards(dt, guards):
    dt.guards = guards
    return dt
