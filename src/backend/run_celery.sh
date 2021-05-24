#!/bin/zsh

path="$DTWIN_PATH"

export PYTHONPATH="${path}/src/:$PYTHONPATH"


export REDIS_LOCALHOST_OR_DOCKER=localhost
export LOCALHOST_OR_DOCKER=localhost

echo $PYTHONPATH

cd "${path}/src/backend/tasks" || exit
celery -A tasks worker --loglevel=DEBUG
