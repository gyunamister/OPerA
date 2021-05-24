import os
from dotenv import load_dotenv

load_dotenv()

# app.secret_key = "dtwin"
entity_redis = os.getenv('REDIS_LOCALHOST_OR_DOCKER')
entity_rabbit = os.getenv('RABBIT_LOCALHOST_OR_DOCKER')
rabbit_user = os.getenv('RABBITMQ_USER')
rabbit_pwd = os.getenv('RABBITMQ_PASSWORD')
redis_pwd = 'apm191'


class CeleryConfig:
    # broker_url = 'amqp://' + rabbit_user + ':' + rabbit_pwd + '@' + entity_rabbit + ':5672'
    # celery flower --broker=redis://:apm191@localhost:6379/0
    # redis://guest:guest@localhost:6379/0
    broker_url = f'redis://:{redis_pwd}@{entity_redis}:6379/0'
    result_backend = f'redis://:{redis_pwd}@{entity_redis}:6379/0'
    accept_content = ['pickle']
    result_serializer = 'pickle'
    result_accept_content = ['pickle']
    task_serializer = 'pickle'
    worker_prefetch_multiplier = 1
    task_acks_late = True
    imports = ('backend.tasks.tasks',)
