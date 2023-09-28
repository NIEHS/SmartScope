#! /bin/bash

helpText () {
    OPTIONS="
Usage: $(basename $0) \e[3msubcommand [command]\e[0m

Subcommand              DESCRIPTION
==========              ===========
start                   Start SmartScope
stop                    Stop smartscope
run \e[3mcommand\e[0m             Run a smartscope command in the smartscope container
exec \e[3mcommand\e[0m            Run any shell command in the smartscope container
python                  Runs an interactive ipython shell inside the smartscope container
"
    echo -e "$OPTIONS"
}

[ -n "$1" ] && argument=$1 || {
    helpText
    exit 1
}
cd $(dirname "$(readlink -f "$0")")

case $argument in
    start)
        export UID=$(id -u)
        export GID=$(id -g)
        echo "Starting smartscope"
        docker compose -f docker-compose.yml -f smartscope.yml up -d ;;
    stop)
        echo "Stopping smartscope"
        docker compose down ;;
    run)
        cmd="docker compose exec smartscope smartscope.py ${@:2}"
        echo -e "Executing command inside the smartscope container:
    \e[3m$cmd\e[0m"
        exec $cmd;;
    help|-h|--help)
        helpText;;
    python)
        echo "Running a python shell inside the smartscope container"
        docker compose exec -it smartscope manage.py shell -i ipython ;;
    exec)
        echo "Executing shell command inside the smartscope container:"
        docker compose exec -it smartscope ${@:2};;
    *)
        echo Unkown command error: $argument
        helpText
        exit 1;;
esac

