from dtween.digitaltwin.valve.objects.obj import NumericalValve, TestValve
from dtween.available.available import AvailableValves
from enum import Enum


class Variants(Enum):
    NUMERICAL = NumericalValve
    TEST = TestValve


def get_valve(variant, name, cur, **kwargs):
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
    constructor = get_constructor(variant)
    return constructor(variant, name, cur, kwargs)


def get_constructor(variant):
    if variant == AvailableValves.NUMERICAL.value:
        return Variants.NUMERICAL.value
    elif variant == 'test':
        return Variants.TEST.value
    else:
        raise ValueError(variant)
