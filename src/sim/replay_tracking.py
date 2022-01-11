from collections import defaultdict
from dataclasses import dataclass
from typing import List, Any, Dict

import numpy as np
import pandas as pd
import pm4py.util.xes_constants as xes_const

from sim import time_utils
from sim.enums import Lifecycle, AvailableLifecycles
from sim.utils import auto_str


class GeneratingFunctions:

    def __getattr__(self, name: str):
        gen__name = 'gen_' + name
        if gen__name in self.__dir__():
            print('generating', name)
            self.__dict__[name] = self.__getattribute__(gen__name)()
            return self.__dict__[name]


class Tracker:

    def __init__(self) -> None:
        super().__init__()
        self.history = []
        self._options = []
        self._option_indices = {}
        self._decisions_df = None

    @property
    def options(self) -> List[Any]:
        return self._options

    @property
    def option_indices(self) -> Dict[Any, int]:
        return self._option_indices

    @options.setter
    def options(self, value: List[Any]):
        self._options = value
        self._option_indices = {o: i for i, o in enumerate(value)}

    @property
    def num_options(self):
        return len(self.options)

    @property
    def decisions_df(self):
        if self._decisions_df is None:
            self._decisions_df = self.generate_decisions_df()
        return self._decisions_df

    def generate_decisions_df(self): ...

    def track(self, case_id, time, option): ...


class DecisionTracker(Tracker):

    def __init__(self) -> None:
        super().__init__()

    def track(self, case_id, time, option):
        index = self.option_indices[option]
        self.history.append((case_id, time, index))

    def generate_decisions_df(self):
        cat = pd.CategoricalDtype(np.arange(self.num_options), ordered=True)
        df = pd.DataFrame(data=self.history, columns=['case_id', 'time', 'decision'])
        df['decision'] = df['decision'].astype(cat, copy=False)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True, drop=False)
        df.sort_index(inplace=True)
        return df


class ArrivalTracker:

    def __init__(self):
        self.history = defaultdict(list)
        self._arrival_history_df = None  # cache because of sorting which is necessary due to unordered tracking

    def track(self, time, case_attributes):
        self.history['time'].append(time)
        for attr, value in case_attributes.items():
            self.history[attr].append(value)

    @property
    def arrival_history_df(self):
        if self._arrival_history_df is None:
            self._arrival_history_df = self.generate_arrival_history_df()
        return self._arrival_history_df

    def generate_arrival_history_df(self):
        df = pd.DataFrame(self.history)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True, drop=False)
        df.sort_index(inplace=True)
        return df


class QueueModel:

    def __init__(self) -> None:
        super().__init__()
        self.queue = []
        self.enqueued_cases = {}
        self.event_history = []
        self.dequeue_history = []
        self._queueing_events_df = None
        self._queueing_history_df = None

    def enqueue(self, case_id, time, resource, event):
        self.queue.append(case_id)
        length = len(self.queue)
        self.enqueued_cases[case_id] = (time, resource, event, length)
        self.event_history.append([time, case_id, resource, 'enqueue', length])

    def dequeue(self, case_id, time, resource, event):
        index = self.queue.index(case_id)
        self.queue.pop(index)
        length = len(self.queue)
        enqueue_time, enqueue_resource, enqueue_event, enqueue_length = self.enqueued_cases.pop(case_id)
        self.event_history.append([time, case_id, resource, 'dequeue', length])
        # queue length on exit (not after) is interesting here
        self.dequeue_history.append([time, case_id, resource, time - enqueue_time, index, length + 1])

    @property
    def queueing_events_df(self):
        if self._queueing_events_df is None:
            self._queueing_events_df = self.generate_queueing_events_df()
        return self._queueing_events_df

    def generate_queueing_events_df(self):
        df = pd.DataFrame(data=self.event_history, columns=['time', 'case_id', 'resource', 'type', 'queue_length'])
        df['resource'] = df['resource'].astype('category', copy=False)
        df['type'] = df['type'].astype('category', copy=False)
        df['time'] = pd.to_datetime(df['time'])
        return df

    @property
    def queueing_history_df(self):
        if self._queueing_history_df is None:
            self._queueing_history_df = self.generate_queueing_history_df()
        return self._queueing_history_df

    def generate_queueing_history_df(self):
        df = pd.DataFrame(data=self.dequeue_history,
                          columns=['time', 'case_id', 'resource', 'wait', 'index', 'queue_length'])
        df['resource'] = df['resource'].astype('category', copy=False)
        df['time'] = pd.to_datetime(df['time'])
        return df


