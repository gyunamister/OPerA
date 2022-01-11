from __future__ import annotations

import heapq
import logging
import random
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Any, List, Optional
from typing import TYPE_CHECKING
import time
import sys

import pandas as pd

import sim.case
import sim.parameter_implementations as pimpls
import sim.utils
from sim import time_utils

if TYPE_CHECKING:
    import sim.model_parameters as params
    import sim.sim_model as smodel


# TODO all unsafe_hash classes should be immutable 'frozen'
@dataclass(unsafe_hash=True)
class Event:
    pass


@dataclass(unsafe_hash=True)
class UpdateEvent(Event):
    pass


@dataclass(unsafe_hash=True)
class ProcessingCompletionEvent(UpdateEvent):
    case: sim.case.OCCase
    resource: smodel.ResourceModel
    case_event: sim.case.OCCaseEvent


@dataclass(unsafe_hash=True)
class CaseDelayedEvent(UpdateEvent):
    case: sim.case.OCCase


@dataclass(unsafe_hash=True)
class DictUpdateEvent(UpdateEvent):
    key: Any
    new_value: Any


@dataclass(unsafe_hash=True)
class BusinessHourEvent(DictUpdateEvent):

    def __init__(self, new_state: bool) -> None:
        super(BusinessHourEvent, self).__init__(
            key='in_business', new_value=new_state)


@dataclass(unsafe_hash=True)
class CaseCreationEvent(UpdateEvent):
    case: sim.case.OCCase


@dataclass(unsafe_hash=True)
class CaseArrivalEvent(UpdateEvent):
    source: str
    arrival_number: int


class Updatable:

    def __init__(self, **kwargs) -> None:
        super(Updatable, self).__init__(**kwargs)

    @abstractmethod
    def receive_event(self, event: UpdateEvent):
        pass


class UpdateSource:

    def __init__(self, **kwargs) -> None:
        super(UpdateSource, self).__init__(**kwargs)
        self.clients: List[Updatable] = []

    @property
    def has_clients(self):
        return len(self.clients) > 0

    def add_client(self, client: Updatable) -> None:
        self.clients.append(client)

    def remove_client(self, client: Updatable) -> None:
        if client in self.clients:
            self.clients.remove(client)

    def update_clients(self, event: UpdateEvent):
        for client in self.clients:
            client.receive_event(event)


@sim.utils.auto_str
class Callback(Event):

    def __init__(self, callback_method: Callable[..., None], payload_event: Optional[Event] = None) -> None:
        self.callback_method = callback_method
        self.payload_event = payload_event

    def activate(self):
        if self.payload_event is None:
            self.callback_method()
        else:
            self.callback_method(self.payload_event)

    def __hash__(self) -> int:
        return hash((self.callback_method, self.payload_event))

    def __eq__(self, o: object) -> bool:
        return isinstance(o,
                          Callback) and self.callback_method == o.callback_method and self.payload_event == o.payload_event


@sim.utils.auto_str
class TimedCallback(Callback):

    def __init__(self, dt: datetime, callback_method: Callable[..., None],
                 payload_event: Optional[Event] = None) -> None:
        super(TimedCallback, self).__init__(callback_method, payload_event)
        self.time = time_utils.make_timezone_aware(dt)

    def __hash__(self) -> int:
        return hash((self.time, self.callback_method, self.payload_event))

    def __eq__(self, o: object) -> bool:
        return isinstance(o, TimedCallback) and super(TimedCallback, self).__eq__(o) and self.time == o.time

    def __le__(self, other) -> bool:
        return self.time.__le__(other.time)

    def __lt__(self, other):
        return self.time.__lt__(other.time)


