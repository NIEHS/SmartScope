#!/bin/bash

echo 'Setting smartscope environment'
#General
export ALLOWED_HOSTS=localhost
export DJANGO_SETTINGS_MODULE=Smartscope.settings.server_singularity
export USE_STORAGE=True
export USE_LONGTERMSTORAGE=False
export USE_AWS=False
export USE_MICROSCOPE=True
export DEFAULT_UMASK=003
export LOGLEVEL=DEBUG

#SerialEM variables
export SEM_PYTHON=True
export NO_TEM_TESTMODE=False
export TEST_FILES=/mnt/data/tmp/smartscope_testfiles/

#Database
export MYSQL_HOST=localhost
export MYSQL_PORT=10500
export MYSQL_USERNAME=root
export MYSQL_ROOT_PASSWORD=
export DB_NAME=smartscope
export DB_PATH=/mnt/mariadb

#AWS
export AWS_STORAGE_BUCKET_NAME=
export AWS_DATA_PREFIX=data
export AWS_S3_REGION_NAME=us-east-1
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
