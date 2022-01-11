from __future__ import annotations

import functools
from datetime import datetime, timedelta
from typing import List, Tuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sim.case
    import sim.sim_model as smodel


def verify(*checks):
    def wrapper(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            result = func(*args, **kwargs)
            for check in checks:
                assert check(result)
            return result

        return decorated

    return wrapper


def nonnegative_timedelta(v):
    return v >= timedelta(0)


def in_range(low, high):
    return lambda v: low <= v <= high


class QueueingDiscipline:

    def select(self, queue: List[Tuple[datetime, sim.case.OCCase]]) -> int: ...


class ProcessingTimeSampler:

    @verify(nonnegative_timedelta)
    def sample(self, case: sim.case.OCCase,
               resource: smodel.ResourceModel) -> timedelta: ...


class CaseClassifier:

    def __init__(self, number_of_classes) -> None:
        self.__number_of_classes = number_of_classes

    @property
    def number_of_classes(self) -> int:
        return self.__number_of_classes

    def classify_override(self, case: sim.case.OCCase) -> int: ...

    def classify(self, case: sim.case.OCCase) -> int:
        classification = self.classify_override(case)
        assert 0 <= classification < self.number_of_classes
        return classification


class MultiDecisionClassifier:

    def classify(self, case: sim.case.OCCase) -> List[int]: ...


class InterArrivalSampler:

    @verify(nonnegative_timedelta)
    def sample(self, current_time) -> timedelta: ...


class DelaySampler:

    @verify(nonnegative_timedelta)
    def sample(self, current_time) -> timedelta: ...


class BusinessHours:

    @verify(in_range(0, 1))
    def average_availability(self) -> float: ...

    def is_dynamic(self) -> bool: ...

    def in_business(self, current_time: datetime) -> bool: ...

    def next_change(self, current_time: datetime) -> datetime: ...


class ResourcePerformance:

    @verify(in_range(0, 1))
    def performance(self, utilization: float) -> float: ...


class BusinessRules:
    def evaluate(self) -> bool: ...


class ValueSampler:

    def sample(self, value) -> int: ...
