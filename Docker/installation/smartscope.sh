#! /bin/bash
[ -n "$1" ] && argument=$1 || {
    echo -n "Enter start, stop: "
    read argument
}
cd $(dirname "$(readlink -f "$0")")

export UID=$(id -u)
export GID=$(id -g)

if [ "$argument" = "start" ]; then
    echo "Starting smartscope"
    docker compose -f docker-compose.yml -f smartscope.yml up -d
elif [ "$argument" = "stop" ]; then
    echo "Stopping smartscope"
    docker compose down
fi
