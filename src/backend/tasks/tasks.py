from time import sleep
from typing import Dict, List, Union, Any, Tuple, Optional

import pandas as pd
import os


from backend.param.available import AvailableCorrelationsExt, get_available_from_name
from backend.param.constants import CSV, JOBS_KEY, JOB_TASKS_KEY
from backend.param.settings import CeleryConfig, redis_pwd
from celery import Celery
from celery.result import AsyncResult
from dtween.digitaltwin.digitaltwin.objects.factory import get_digital_twin
from ocpa.objects.log.importer.mdl import factory as mdl_import_factory
from ocpa.algo.discovery.ocpn import algorithm as discovery_factory
from ocpa.algo.conformance.token_based_replay import algorithm as diagnostics_factory
from ocpa.objects.log.obj import ObjectCentricEventLog
from ocpa.objects.log.importer.ocel.versions import import_ocel_json
from ocpa.algo.enhancement.token_replay_based_performance import algorithm as performance_factory
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


redis_host = os.getenv('REDIS_LOCALHOST_OR_DOCKER')
db = redis.StrictRedis(host=redis_host, port=6379, password=redis_pwd, db=0)

# db = redis.StrictRedis(host='localhost', port=6379, password=redis_pwd, db=0)

db.keys()
celery = Celery('dtween.worker',
                )
celery.config_from_object(CeleryConfig)

localhost_or_docker = os.getenv('LOCALHOST_OR_DOCKER')


# celery.conf.update({'CELERY_ACCEPT_CONTENT': ['pickle']})


@celery.task(bind=True, serializer='pickle')
def store_redis_backend(self, data: Any) -> Any:
    store_redis(data, self.request)


@celery.task(bind=True, serializer='pickle')
def parse_data(self, data, data_type, parse_param) -> ObjectCentricEventLog:
    # Dirty fix for serialization of parse_param to celery seem to change the values always to False
    if data_type == CSV:
        ocel = mdl_import_factory.apply(
            data, variant="to_obj", parameters=parse_param)
        store_redis(ocel, self.request)
    else:
        store_redis(import_ocel_json.parse_json(
            data), self.request)


@celery.task(bind=True, serializer='pickle')
def build_digitaltwin(self, data):
    df = mdl_import_factory.apply(data)
    ocpn = discovery_factory.apply(df)

    dt = get_digital_twin(ocpn)
    store_redis(dt, self.request)


@celery.task(bind=True, serializer='pickle')
def discover_ocpn(self, data):
    ocpn = discovery_factory.apply(data)
    store_redis(ocpn, self.request)


@celery.task(bind=True, serializer='pickle')
def analyze_opera(self, ocpn, data, parameters):
    diagnostics = performance_factory.apply(
        ocpn, data, parameters=parameters)
    store_redis(diagnostics, self.request)


@celery.task(bind=True, serializer='pickle')
def generate_diagnostics(self, ocpn, data, start_date=None, end_date=None):
    # if start_date != "" and end_date != "":
    #     # start_date = parser.parse(start_date).date()
    #     # end_date = parser.parse(end_date).date()
    #     # end_date += datetime.timedelta(days=1)
    #     data = data.loc[(data["event_timestamp"] > pd.datetime(start_date))
    #                     & (data["event_timestamp"] < pd.Timestamp(end_date))]
    #     print("Events are filtered: {} - {}".format(start_date, end_date))
    diagnostics = diagnostics_factory.apply(ocpn, data)
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
