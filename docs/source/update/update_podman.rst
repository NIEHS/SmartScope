Updating a Docker installation
##############################

This section outlines the steps to update your SmartScope installation with Podman/Docker

#. Back up your database

    This step is mostly to protect your data in case the update fails.

    .. code-block:: bash

        ## REPLACE YYYYMMDD by the current date ##
        sudo podman exec smartscope-db /bin/bash -c 'mysqldump --user=$MYSQL_USER --password=$MYSQL_ROOT_PASSWORD $MYSQL_DATABASE > /var/lib/mysql/YYYYMMDD_dump.sql'

#. Stop SmartScope

    .. code-block:: bash

        sudo docker-compose down


#. Pull the latest version

    To update your docker installation, first go to your smartscope directory, where you initially cloned the repository,
    Copy your docker-compose.yml file in case there is an update to that file and pull the update.

    .. code-block:: bash

        cd /to/Smartscope/directory/
        cp docker-compose.yml docker-compose-bak.yml
        git pull

    If the docker-compose.yml was changed, make that your volume and enviroment sections are the correct. Use the back up file to copy the values back in.

#. Restart the pod

    .. code-block:: bash

        sudo docker-compose up -d

    .. note:: If the Dockerfile changed, it will rebuild the new image

#. Apply database migrations

    There is a chance that something changed in the database and, to avoid errors, try applying the migrations

    .. code-block:: bash

        sudo docker exec smartscope manage.py migrate

    .. note:: The output may throw warnings. This is ok as long that there isn't errors.