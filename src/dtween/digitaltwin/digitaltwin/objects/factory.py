from dtween.digitaltwin.digitaltwin.objects.obj import DigitalTwin, Guard
# from dtween.digitaltwin.ocpn.objects.obj import Marking
from ocpa.objects.oc_petri_net.obj import Marking

from enum import Enum


def get_digital_twin(ocpn):
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
    return DigitalTwin(ocpn=ocpn)
