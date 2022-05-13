# Singularity enviroment configuration file

This section explains how to set up the configuration file for singularity.

This file is located in Smartscope/config/singularity/env-template.sh and contains the environment variables necessary for running SmartScope.

The template file should be copied as `env.sh` in the same directory. This is the file that will be read.

The file looks likes the following. Each variable is described below.
```bash
#General
export ALLOWED_HOSTS=localhost
export DJANGO_SETTINGS_MODULE=Smartscope.settings.server_singularity
export USE_STORAGE=True
export USE_LONGTERMSTORAGE=False
export USE_AWS=False
export USE_MICROSCOPE=True
export WORKER_HOSTNAME=localhost
export DEFAULT_UMASK=003
export LOGLEVEL=DEBUG

#SerialEM variables
export SEM_IP=192.168.0.32
export SEM_PORT=48888
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

#Microscope
export WINDRIVE=X:\\auto_screening\

#AWS
export AWS_STORAGE_BUCKET_NAME=
export AWS_DATA_PREFIX=data
export AWS_S3_REGION_NAME=us-east-1
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
```

### General

* ALLOWED_HOSTS *Default: localhost*
    Comma separated list of hostsnames that are allowed to be used to connect to the server.
    *e.g.* locahost,myhostname,mydomain.com,

* DJANGO_SETTINGS_MODULE *Default: Smartscope.settings.server_singularity*
    Useful to change if an instance will only be used as a worker.
    More details coming soon.

* USE_STORAGE *Default: True*
    *options: True|False*
    If the instance should look in the main storage area for files. This option is required if the instance is connected to the microscope.
    Can be turned off if setting up an instance that can only view the results from other sources like a server that would only load files from AWS or long-term storage areas.
    This sotrage location is prioritized to load the files from as it should be the fastest accessible drive.

* USE_LONGTERMSTORAGE *Default: False*
    *options: True|False*
    If you plan on backing up the storage drive to another area with more storage space, the server can look for files in that area for displaying on the website.
    This storage area has second priority to load the files from if the data isn't present in the main storage any longer.

* USE_AWS *Default: False*
    *options: True|False*
    If true, the AWS section of the file will need to be filled up. SmartScope will automatically back up the data for each specimen once they're completed. The data can be loaded from AWS to display on the webpage after it's been removed from the main storage.
    This area has third priority to load the files from.

* USE_MICROSCOPE *Default: True*
    *options: True|False*
    If the instance of Smartscope being deployed is only going to serve as a viewing server that doesn't connect to the microscope, set to False. It will disable the links to setup and run sessions.

* WORKER_HOSTNAME *Default: localhost*
    If the webserver and worker (instance connected to the microscope) are not installed in the same computer.
    More details coming soon.

* DEFAULT_UMASK *Default: 003*
    Set the way the permissions will be set on the files created by smartscope. With umask 003, the files will inherit a 774 (rwxrwxr--) permission set allowing group write.

* LOGLEVEL *Default=INFO*
    *options: INFO|DEBUG*
    Set the sensitivity of logging. The default is INFO will print the most informative status updates while debug allows for more in-depth information.

### SerialEM-related variables

* SEM_IP *Default:192.168.0.32*
    The IP address of the SerialEM computer

* SEM_PORT *Default:48888*
    The SerialEM python port from the SerialEM configuration

* SEM_PYTHON *Default:True*
    Whether SmartScope will try to connect to SerialEM to run a session. Useful to turn off when testing in "fake scope" mode

* NO_TEM_TESTMODE *Default:False*
    To turn on "fake scope" mode. The SEM_PYTHON option needs to also be turned off to take effect.

* TEST_FILES *Default:/mnt/data/tmp/smartscope_testfiles/*
    The location of the dummy files to run in "fake scope" mode.

### Database
* MYSQL_HOST *Default:localhost*
    IP address or hostname of the database server.

* MYSQL_PORT *Default:10500*
    Port for the mysql server. 10500 is the default if using a dabaster from SmartScope singularity container. The actual default for mariabDB is 3306.

* MYSQL_USERNAME *Default:root*
    Username for the mariaDB connection

* MYSQL_ROOT_PASSWORD *Default:*
    Password for the user for mariaDB connection

* DB_NAME *Default:smartscope*
    Name of the database in the mariaDB server

* DB_PATH *Default:/mnt/mariadb*
    Path of the database. Only useful if MYSQL_HOST=localhost

### Microscope
* WINDRIVE *Default: "X:\\\auto_screening\\\"*
    The path where the SmartScope files will be saved on the SerialEM computer

### AWS connection information
This section is required if the USE_AWS=True and if the information is not stored in ~/.aws
Please view [AWS S3](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) information on these variables


