Complete list of environment variables
######################################

This section explains how to set up the environment variables for SmartScope

General
*******

* ALLOWED_HOSTS *Default: localhost*

    Comma separated list domains that are allowed to be used to connect to the server. Usually, it is the IP an/or hostname of the computer where SmartScope is installed. If you have a domain name.
    *e.g.* locahost,myhostname,mydomain.com

* DJANGO_SETTINGS_MODULE *Default: Smartscope.settings.server_docker*

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

* DEBUG  *Default=True*

    Sets the server in debug mode to return traceback of the error on webpage loading instead of the regular return code.

Fake-scope mode
***************************************

* TEST_FILES *Default:/mnt/data/tmp/smartscope_testfiles/*

    The location of the dummy files to run in "fake scope" mode.

Database
********

* MYSQL_HOST *Default:localhost*

    IP address or hostname of the database server.

* MYSQL_PORT *Default:3306*

    Port for the mysql server. 3306 is the default if the default port for mariabDB.

* MYSQL_USERNAME *Default:root*

    Username for the mariaDB connection

* MYSQL_ROOT_PASSWORD *Default:*

    Password for the user for mariaDB connection

* DB_NAME *Default:smartscope*

    Name of the database in the mariaDB server

* DB_PATH *Default:/mnt/mariadb*

    Path of the database. Only useful if MYSQL_HOST=localhost

AWS connection information
**************************

This section is required if the USE_AWS=True and if the information is not stored in ~/.aws
Please view `AWS S3 <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html>`_ information on these variables


