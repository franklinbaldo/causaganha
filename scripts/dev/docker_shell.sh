#!/usr/bin/env bash
# Start development shell inside the Docker container
set -e

docker-compose run --rm app "$@"
