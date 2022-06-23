export OPERA_PATH="/Users/gyunam/Documents/DigitalTwin/"
# export OCPA_PATH="/Users/gyunam/Documents/ocpa-core"
dtween_path=$OPERA_PATH
ocpa_path=$OCPA_PATH

export PYTHONPATH="${dtween_path}/src/:${ocpa_path}:$PYTHONPATH"


export REDIS_LOCALHOST_OR_DOCKER=localhost
export LOCALHOST_OR_DOCKER=localhost

cd "${dtween_path}/src/backend/"
chmod +x ./run_celery.sh 

cd "${dtween_path}/src/backend/tasks" || exit
celery -A tasks worker --loglevel=DEBUG
