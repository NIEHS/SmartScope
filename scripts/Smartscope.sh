#!/bin/bash

# Start the database, nginx and web server
[ -n "$1" ] && argument=$1 || {
    echo -n "Enter start, stop or restart: "
    read argument
}
[ -n "$2" ] && dev=$2 || dev=false

# source /data1/conda.bashrc


cd $(dirname "$(readlink -f "$0")")
pwd
echo 'Setting smartscope environment'
set -a
. ../conf.env
set +a

source $CONDA_INSTALL/activate smartscope
DIR=$CONDA_PREFIX/var/run
umask $DEFAULT_UMASK


check_if_running() {
    IS_DB=false
    IS_DJANGO=false
    IS_WEB=false
    if [ "$MYSQL_HOST" = "localhost" ] && [ $MYSQL_IN_ENV = true ]; then
        if test -f "$DIR/mysql.pid"; then
            echo "Database is already running."
            IS_DB=true
        else
            echo "Database is not running."
        fi
        start_or_stop_db
    fi
    if test -f "$DIR/django.pid"; then
        echo "Smartscope is already running."
        IS_DJANGO=true
    else
        echo "Smartscope is not running."
    fi
    start_or_stop_app
    if test -f "$DIR/nginx.pid"; then
        echo "Web server is already running."
        IS_WEB=true
    else
        echo "Web server is not running."
    fi
    start_or_stop_web
}

start_or_stop_db() {
    if [ $stop = true ] && [ $IS_DB = true ]; then
        echo "Stopping Database"
        nohup mysqladmin --defaults-file=$CONDA_PREFIX/etc/my.cnf -u $MYSQL_USERNAME -p$MYSQL_ROOT_PASSWORD shutdown>/dev/null 2>&1
        IS_DB=false
    fi
    if [ $start = true ] && [ $IS_DB = false ]; then
        echo "Starting Database"
        cd $CONDA_PREFIX
        nohup $CONDA_PREFIX/bin/mysqld_safe --defaults-file=$CONDA_PREFIX/etc/my.cnf >/dev/null 2>&1 &
    fi
}

start_or_stop_app() {
    if [ $stop = true ] && [ $IS_DJANGO = true ]; then
        if [ $dev = false ]; then
            printf "Stopping Smartscope"
            kill $(cat $DIR/django.pid)
            while test -f "$DIR/django.pid"
                do
                printf "."
                sleep 1 # or less like 0.2
                done
            printf "Done\n"
            IS_DJANGO=false
        else
            echo "Stopping Development Smartscope"
            pkill -f runserver
            rm $DIR/django.pid
            IS_DJANGO=false
        fi

    fi
    if [ $start = true ] && [ $IS_DJANGO = false ]; then

        if [ $dev = false ]; then
            printf "Starting Smartscope"
            uwsgi --ini $APP/Smartscope-server/autoscreenServer/smartscope.ini &
            while [ $IS_DJANGO = false ]
                do
                if test -f "$DIR/django.pid"; then
                    IS_DJANGO=true
                fi
                printf "."
                sleep 1 # or less like 0.2
                done
            printf "Done\n"
        else
            echo "Starting Development Smartscope"
            cd $APP/Smartscope-server
            python manage.py runserver >$CONDA_PREFIX/var/log/django_dev.log &
            echo $! >$CONDA_PREFIX/var/run/django.pid
        fi

    fi
}

start_or_stop_web() {
    if [ $stop = true ] && [ $IS_WEB = true ]; then
        echo "Stopping Web Server"
        kill -INT $(cat $DIR/nginx.pid)
        while test -f "$DIR/nginx.pid"
            do
            printf "."
            sleep 1 # or less like 0.2
            done
        printf "Done\n"
        IS_WEB=false
    fi
    if [ $start = true ] && [ $IS_WEB = false ]; then

        if [ $dev = false ]; then
            echo "Starting Web Server"
            envsubst '$CONDA_PREFIX $APP $AUTOSCREENSTORAGE $AUTOSCREENDIR' <$APP/Template_files/smartscope.template >$CONDA_PREFIX/etc/nginx/sites.d/smartscope.conf
            nginx &
            while [ $IS_WEB = false ]
                do
                if test -f "$DIR/nginx.pid"; then
                    IS_WEB=true
                fi
                printf "."
                sleep 1 # or less like 0.2
                done
            printf "Done\n"
        else
            echo "Starting Developement Web Server"
            envsubst '$APP $AUTOSCREENSTORAGE $AUTOSCREENDIR' <$APP/Template_files/smartscope-dev.template >$CONDA_PREFIX/etc/nginx/sites.d/smartscope.conf
            nginx &
        fi
        

    fi
}

start=false
stop=false
if [ "$argument" = "start" ]; then
    echo "Starting server"
    start=true
elif [ "$argument" = "stop" ]; then
    echo "Stopping server"
    stop=true
elif [ "$argument" = "restart" ]; then
    echo "Restarting server"
    start=true
    stop=true
fi

check_if_running
