Installation with Podman or Docker
###################################

This is the fastest way to get started with SmartScope.

Requirements
************

.. warning:: This has been tested with both Podman and Docker. Simply replace podman with docker and podman-compose with docker-compose.

.. note:: The installation requires Podman version >=3.0 and podman-compose 0.1.x. If you are using podman >=3.4, you can use podman-compose from the main branch on github.

Here are the links on how to install Podman and podman-compose:
    - `Podman <https://podman.io/getting-started/installation>`_
    - `podman-compose 0.1.x <https://github.com/containers/podman-compose/tree/0.1.x>`_. For use with podman >=3.0,<3.4
    - `podman-compose stable <https://github.com/containers/podman-compose/tree/stable>`_. For use with podman >=3.4

Nvidia GPU passthrough (optional)
*********************************

If you are planning on using GPU acceleration with SmartScope with podman, the nvidia-container-toolkit is required. The documentation on how to set it up for podman or docker can be found `here <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#podman>`_

Installation steps
******************

1. Clone or download the `git repository <https://github.com/NIEHS/SmartScope>`_ and navigate to the directory

    .. code-block:: bash

        git clone https://github.com/NIEHS/SmartScope.git
        cd SmartScope

.. _installation models download:

2. Download the AI models

    The AI models can be download by clicking the following :download:`this link <https://docs.smartscope.org/downloads/Smartscope0.6.tar.gz>` or via the wget command.

    .. code-block:: bash

        wget docs.smartscope.org/downloads/Smartscope0.6.tar.gz
        tar -xvf SmartScope0.6.tar.gz

3. Using a text editor, copy the :code:`docker-compose-template.yml` to :code:`docker-compose.yml` and edit the values in the volumes and environment to your needs. The file includes description of each entry.
    
    .. code-block:: bash
        
        #Copy the template file
        cp docker-compose-template.yml docker-compose.yml
        #Open and edit with vim or other text editor
        vim docker-compose.yml

    .. toctree::
        :maxdepth: 1

        ./docker-compose_details.rst
        ./environment.rst


4. Run the docker-compose file. On the first run, this should build the images and start the pods.

    .. note:: 
        This process takes a few minutes to complete when the smartscope images needs to be built. 
        You may be promtped to download images with multiple choices. Select the option that would pull from docker.io.

    .. code-block:: bash

        #This will build and run the pod as a daemon
        sudo podman-compose up -d

    After the process is finished, you can list the running containers using the following command:

    .. code-block:: bash

        sudo podman ps
        #Should produce the following output
        CONTAINER ID  IMAGE                               COMMAND               CREATED       STATUS           PORTS                  NAMES
        c4eaa0478684  k8s.gcr.io/pause:3.2                                      6 hours ago   Up 6 hours ago   0.0.0.0:48000->80/tcp  3e292605506f-infra
        7bb77fe800e6  docker.io/library/mariadb:10.5      mysqld                6 hours ago   Up 6 hours ago   0.0.0.0:48000->80/tcp  smartscope-db
        345730a43ad1  docker.io/library/redis:6.2-alpine  redis-server --sa...  6 hours ago   Up 6 hours ago   0.0.0.0:48000->80/tcp  smartscope-beta_cache_1
        53310f8baf12  localhost/smartscope:0.62           gunicorn -c /opt/...  6 hours ago   Up 6 hours ago   0.0.0.0:48000->80/tcp  smartscope
        ed4cf9175516  docker.io/library/nginx:latest      nginx -g daemon o...  6 hours ago   Up 6 hours ago   0.0.0.0:48000->80/tcp  smartscope-beta_nginx_1

    .. note:: 
        Anytime the docker-compose.yml is changed, the pod needs to be stopped and restarted.
        Stop with `sudo podman-compose down` and start `sudo podman-compose up -d`


    Altenatively, it is possible to build separately. To rebuild, add the --no-cache argument to the following command:

    .. code-block:: bash

        #This will only the image building
        sudo podman-compose build
        #To force rebuilding an existing image
        sudo podman-compose build --no-cache

5. Set up the initial database (only once)

    SmartScope includes an initial database dump containing the migrations and some basic entries. To copy it into your deployment, you'll need to access the database pod and enter a few commands:

    .. code-block:: bash

        #First copy the dump into the location were your database is. This is the same directory specified in the volumes section of the docker-compose file for the db service.
        cp SmartScope/config/docker/initialdb.sql /path/to/db/
        sudo podman exec smartscope-db /bin/bash -c 'mysql --user=$MYSQL_USER --password=$MYSQL_ROOT_PASSWORD $MYSQL_DATABASE < /var/lib/mysql/initialdb.sql'

6. Log in to the web interface with the initial admin account.

    You should now be able to access the smartscope interface at `<https://localhost:48000/>`_.

    .. note:: You may need to change the domain and port number to reflect the docker-compose file with the port specified in the nginx service and one of the domains specified in the ALLOWED_HOSTS of the smartscope service.

7. The installation is done!
    
    There is a few more set up steps to do in SerialEM and in the web portal to get up and running. `Click here <../setup.html>`_. for the instructions