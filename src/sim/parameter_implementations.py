from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timedelta, time
from typing import List, Tuple, Optional, Dict
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import scipy.stats

import sim.model_parameters as params
from sim import time_utils, utils
from sim.enums import ResourceProperty, ResourceState
from sim.model_parameters import ResourcePerformance
from sim.time_utils import Weekdays

if TYPE_CHECKING:
    import sim.case
    import sim.sim_model as smodel


class FixedRelative(params.QueueingDiscipline):

    def __init__(self, relative_index) -> None:
        super().__init__()
        self.relative_index = relative_index

    def select(self, queue: List[Tuple[datetime, sim.case.OCCase]]) -> int:
        return int(self.relative_index * (len(queue) - 1))

    def __str__(self) -> str:
        return f'FixedRelativeQueueing(rel_index={self.relative_index})'


class RandomQueueing(params.QueueingDiscipline):

    def select(self, queue: List[Tuple[datetime, sim.case.OCCase]]) -> int:
        return random.randint(0, len(queue) - 1)

    def __str__(self) -> str:
        return f'Random'


class FifoQueueing(FixedRelative):

    def __init__(self) -> None:
        super().__init__(0)

    def __str__(self) -> str:
        return 'Fifo'


class LifoQueueing(FixedRelative):

    def __init__(self) -> None:
        super().__init__(1)

    def __str__(self) -> str:
        return 'Lifo'


Fifo = FifoQueueing()
Lifo = LifoQueueing()
Random = RandomQueueing()


class DistSampler(params.ProcessingTimeSampler, params.DelaySampler, params.InterArrivalSampler):

    def __init__(self, distribution, dist_kwargs, unit='m') -> None:
        super().__init__()
        self.unit = unit
        self.dist_kw_args = utils.FrozenDict(dist_kwargs)
        self.distribution = distribution
        self.dist = distribution(**dist_kwargs)

    def sample(self, *args) -> timedelta:
        val = self.dist.rvs()
        return pd.Timedelta(max(int(val), 1), unit=self.unit)

    def __eq__(self, o: object) -> bool:
        return isinstance(o,
                          self.__class__) and self.distribution == o.distribution and self.dist_kw_args == o.dist_kw_args and self.unit == o.unit

    def __hash__(self) -> int:
        return hash((self.distribution, self.dist_kw_args, self.unit))

    def __str__(self) -> str:
        return f'DistSampler({self.distribution.name}({self.dist_kw_args}) {self.unit})'


def ExpSampler(inter, unit='m'):
    return DistSampler(scipy.stats.expon, {'scale': inter}, unit=unit)


def NormSampler(mu, unit='m'):
    return DistSampler(scipy.stats.norm, {'loc': mu}, unit=unit)


def LogNormSampler(mu, unit='m'):
    return DistSampler(scipy.stats.lognorm, {'scale': np.exp(mu)}, unit=unit)


def fitted_expon(values, unit='m'):
    fit = scipy.stats.expon.fit(values)
    return DistSampler(scipy.stats.expon, {'loc': fit[0], 'scale': fit[1]}, unit=unit)


class EmpiricalSampler(params.ProcessingTimeSampler, params.DelaySampler, params.InterArrivalSampler):

    def __init__(self, percentiles_df: pd.DataFrame, use_linear_combination=True, k=None) -> None:
        super().__init__()
        self.use_linear_combination = use_linear_combination
        if k is not None:
            percentiles_df = EmpiricalSampler.discretize(percentiles_df, k=k)
        self.percentiles = tuple(percentiles_df.reset_index(drop=True).values)
        self.k = len(percentiles_df)

    def sample(self, *args):
        m = np.random.rand()
        m_k = m * (self.k - 1)
        if self.use_linear_combination:
            lower_i = int(np.floor(m_k))
            upper_i = int(np.ceil(m_k))
            return pd.Timedelta(
                self.percentiles[lower_i] * (m_k - lower_i) + self.percentiles[upper_i] * (upper_i - m_k))
        else:
            return pd.Timedelta(self.percentiles[int(np.rint(m_k))])

    @staticmethod
    def discretize(data_df, k=10):
        return data_df.quantile([i / k for i in range(k + 1)])

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self.__class__) \
            and self.use_linear_combination == o.use_linear_combination \
            and self.percentiles == o.percentiles and self.k == o.k

    def __hash__(self) -> int:
        return hash((self.use_linear_combination, self.percentiles, self.k))

    def __str__(self) -> str:
        return f'EmpiricalSampler(percentiles={list(self.percentiles)}, linear_comb={self.use_linear_combination})'