class ProcessingModel:

    def __init__(self) -> None:
        super().__init__()
        self.processing_queue = []
        self.processing_cases = {}
        self.event_history = []
        self.processing_history = []
        self._processing_events_df = None
        self._processing_history_df = None

    def process(self, case_id, time, resource, event):
        self.processing_queue.append(case_id)
        length = len(self.processing_queue)
        self.processing_cases[case_id] = (time, resource, event, length)
        self.event_history.append([time, case_id, resource, 'started', length])

    def complete(self, case_id, time, resource, event):
        self.processing_queue.remove(case_id)
        length = len(self.processing_queue)
        (start_time, start_resource, start_event, start_concurrent) = self.processing_cases[case_id]
        self.event_history.append([time, case_id, resource, 'completed', length])
        self.processing_history.append([start_time, case_id, resource, time - start_time, start_concurrent])

    @property
    def processing_events_df(self):
        if self._processing_events_df is None:
            self._processing_events_df = self.generate_processing_events_df()
        return self._processing_events_df

    def generate_processing_events_df(self):
        df = pd.DataFrame(data=self.event_history,
                          columns=['time', 'case_id', 'resource', 'type', 'concurrent_items'])
        df['resource'] = df['resource'].astype('category', copy=False)
        df['type'] = df['type'].astype('category', copy=False)
        df['time'] = pd.to_datetime(df['time'])
        return df

    @property
    def processing_history_df(self):
        if self._processing_history_df is None:
            self._processing_history_df = self.generate_processing_history_df()
        return self._processing_history_df

    def generate_processing_history_df(self):
        df = pd.DataFrame(data=self.processing_history,
                          columns=['start_time', 'case_id', 'resource', 'duration', 'concurrent_items'])
        df['resource'] = df['resource'].astype('category', copy=False)
        df['start_time'] = pd.to_datetime(df['start_time'])
        return df


class DelayModel:

    def __init__(self) -> None:
        self.delays = []

    def accept(self, case_id, time, delay):
        self.delays.append((time, case_id, delay))

    @property
    def delay_df(self):
        df = pd.DataFrame(data=self.delays, columns=['time', 'case_id', 'delay'])
        df['time'] = pd.to_datetime(df['time'])
        return df


class ResourcePool:

    def __init__(self) -> None:
        super().__init__()
        self.event_history = []
        self.resource_history = []
        self.assignment_counts = []
        self.open_assignments = defaultdict(dict)
        self.observed_resources = set()

    def assign(self, case_id, activity, time, resource):
        self.observed_resources.add(resource)
        self.open_assignments[resource][(case_id, activity)] = time
        length = len(self.open_assignments[resource])
        self.assignment_counts.append([resource, time, length])
        self.event_history.append([time, case_id, activity, resource, 'assigned', length])

    def release(self, case_id, activity, time, resource):
        assignment_time = self.open_assignments[resource].pop((case_id, activity))
        length = len(self.open_assignments[resource])
        self.assignment_counts.append([resource, time, length])
        self.event_history.append([time, case_id, activity, resource, 'released', length])
        self.resource_history.append([resource, assignment_time, activity, time - assignment_time, length])

    @property
    def event_history_df(self):
        df = pd.DataFrame(data=self.event_history,
                          columns=['time', 'case_id', 'activity', 'resource', 'type', 'concurrently_assigned'])
        df['activity'] = df['activity'].astype('category', copy=False)
        df['resource'] = df['resource'].astype('category', copy=False)
        df['type'] = df['type'].astype('category', copy=False)
        df['time'] = pd.to_datetime(df['time'])
        return df

    @property
    def assignment_counts_df(self):
        df = pd.DataFrame(data=self.assignment_counts, columns=['resource', 'time', 'count'])
        df['resource'] = df['resource'].astype('category', copy=False)
        df['time'] = pd.to_datetime(df['time'])
        return df

    @property
    def resource_history_df(self):
        df = pd.DataFrame(data=self.resource_history,
                          columns=['resource', 'assignment_time', 'activity', 'duration', 'concurrently_assigned'])
        df['assignment_time'] = pd.to_datetime(df['assignment_time'])
        return df


