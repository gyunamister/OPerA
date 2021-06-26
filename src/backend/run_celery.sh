
path="$DTWEEN_PATH"

export PYTHONPATH="${path}/src/:$PYTHONPATH"


export REDIS_LOCALHOST_OR_DOCKER=localhost
export LOCALHOST_OR_DOCKER=localhost

cd "${path}/src/backend/tasks" || exit
celery -A tasks worker --loglevel=DEBUG