class EventQueue:

    def __init__(self) -> None:
        self.__queue = []
        self.__global_time = None
        self.event_in_counter = 0
        self.event_out_counter = 0
        self.queued_callbacks = set()
        self.end_of_timestep_tasks = set()
        self.pause = None
        self.pause_step = None
        self.pause_length = None

    @property
    def global_time(self) -> datetime:
        return self.__global_time

    @global_time.setter
    def global_time(self, value: datetime):
        value = time_utils.make_timezone_aware(value)
        if type(value) is not pd.Timestamp:
            value = pd.Timestamp(value)
        assert self.__global_time is None or value >= self.__global_time
        if self.__global_time and value > self.__global_time:
            logging.info(
                f'############# time shifts from {self.__global_time} to {value}')
        self.__global_time = value

    def offer_immediate(self, callback: Callback):
        self.offer(TimedCallback(self.global_time,
                   callback.callback_method, callback.payload_event))

    def offer_delayed(self, delta: timedelta, callback: Callback):
        assert delta >= timedelta(0)  # assert positive
        self.offer(
            TimedCallback(time_utils.add(self.global_time, delta), callback.callback_method, callback.payload_event))

    def offer_at(self, dt: datetime, callback: Callback):
        # in case the offered date lies in the past
        dt = time_utils.make_timezone_aware(dt)
        self.offer(TimedCallback(max(self.global_time, dt),
                   callback.callback_method, callback.payload_event))

    def offer(self, timed_callback: TimedCallback):
        if timed_callback not in self.queued_callbacks:
            heapq.heappush(
                self.__queue, (timed_callback, self.event_in_counter))
            self.event_in_counter += 1
            self.queued_callbacks.add(timed_callback)

    def offer_end_of_timestep_task(self, callback: Callable[[None], ...]):
        self.end_of_timestep_tasks.add(callback)

    def execute_end_of_timestep_tasks(self):
        logging.info('executing current end-of-timestep tasks')
        for callback in self.end_of_timestep_tasks:
            callback()
        self.end_of_timestep_tasks.clear()

    def poll(self) -> TimedCallback:
        if len(self.end_of_timestep_tasks) > 0 and len(self.__queue) == 0:
            return TimedCallback(self.global_time, self.execute_end_of_timestep_tasks)
        elif len(self.__queue) > 0:
            tc = heapq.nsmallest(1, self.__queue)[0][0]
            if len(self.end_of_timestep_tasks) > 0 and tc.time > self.global_time:
                return TimedCallback(self.global_time, self.execute_end_of_timestep_tasks)
            else:
                timed_callback = heapq.heappop(self.__queue)[0]
                self.event_out_counter += 1
                self.queued_callbacks.remove(timed_callback)
                self.global_time = timed_callback.time
                return timed_callback

    def empty(self) -> bool:
        return len(self.__queue) == 0 and len(self.end_of_timestep_tasks) == 0

    def creep_time(self):
        te = heapq.nsmallest(1, self.__queue)[0][0]
        milli_range = min(
            max((te.time - self.global_time).total_seconds() * 1000, 1), 1000)
        delta = random.randint(1, milli_range)
        return time_utils.add(self.global_time, timedelta(milliseconds=delta))

    def step(self) -> None:
        timed_callback = self.poll()
        timed_callback.activate()


class DistributingEventSource(UpdateSource):

    def __init__(self, event_queue: EventQueue, **kwargs) -> None:
        super(DistributingEventSource, self).__init__(**kwargs)
        self.event_queue = event_queue

    def distribute(self, event):
        self.event_queue.offer_immediate(Callback(self.update_clients, event))


class ProliferatingEventSource(UpdateSource):

    def __init__(self, event_queue: EventQueue, **kwargs) -> None:
        super(ProliferatingEventSource, self).__init__(**kwargs)
        self.event_queue = event_queue
        self._paused = False
        self._terminated = False

    def start(self) -> None:
        def actual_start():
            if not (self.is_paused or self.has_terminated):
                self.event_queue.offer_immediate(
                    Callback(self.proliferate, self.initial_event()))

        when = self.initial_time()
        if when is None:
            actual_start()  # TODO could preserve ordering by using offer_immediate, causes another immediate callback however
        else:
            self.event_queue.offer_at(when, Callback(actual_start))

    def stop(self) -> None:
        self._terminated = True

    def initial_time(self) -> Optional[datetime]:
        pass

    def initial_event(self) -> Event:
        pass

    def next_time(self, current_time: datetime) -> datetime:
        pass

    def next_event(self) -> Event:
        pass

    def handle_event(self, event: Event) -> None:
        pass

    def should_terminate(self) -> bool:
        return not self.has_clients

    def force_terminate(self) -> None:
        self.stop()

    @property
    def has_terminated(self):
        return self._terminated

    @property
    def is_paused(self):
        return self._paused

    def pause(self) -> None:
        self._paused = True

    def unpause(self) -> None:
        self._paused = False
        self.start()

    def proliferate(self, event: Event):
        self.handle_event(event)
        should_terminate = self.should_terminate()
        if not (self.has_terminated or self.is_paused or should_terminate):
            next_time = self.next_time(self.event_queue.global_time)
            next_event = self.next_event()
            self.event_queue.offer(TimedCallback(
                next_time, self.proliferate, next_event))
        elif should_terminate:
            self.stop()


