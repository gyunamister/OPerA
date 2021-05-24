import datetime
from time import sleep
from typing import Dict, List, Union, Any, Tuple, Optional

import numpy as np
import pandas as pd
import os
import itertools
from dateutil import parser


from backend.param.available import AvailableCorrelationsExt, get_available_from_name
from backend.param.constants import CSV, AGGREGATOR, CONTEXT_KEY, INCLUDES_KEY, GUIDES_KEY, JOBS_KEY, JOB_TASKS_KEY, \
    METHODS_KEY, negative_context, tid_t, group_t, DEFAULT_TOP, \
    column_names, high_t, bord_ps, bord_ng, LOCATION, RESOURCE
from backend.param.settings import CeleryConfig, redis_pwd
from celery import Celery
from celery.result import AsyncResult
from dtwin.available.available import AvailableCorrelations
from dtwin.parsedata.objects.ocdata import ObjectCentricData, sort_events
from dtwin.parsedata.objects.oclog import ObjectCentricLog, Trace
from dtwin.parsedata.parse import parse_csv, parse_json
from dtwin.digitaltwin.digitaltwin.objects.factory import get_digital_twin
from dtwin.digitaltwin.ocel.objects.mdl.importer import factory as mdl_import_factory
from dtwin.digitaltwin.ocpn.discovery import algorithm as discovery_factory
from dtwin.digitaltwin.diagnostics import algorithm as diagnostics_factory
import pickle
import redis

# The time in seconds a callback waits for a celery task to get ready
CELERY_TIMEOUT = 21600


def user_log_key(user, log_hash):
    return f'{user}-{log_hash}'


def results_key(task_id):
    return f'result-{task_id}'


def store_redis(data, task):
    key = results_key(task.id)
    pickled_object = pickle.dumps(data)
    db.set(key, pickled_object)


db = redis.StrictRedis(host='localhost', port=6379, password=redis_pwd, db=0)

db.keys()
celery = Celery('dtwin.worker',
                )
celery.config_from_object(CeleryConfig)

localhost_or_docker = os.getenv('LOCALHOST_OR_DOCKER')


# celery.conf.update({'CELERY_ACCEPT_CONTENT': ['pickle']})


@celery.task(bind=True, serializer='pickle')
def store_redis_backend(self, data: Any) -> Any:
    store_redis(data, self.request)


@celery.task(bind=True, serializer='pickle')
def parse_data(self, data, data_type, parse_param, resource, location) -> ObjectCentricData:
    # Dirty fix for serialization of parse_param to celery seem to change the values always to False
    if resource:
        parse_param.vmap_availables[RESOURCE] = True
    if location:
        parse_param.vmap_availables[LOCATION] = True
    if data_type == CSV:
        store_redis(parse_csv(data, parse_param), self.request)
    else:
        store_redis(parse_json(data, parse_param), self.request)


@celery.task(bind=True, serializer='pickle')
def correlate_events(self,
                     data: ObjectCentricData,
                     user_ot_selection: List[str],
                     version: str):
    version_ext = get_available_from_name(version,
                                          AvailableCorrelationsExt.INITIAL_PAIR_CORRELATION,
                                          AvailableCorrelationsExt)
    selection = set(user_ot_selection)
    sort_events(data)
    store_redis(version_ext.value[version].call_with_param(
        selection=selection, data=data), self.request)


@celery.task(bind=True, serializer='pickle')
def build_digitaltwin(self, data):
    df = mdl_import_factory.apply(data)
    ocpn = discovery_factory.apply(df)

    dt = get_digital_twin(ocpn)
    store_redis(dt, self.request)


@celery.task(bind=True, serializer='pickle')
def generate_diagnostics(self, ocpn, data, start_date=None, end_date=None):
    df = mdl_import_factory.apply(data)
    if start_date != "" and end_date != "":
        # +1 day to consider the selected end date
        start_date = parser.parse(start_date).date()
        end_date = parser.parse(end_date).date()
        end_date += datetime.timedelta(days=1)
        df = df.loc[(df["event_timestamp"] > pd.Timestamp(start_date))
                    & (df["event_timestamp"] < pd.Timestamp(end_date))]
        print("Events are filtered: {} - {}".format(start_date, end_date))
    diagnostics = diagnostics_factory.apply(ocpn, df)
    print("Diagnostics generated: {}".format(diagnostics))
    store_redis(diagnostics, self.request)


def get_remote_data(user, log_hash, jobs, task_type, length=None):
    if jobs is not None and log_hash in jobs[JOBS_KEY] and task_type in jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY]:
        task = get_task(jobs, log_hash, task_type)
        task.forget()
        timeout = 0
        key = results_key(get_task_id(jobs, log_hash, task_type))
        while not db.exists(key):
            sleep(1)
            timeout += 1
            if timeout > CELERY_TIMEOUT:
                return None
            if task.failed():
                return None
        return pickle.loads(db.get(key))
    else:
        if length is not None:
            return tuple([None] * length)
        else:
            return None


def get_task(jobs, log_hash, task_type):
    task = AsyncResult(id=get_task_id(jobs, log_hash, task_type), app=celery)
    return task


def get_task_id(jobs, log_hash, task_type):
    return jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][task_type]


if __name__ == '__main__':
    celery.worker_main()