class StaticSampler(params.ProcessingTimeSampler, params.DelaySampler, params.InterArrivalSampler):

    def __init__(self, value: timedelta) -> None:
        super().__init__()
        self.value = value

    def sample(self, *args) -> timedelta:
        return self.value

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self.__class__) and self.value == o.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __str__(self) -> str:
        return f'StaticSampler({self.value})'


ZeroSampler = StaticSampler(timedelta(seconds=0))
ZeroSampler.__str__ = lambda self: 'ZeroSampler'


class ConstantPerformance(ResourcePerformance):

    def __init__(self, value: float) -> None:
        super().__init__()
        #assert 0 <= value <= 1
        self.value = value

    def performance(self, utilization: float):
        return self.value

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self.__class__) and self.value == o.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __str__(self) -> str:
        return f'ConstantPerformance({self.value})'


class ConstantPeakPerformance(ConstantPerformance):

    def __init__(self) -> None:
        super().__init__(1.0)

    def __str__(self) -> str:
        return 'ConstantPeakPerformance'


PeakPerformance = ConstantPeakPerformance()


class LinearYerkesDodson(ResourcePerformance):
    """
    badly linearized yerkes-dodson parabola
    """

    def __init__(self, peak) -> None:
        super().__init__()
        assert 0 <= peak <= 1
        self.peak = peak

    def performance(self, arousal):
        if arousal <= self.peak:
            return (self.peak - arousal) / self.peak
        else:
            return (arousal - self.peak) / (1 - self.peak)

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self.__class__) and self.peak == o.peak

    def __hash__(self):
        return hash(self.peak)

    def __str__(self):
        return f'LinearYerkesDodson(peak={self.peak})'


class ResourceDependentPTSampler(params.ProcessingTimeSampler):

    def __init__(self, base_sampler: params.ProcessingTimeSampler, resource_skills: Dict[str, float] = None,
                 use_resource_performance: bool = False) -> None:
        super().__init__()
        self.base_sampler = base_sampler
        if resource_skills is None:
            resource_skills = utils.FrozenDict()
        assert all(0 <= s <= 1 for s in resource_skills.values())
        self.resource_skills = resource_skills
        self.use_resource_performance = use_resource_performance
        self.lookup = lambda r: self.resource_skills.get(r.label, 1)
        if use_resource_performance:
            def look(r):
                skill_factor = self.resource_skills.get(r.label, 1)
                performance_factor = 1
                performance_calculator = r.data.peek_at_property(
                    ResourceProperty.Performance)
                if performance_calculator is not None:
                    performance_factor = performance_calculator.performance(
                        r.data.peek_at_state(ResourceState.CurrentlyAssigned) / r.data.peek_at_property(
                            ResourceProperty.Capacity))
                return skill_factor * performance_factor

            self.lookup = look

    def sample(self, case: sim.case.OCCase, resource: smodel.ResourceModel) -> timedelta:
        base = self.base_sampler.sample()
        lookup = self.lookup(resource)
        return base / lookup

    def __eq__(self, o: object) -> bool:
        return isinstance(o,
                          self.__class__) and self.base_sampler == o.base_sampler and self.resource_skills == o.resource_skills and self.use_resource_performance == o.use_resource_performance

    def __hash__(self) -> int:
        return hash((self.base_sampler, self.resource_skills, self.use_resource_performance))

    def __str__(self) -> str:
        return f'ResourceDependentPTSampler(base_sampler={self.base_sampler}, skills={self.resource_skills}, use_resource_performance={self.use_resource_performance})'


class StochasticClassifier(params.CaseClassifier):

    def __init__(self, probabilities) -> None:
        super().__init__(len(probabilities))
        self.probabilities = probabilities

    def classify_override(self, case: sim.case.OCCase) -> int:
        return np.random.choice(self.number_of_classes, p=self.probabilities)

    def __eq__(self, o: object) -> bool:
        return isinstance(o,
                          self.__class__) and self.number_of_classes == o.number_of_classes and self.probabilities == o.probabilities

    def __hash__(self) -> int:
        return hash((self.number_of_classes, self.probabilities))

    def __str__(self) -> str:
        return f'StochasticClassifier({list(self.probabilities)})'


class AlwaysInBusinessHours(params.BusinessHours):

    def average_availability(self) -> float:
        return 1.0

    def is_dynamic(self) -> bool:
        return False

    def in_business(self, current_time: datetime) -> bool:
        return True

    def next_change(self, current_time: datetime) -> Optional[datetime]:
        return None

    def __str__(self) -> str:
        return 'AlwaysInBusiness'