class ActivityTracker:

    def __init__(self, resource_pool: ResourcePool) -> None:
        super().__init__()
        self.resource_pool = resource_pool
        self.queue_model = QueueModel()
        self.delay_model = DelayModel()
        self.processing_model = ProcessingModel()
        self.history = []
        self.running_cases = defaultdict(list)
        self.delays = defaultdict(list)
        self.waits = defaultdict(list)
        self.services = defaultdict(list)

    @property
    def resource_pool(self) -> ResourcePool:
        return self._resource_pool

    @resource_pool.setter
    def resource_pool(self, value: ResourcePool) -> None:
        self._resource_pool = value

    def track(self, case_id, lifecycle, event):
        if lifecycle == Lifecycle.Enabled:
            self.enable(case_id, event)
        elif lifecycle == Lifecycle.Scheduled:
            self.schedule(case_id, event)
        elif lifecycle == Lifecycle.Started:
            self.start(case_id, event)
        elif lifecycle == Lifecycle.Completed:
            self.complete(case_id, event)

    def enable(self, case_id, event):
        time = time_utils.get_event_timestamp(event)
        self.history.append((time, case_id, Lifecycle.Enabled, event))
        self.running_cases[case_id] = time

    def schedule(self, case_id, event):
        time = time_utils.get_event_timestamp(event)
        resource = event[xes_const.DEFAULT_RESOURCE_KEY]
        enable_time = self.running_cases.pop(case_id)
        self.queue_model.enqueue(case_id, time, resource, event)
        self.history.append((time, case_id, Lifecycle.Scheduled, event))
        delay = time - enable_time
        self.delays[case_id].append(delay)
        self.delay_model.accept(case_id, time, delay)
        self.running_cases[case_id] = time

    def start(self, case_id, event):
        time = time_utils.get_event_timestamp(event)
        resource = event[xes_const.DEFAULT_RESOURCE_KEY]
        self.queue_model.dequeue(case_id, time, resource, event)
        self.resource_pool.assign(case_id, event[xes_const.DEFAULT_NAME_KEY], time, resource)
        self.processing_model.process(case_id, time, resource, event)
        self.history.append((time, case_id, Lifecycle.Started, event))
        schedule_time = self.running_cases.pop(case_id)
        self.waits[case_id].append(time - schedule_time)
        self.running_cases[case_id] = time

    def complete(self, case_id, event):
        time = time_utils.get_event_timestamp(event)
        resource = event[xes_const.DEFAULT_RESOURCE_KEY]
        self.resource_pool.release(case_id, event[xes_const.DEFAULT_NAME_KEY], time, resource)
        self.processing_model.complete(case_id, time, resource, event)
        self.history.append((time, case_id, Lifecycle.Completed, event))
        start_time = self.running_cases.pop(case_id)
        self.services[case_id].append(time - start_time)


@auto_str
@dataclass(unsafe_hash=True)
class DurationMeasurement:
    total: pd.Timedelta
    delay: pd.Timedelta = None
    wait: pd.Timedelta = None
    service: pd.Timedelta = None


