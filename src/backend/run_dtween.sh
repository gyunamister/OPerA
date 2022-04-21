export DTWEEN_PATH="/Users/gyunam/Documents/DigitalTwin/"
# export OCPA_PATH="/Users/gyunam/Documents/ocpa-core"
dtween_path=$DTWEEN_PATH
# ocpa_path=$OCPA_PATH

export PYTHONPATH="${dtween_path}/src/:${ocpa_path}:$PYTHONPATH"


export REDIS_LOCALHOST_OR_DOCKER=localhost
export LOCALHOST_OR_DOCKER=localhost

cd "${dtween_path}/src/backend/"
chmod +x ./run_dtween.sh 

cd "${dtween_path}/src/backend" || exit
python index.py