AlwaysInBusiness = AlwaysInBusinessHours()


class WorkweekBusinessHours(params.BusinessHours):

    def __init__(self, daily_business_hours: Dict[Weekdays, Tuple[datetime.time, datetime.time]]) -> None:
        self.bh = utils.FrozenDict(daily_business_hours)
        # at least one business day, leads to (recursion) stack overflow otherwise
        assert len(self.bh) > 0

    def average_availability(self) -> float:
        agg = pd.Timedelta(0)
        for day, (start, end) in self.bh.items():
            hours_on_day = time_utils.duration_between_times(start, end)
            agg += hours_on_day
        return agg / pd.Timedelta(days=7)

    def is_dynamic(self) -> bool:
        return True

    def in_business(self, current_time: datetime) -> bool:
        day = Weekdays(current_time.weekday())
        if day in self.bh:
            start, end = self.bh[day]
            return start <= current_time.time() < end
        return False

    def _next_change_recursive(self, current_time: datetime, start_day, looped_once=False):
        day = Weekdays(current_time.weekday())
        if day in self.bh:
            start, end = self.bh[day]
            start_dt, end_dt = time_utils.set_time(
                current_time, start), time_utils.set_time(current_time, end)
            if current_time < start_dt:
                return start_dt
            elif current_time < end_dt:
                return end_dt
        next_day = time_utils.next_day(current_time)
        if Weekdays(next_day.weekday()) is not start_day:
            return self._next_change_recursive(next_day, start_day, looped_once=False)
        elif not looped_once:
            return self._next_change_recursive(next_day, start_day, looped_once=True)
        else:
            print(current_time, next_day, start_day, looped_once)
            print(current_time.weekday(), Weekdays(current_time.weekday()))
            print(next_day.weekday(), Weekdays(next_day.weekday()))
            print(self.bh)

    def next_change(self, current_time: datetime):
        return self._next_change_recursive(current_time, Weekdays(current_time.weekday()))

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self.__class__) and self.bh == o.bh

    def __hash__(self) -> int:
        return hash(self.bh)

    def __str__(self) -> str:
        return f'WorkweekBusinessHours({str(self.bh)})'


StandardWorkweek = WorkweekBusinessHours({
    Weekdays.Monday: (time(hour=9), time(hour=17)),
    Weekdays.Tuesday: (time(hour=9), time(hour=17)),
    Weekdays.Wednesday: (time(hour=9), time(hour=17)),
    Weekdays.Thursday: (time(hour=9), time(hour=17)),
    Weekdays.Friday: (time(hour=9), time(hour=17)),
})


class ValueDistSampler(params.ValueSampler):

    def __init__(self, distribution, dist_kwargs) -> None:
        super().__init__()
        self.dist_kw_args = utils.FrozenDict(dist_kwargs)
        self.distribution = distribution
        self.dist = distribution(**dist_kwargs)

    def sample(self, *args) -> timedelta:
        val = self.dist.rvs()
        return int(val)

    def __eq__(self, o: object) -> bool:
        return isinstance(o,
                          self.__class__) and self.distribution == o.distribution and self.dist_kw_args == o.dist_kw_args

    def __hash__(self) -> int:
        return hash((self.distribution, self.dist_kw_args))

    def __str__(self) -> str:
        return f'DistSampler({self.distribution.name}({self.dist_kw_args}))'


def ValueUniformSampler(loc, scale):
    return ValueDistSampler(scipy.stats.uniform, {'loc': loc, 'scale': scale})


def ValueIntUniformSampler(loc, scale):
    return ValueDistSampler(scipy.stats.randint, {'loc': loc})


class PR_BusinessRules(params.BusinessRules):

    def __init__(self, oc_case: sim.case.OCCase) -> None:
        super().__init__()
        self.oc_case = oc_case

    def evaluate(self, *args) -> bool:
        min_planned_delivery_days = 0
        materials = [
            x for x in self.oc_case.objects if x.object_type == "Material"]
        if all(mat.ovmap["planned_delivery_days"] > min_planned_delivery_days for mat in materials):
            return True
        else:
            return False

    def __eq__(self, o: object) -> bool:
        return isinstance(o,
                          self.__class__) and self.object_type == o.object_type

    def __hash__(self) -> int:
        return hash(self.object_type)

    def __str__(self) -> str:
        return f'ObjectSampler({self.object_type})'
