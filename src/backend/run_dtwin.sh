#!/bin/zsh

path="$DTWIN_PATH"

export PYTHONPATH="${path}/src/backend/:${path}/src/:$PYTHONPATH"

export REDIS_LOCALHOST_OR_DOCKER=localhost
export LOCALHOST_OR_DOCKER=localhost

cd "${path}/src/backend" || exit
python index.py