class Scheduler(ProliferatingEventSource):

    def __init__(self, event_queue: EventQueue, **kwargs) -> None:
        super(Scheduler, self).__init__(event_queue=event_queue, **kwargs)

    def _update_state(self, event: UpdateEvent) -> None:
        pass

    def handle_event(self, event: UpdateEvent) -> None:
        self._update_state(event)
        self.update_clients(event)


class BusinessHoursScheduler(Scheduler):

    def __init__(self, event_queue: EventQueue, business_hours: params.BusinessHours = pimpls.AlwaysInBusiness,
                 intended_start: datetime = None, **kwargs) -> None:
        super(BusinessHoursScheduler, self).__init__(
            event_queue=event_queue, **kwargs)
        self.bh: params.BusinessHours = business_hours
        self.intended_start = intended_start
        self.in_business: bool = False

    def should_terminate(self) -> bool:
        return super(BusinessHoursScheduler, self).should_terminate() or not self.bh.is_dynamic()

    def initial_time(self) -> Optional[datetime]:
        return self.intended_start

    def initial_event(self) -> Event:
        return BusinessHourEvent(self.bh.in_business(self.event_queue.global_time))

    def _update_state(self, event: BusinessHourEvent) -> None:
        self.in_business = event.new_value

    def next_event(self) -> BusinessHourEvent:
        return BusinessHourEvent(not self.in_business)

    def next_time(self, current_time: datetime) -> datetime:
        return self.bh.next_change(current_time)


class ArrivalProcessScheduler(Scheduler):

    def __init__(self, event_queue: EventQueue, inter_arrival_sampler: params.InterArrivalSampler, label: str = None,
                 current_creation_count=0, creation_count_limit=None, date_limit=None,
                 external_termination_check: Callable[..., bool] = None,
                 **kwargs) -> None:
        super(ArrivalProcessScheduler, self).__init__(
            event_queue=event_queue, **kwargs)
        self.date_limit = date_limit
        self.count_limit = creation_count_limit
        self.external_termination_check = external_termination_check
        self.label = label if label else 'process_0'
        self.inter_arrival_sampler = inter_arrival_sampler
        self.arrival_scheduled_counter = current_creation_count
        self.next_scheduled_arrival = None

    def initial_event(self) -> Event:
        return self.next_event()

    def should_terminate(self) -> bool:
        return super(ArrivalProcessScheduler, self).should_terminate() or (
            (self.count_limit is not None and self.arrival_scheduled_counter >=
             self.count_limit)
            or (self.date_limit is not None and self.event_queue.global_time >= self.date_limit)
            or (self.external_termination_check is not None and self.external_termination_check()))

    def next_event(self) -> Event:
        arrival_event = CaseArrivalEvent(
            self.label, self.arrival_scheduled_counter)
        self.arrival_scheduled_counter += 1
        return arrival_event

    def next_time(self, current_time: datetime) -> datetime:
        delta = self.inter_arrival_sampler.sample(current_time)
        time = time_utils.add(current_time, delta)
        logging.info(
            f'arrival process sampled iat {current_time}, {delta}, {time}')
        self.next_scheduled_arrival = time
        return time


class ScheduledArrivalProcessScheduler(ArrivalProcessScheduler, Updatable):

    def __init__(self, *args, **kwargs) -> None:
        super(ScheduledArrivalProcessScheduler, self).__init__(*args, **kwargs)
        self.scheduler: Scheduler = kwargs.get('scheduler')
        self.pause()

    def stop(self) -> None:
        super(ScheduledArrivalProcessScheduler, self).stop()
        if self.scheduler is not None:
            self.scheduler.remove_client(self)

    def unpause(self) -> None:
        self._paused = False
        if self.next_scheduled_arrival is None or self.next_scheduled_arrival < self.event_queue.global_time:
            self.start()

    def receive_event(self, event: BusinessHourEvent):
        logging.info(
            f'arrival process {"un" if event.new_value else ""}paused')
        if event.new_value:
            self.unpause()