@auto_str
@dataclass(unsafe_hash=True)
class Measurement:
    activity: str
    resource: str
    enabled: pd.Timestamp
    completed: pd.Timestamp
    durations: DurationMeasurement


class TraceTracker:

    def __init__(self, available_lifecycle_map: Dict[str, AvailableLifecycles]) -> None:
        super().__init__()
        self.available_lifecycle_map = available_lifecycle_map
        self.history = defaultdict(list)
        self.case_ids = []
        self._measurements = None  # TODO wasted memory by duplication
        self._measurements_df = None

    def track(self, case_id, activity, lifecycle, event):
        self.history[case_id].append((activity, lifecycle, event))
        self.case_ids.append(case_id)

    @property
    def measurements_dict(self) -> Dict[str, Dict[str, List[Measurement]]]:
        if self._measurements is None:
            self._measurements = self.generate_measurements_dict()

        return self._measurements

    def generate_measurements_dict(self) -> Dict[str, Dict[str, List[Measurement]]]:
        measurements = dict()
        for case_id, trace in self.history.items():
            enables = dict()
            schedules = dict()
            starts = dict()
            activity_wise_measurements = dict()

            for (activity, lifecycle, event) in trace:
                time = time_utils.get_event_timestamp(event)
                if lifecycle == Lifecycle.Enabled:
                    enables[activity] = time
                elif lifecycle == Lifecycle.Scheduled:
                    schedules[activity] = time
                elif lifecycle == Lifecycle.Started:
                    starts[activity] = time
                elif lifecycle == Lifecycle.Completed:
                    delay, wait, service = None, None, None
                    if activity in schedules:
                        delay = schedules[activity] - enables[activity]
                    if activity in schedules and activity in starts:
                        wait = starts[activity] - schedules[activity]
                    if activity in starts:
                        service = time - starts[activity]
                    dm = DurationMeasurement(time - enables[activity], delay, wait, service)
                    if activity not in activity_wise_measurements:
                        activity_wise_measurements[activity] = []
                    activity_wise_measurements[activity].append(
                        Measurement(activity, event[xes_const.DEFAULT_RESOURCE_KEY], enables[activity], time, dm))
                    del enables[activity]
                    schedules.pop(activity, None)
                    starts.pop(activity, None)

            measurements[case_id] = activity_wise_measurements

        return measurements

    @staticmethod
    def enrich(df):
        length = len(df)
        edf = df.set_index('enabled').assign(change=1, orig=range(length))
        cdf = df.set_index('completed').assign(change=-1, orig=range(length))
        conc = pd.concat([edf, cdf]).sort_index(kind='mergesort')

        def keywise_cumsum(key):
            col = pd.Series(index=df.index, dtype='int64')
            vals = sorted(set(df[key]))
            for v in vals:
                df_masked = conc[(conc[key] == v)]
                concurrent_on_completion = df_masked['change'].cumsum().loc[df_masked['change'] == -1]
                col.loc[df_masked.loc[df_masked['change'] == -1, 'orig']] = concurrent_on_completion.values
            return col

        a_col = keywise_cumsum('activity')
        r_col = keywise_cumsum('resource')

        pair_col = pd.Series(index=df.index, dtype='int64')
        sizes = df.groupby(['activity', 'resource']).size()
        combinations = sizes[sizes > 0].to_dict()
        for (a, r) in combinations:
            df_masked = conc[(conc['activity'] == a) & (conc['resource'] == r)]
            concurrent_on_completion = df_masked['change'].cumsum().loc[df_masked['change'] == -1]
            pair_col.loc[df_masked.loc[df_masked['change'] == -1, 'orig']] = concurrent_on_completion.values

        return df.assign(concurrent_by_activity=a_col, concurrent_by_resource=r_col, concurrent_by_combination=pair_col)

    @property
    def measurements_df(self):
        if self._measurements_df is None:
            self._measurements_df = self.generate_measurements_df()
        return self._measurements_df

    def generate_measurements_df(self):
        rows = []
        for case_id, case_measurements in self.measurements_dict.items():
            for a, activity_measurements in case_measurements.items():
                for measurement in activity_measurements:
                    rows.append([case_id, a, measurement.resource, measurement.enabled, measurement.completed,
                                 measurement.durations.total, measurement.durations.delay,
                                 measurement.durations.wait, measurement.durations.service])
        df = pd.DataFrame(rows, columns=['case_id', 'activity', 'resource', 'enabled', 'completed', 'total', 'delay',
                                         'wait', 'service'])
        df['activity'] = df['activity'].astype('category', copy=False)
        df['resource'] = df['resource'].astype('category', copy=False)
        df['total_seconds'] = df['total'].dt.total_seconds()
        return TraceTracker.enrich(df)

    def get_activity_wise_total_durations(self):
        dic = defaultdict(list)
        for case_measurements in self.measurements_dict.values():
            for a, activity_measurements in case_measurements.items():
                for measurement in activity_measurements:
                    dic[a].append(measurement.durations.total)

        return {a: pd.Series(vals) for a, vals in dic.items()}

    def impute(self, guess_function=None):
        if guess_function is None:
            def guess_function(activity, enabled, completed, total_duration):
                return enabled, completed

        new_order = []

        def make_event(activity, time, resource):
            return {xes_const.DEFAULT_NAME_KEY: activity,
                    xes_const.DEFAULT_TIMESTAMP_KEY: time,
                    xes_const.DEFAULT_RESOURCE_KEY: resource}

        for case_id, trace in self.history.items():
            activity_measurements = self.measurements_dict[case_id]

            activity_occurrence_counts = defaultdict(int)
            for i, (activity, lifecycle, event) in enumerate(trace):
                measurement = activity_measurements[activity][activity_occurrence_counts[activity]]
                typ = self.available_lifecycle_map[activity]
                time = time_utils.get_event_timestamp(event)
                new_order.append((case_id, time, activity, lifecycle, event))
                if typ == AvailableLifecycles.ScheduleStartComplete:
                    pass
                elif typ == AvailableLifecycles.StartComplete:
                    if lifecycle == Lifecycle.Enabled:
                        t = measurement.durations.total
                        schedule_time, _ = guess_function(activity, measurement.enabled, measurement.completed, t)
                        new_order.append((case_id, schedule_time, activity, Lifecycle.Scheduled,
                                          make_event(activity, schedule_time, measurement.resource)))
                elif typ == AvailableLifecycles.CompleteOnly:
                    if lifecycle == Lifecycle.Enabled:
                        t = measurement.durations.total
                        schedule_time, start_time = guess_function(activity, measurement.enabled, measurement.completed,
                                                                   t)
                        new_order.append((case_id, schedule_time, activity, Lifecycle.Scheduled,
                                          make_event(activity, schedule_time, measurement.resource)))
                        new_order.append(
                            (case_id, start_time, activity, Lifecycle.Started,
                             make_event(activity, start_time, measurement.resource)))

                if lifecycle == Lifecycle.Completed:
                    activity_occurrence_counts[activity] += 1

        new_order.sort(key=lambda tup: tup[0])

        return new_order

    def re_replay(self, guess_function=None) -> (Dict[str, ActivityTracker], ResourcePool):

        new_order = self.impute(guess_function)

        resource_pool = ResourcePool()
        activity_trackers = {label: ActivityTracker(resource_pool) for label, lifecycle_availability in
                             self.available_lifecycle_map.items()}

        for (case_id, time, activity, lifecycle, event) in new_order:
            tracker = activity_trackers[activity]
            tracker.track(case_id, lifecycle, event)

        return activity_trackers, resource_pool
