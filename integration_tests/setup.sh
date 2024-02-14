#!/bin/sh

set -e

echo "Preparing test..."
docker compose up -d

echo "Sleeping..."
sleep 10
echo "Continuing!"

docker cp .. ${FRDR_FORWARDER_CONTAINER_NAME:-forwarder}:/home/jenkins/

docker exec ${FRDR_FORWARDER_CONTAINER_NAME:-forwarder} bash -c 'scl enable rh-python38 -- python -m pip install --user -r forwarder/requirements.txt'
docker exec ${FRDR_FORWARDER_CONTAINER_NAME:-forwarder} bash -c 'scl enable rh-python38 -- python -m pip install --user pytest'

echo "Preparation completed!"
