#!/bin/bash

echo 'Setting smartscope environment'
#General
export ALLOWED_HOSTS=localhost,lxd-02012614
export DJANGO_SETTINGS_MODULE=Smartscope.settings.server_singularity
export USE_STORAGE=True
export USE_LONGTERMSTORAGE=True
export USE_AWS=False
export USE_MICROSCOPE=True
export DEFAULT_UMASK=003
export LOGLEVEL=DEBUG

#SerialEM variables
export SEM_PYTHON=False
export NO_TEM_TESTMODE=True
export TEST_FILES=/mnt/data/tmp/scope/smartscope_testfiles/

#Database
export MYSQL_HOST=localhost
export MYSQL_PORT=10500
export MYSQL_USERNAME=root
export MYSQL_ROOT_PASSWORD=
export DB_NAME=smartscope_beta
export DB_PATH=/mnt/mariadb

#Cache
export REDIS_HOST=127.0.0.1
export REDIS_PORT=7780

#AWS
export AWS_STORAGE_BUCKET_NAME=
export AWS_DATA_PREFIX=data
export AWS_S3_REGION_NAME=us-east-1
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
