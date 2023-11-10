#! /bin/bash

readonly cmd_file="dockerCmd.txt"
readonly dockerRepo="ghcr.io/niehs/smartscope"
composeCmd="docker compose"
dockerCmd="docker"

if [ -e "$file_path" ]; then
    read -r dockerCmd < "$cmd_file"
    read -r composeCmd < "$cmd_file"
fi

helpText () {
    OPTIONS="
Usage: $(basename $0) \e[3msubcommand [command]\e[0m

Subcommand              DESCRIPTION
==========              ===========
start                   Start SmartScope
stop                    Stop smartscope
restart                 Restart smartscope
setup                   Setup the smartscope directories
update \e[3mversion\e[0m                 Update smartscope to the specified version. Choices: ['latest','stable'] (default: latest)
run \e[3mcommand\e[0m             Run a smartscope command in the smartscope container
exec \e[3mcommand\e[0m            Run any shell command in the smartscope container
python                  Runs an interactive ipython shell inside the smartscope container
"
    echo -e "$OPTIONS"
}

stop () {
    echo "Stopping smartscope"
    $composeCmd down
}

start () {
    export UID=$(id -u)
    export GID=$(id -g)
    echo "Starting smartscope"
    $composeCmd -f docker-compose.yml -f smartscope.yml up -d
}

promptYesNo () {
    local question=$1
    while true; do
        echo "$question (y/n)"
        read user_input

        if [[ "$user_input" == "y" ]]; then
            return 0  # Return true
        elif [[ "$user_input" == "n" ]]; then
            return 1  # Return false
        else
            echo "Invalid choice. Please enter 'yes' or 'no'."
        fi
    done    
}

checkForUpdates () {
    local version=$1
    echo "Checking for updates to version $version"
    online_sha=$($dockerCmd manifest inspect $dockerRepo:$version | sed -n '/"config": {/,/"digest": "sha256:\([^"]*\)"/s/.*"digest": "sha256:\([^"]*\)".*/\1/p')
    local_sha=$($dockerCmd inspect --format "{{.ID}}" $dockerRepo:$version | cut -d ':' -f 2)
    echo "Online sha: $online_sha
Local sha: $local_sha"
    if [[ "$online_sha" == "$local_sha" ]]; then
        echo "No updates available"

    else
        echo "Updates available"
    fi
}

[ -n "$1" ] && argument=$1 || {
    helpText
    exit 1
}
cd $(dirname "$(readlink -f "$0")")



case $argument in
    start)
        if checkForUpdates 'latest'; then
            echo "A new release is available. Run 'smartscope.sh update latest' to update to the latest version."
        fi        
        if checkForUpdates 'stable'; then
            echo "A new beta version is available. Run 'smartscope.sh update stable' to update to the new beta version."
        fi 
        start;;
    stop)
        stop;;
    restart)
        stop
        sleep 2
        start;;
    run)
        cmd="$composeCmd exec smartscope smartscope.py ${@:2}"
        echo -e "Executing command inside the smartscope container:
    \e[3m$cmd\e[0m"
        exec $cmd;;
    help|-h|--help)
        helpText;;
    python)
        echo "Running a python shell inside the smartscope container"
        $composeCmd exec -it smartscope manage.py shell -i ipython ;;
    exec)
        echo "Executing shell command inside the smartscope container:"
        $composeCmd exec -it smartscope ${@:2};;
    setup)
        echo "Setting up the smartscope directories"
        mkdir -p logs shared/nginx shared/auth shared/smartscope db data backups;;
    update)
        version=${2:-latest}
        echo "Updating smartscope to version: $version"
        if ! thencheckForUpdates $version; then
            echo "No updates available for version: $version"
            exit 0
        fi 

        backupDir="backups/$(date +%Y%m%d)_config_pre_update"
        if promptYesNo "Do you want to back up the database? (Highly recommended)"; then
            echo "Backing up the database. This may take a few minutes."
            $composeCmd exec smartscope smartscope.py backup_db
        fi
        echo "Creating a backup of the configuration in $backupDir"
        mkdir $backupDir
        cp docker-compose.yml smartscope.yml smartscope.conf database.conf smartscope.sh $backupDir
        echo "Pulling updated docker-compose.yml"
        exit 0
        repo_url="https://raw.githubusercontent.com/NIEHS/SmartScope/$version/Docker/SmartScope"
        wget $repo_url/docker-compose.yml
        echo "Pulling docker image"
        $composeCmd pull
        echo "Pulling updated smartscope.sh"
        exec wget $repo_url/smartscope.sh && echo "Files updated, you may now restart smartscope";;

    *)
        echo Unkown command error: $argument
        helpText
        exit 1;;
esac

