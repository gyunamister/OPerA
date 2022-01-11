from datetime import datetime, timedelta, time, date
from enum import IntEnum

import dateutil.tz
import pandas as pd
from dateutil.relativedelta import relativedelta
from pm4py.util import xes_constants

Weekdays = IntEnum('Weekdays', 'Monday Tuesday Wednesday Thursday Friday Saturday Sunday', start=0)


def get_tz():
    return dateutil.tz.tzutc()


def get_event_timestamp(event):
    return make_timezone_aware(event[xes_constants.DEFAULT_TIMESTAMP_KEY])  # TODO FIXXxx


def add(dt: datetime, delta: timedelta):
    res = dt + delta
    return res.astimezone(dt.tzinfo)  # dateutil.tz.resolve_imaginary(res)


def subtract(dt: datetime, delta: timedelta):
    res = dt - delta
    return res.astimezone(dt.tzinfo)  # dateutil.tz.resolve_imaginary(res)


def add_relative(dt: datetime, rt: relativedelta):
    # TODO never have I seen something more ugly
    # caused by apparent pd.Timestamp + relativedelta incompatibility
    temp = dt
    if isinstance(dt, pd.Timestamp):
        temp = dt.to_pydatetime()
    res = pd.Timestamp(temp + rt)
    imaginary = dateutil.tz.resolve_imaginary(res)
    return imaginary


def next_day(dt: datetime):
    return add_relative(dt, relativedelta(days=1, hour=0, minute=0, second=0, microsecond=0))


def set_time(dt: datetime, t: time) -> datetime:
    res = pd.Timestamp(datetime.combine(dt.date(), t, dt.tzinfo))
    imaginary = dateutil.tz.resolve_imaginary(res)
    return imaginary


def tests():
    ber = dateutil.tz.gettz('Europe/Berlin')
    pre_dst = datetime(2020, 10, 25, 1, 0, tzinfo=ber)
    assert add(pre_dst, timedelta(hours=3)) == datetime(2020, 10, 25, 3, 0, tzinfo=ber)
    assert next_day(pre_dst) == datetime(2020, 10, 26, tzinfo=ber)
    assert add_relative(pre_dst, relativedelta(days=1)) == datetime(2020, 10, 26, 1, 0, tzinfo=ber)
    assert add_relative(pre_dst, relativedelta(hours=24)) == datetime(2020, 10, 26, 0, 0, tzinfo=ber)


def now():
    return datetime.now(tz=dateutil.tz.gettz('Europe/Berlin'))


def filenameable_timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def duration_between_times(start, end):
    return datetime.combine(date(2020, 4, 28), end) - datetime.combine(date(2020, 4, 28), start)


def make_timezone_aware(dt: datetime):
    if dt.tzinfo is None:
        return datetime.astimezone(dt)
    else:
        return dt
