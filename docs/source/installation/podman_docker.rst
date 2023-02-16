Installation with Docker or Podman
###################################

This is the fastest way to get started with SmartScope.

Requirements
************

.. warning:: This has been tested with both Podman and Docker. In all the commands below, :code:`docker` can be replaced by :code:`podman` and :code:`docker-compose` by :code:`podman-compose`.

Docker
======

Docker is much easier to set up on most linux distributions and is therefore recommended. `Click here to learn how to install docker <https://docs.docker.com/engine/install/>`_.

.. note:: The latest versions of docker ship with docker-compose included. The commands shown below as :code:`docker-compose` may have to be replaced with :code:`docker compose`

Podman
======

.. note:: The installation requires Podman version >=3.0 and podman-compose 0.1.x. If you are using podman >=3.4, you can use podman-compose from the main branch on github.

Here are the links on how to install Podman and podman-compose:
    - `Podman <https://podman.io/getting-started/installation>`_
    - `podman-compose 0.1.x <https://github.com/containers/podman-compose/tree/0.1.x>`_. For use with podman >=3.0,<3.4
    - `podman-compose stable <https://github.com/containers/podman-compose/tree/stable>`_. For use with podman >=3.4

Nvidia GPU passthrough (optional)
*********************************

.. note:: SmartScope runs quite fast without GPU since it uses pre-trained models for object detection.

If you are planning on using GPU acceleration with SmartScope with podman, the nvidia-container-toolkit is required. The documentation on how to set it up for podman or docker can be found `here <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#podman>`_

NEW! Simplified installation (recommended)
*************************************************

.. note:: To avoid file permission issues, you should perform these steps as the user that will run the smartscope software.

#. Download the minimal configuration files.

    .. code-block:: shell-session

        wget docs.smartscope.org/downloads/SmartScopeInstallation.tar.gz --no-check-certificate
        tar -xvf SmartScopeInstallation.tar.gz 
        cd SmartScope


    The directory contains 5 files that can be divided in 3 categories:

        Docker files:

        - :code:`docker-compose.yml`: Main file for the docker environment. Should not need to be changed.
        - :code:`smartscope.yml`: Simpler version of the docker-compose.yml to add additional settings. This one needs to be changed.

        Configuration:

        - :code:`database.conf`: Contains the configuration for the database connections to share between smartscope and the database.
        - :code:`smartscope.conf`: Contains the configuration that is unique to smartscope.

        Script:

        - :code:`smartscope.sh`: Used to start and stop the smartsocpe software.

#. Create a directory on your SerialEM computer where SmartScope will save data and a storage area for smartscope.

    .. code-block:: shell-session

        mkdir /mnt/serialemComputer/smartscope
        mkdir /mnt/nas/smartscope


#. Edit the :code:`smartscope.yml` file to add your microscope path and the paths that you just created.

    .. code-block:: yaml

        version: "3"
        services:
        smartscope:
          image: ghcr.io/niehs/smartscope:0.8-rc.2  
          user: ${UID}:${GID}
          volumes: 
            # - /home/ubuntu/SmartScope/:/opt/smartscope/
            ######## ADD YOUR MAIN DATA LOCATION ##########
            - /mnt/nas/smartscope/:/mnt/data/
            # Example:
            # - /nfs/data/:/mnt/data/
            ######## ADD YOUR MICROSCOPES #########
            # The synthax from the microscope volumes is as follows:
            # - /path/to/where/serialem/will/write/files/:/mnt/your_scope_name_here/
            - /mnt/serialemComputer/smartscope/:/mnt/myscope1/
            # Example:
            # - /mnt/gatan_Raid_X/smartscope/:/mnt/arctica/


    .. note:: You can add multiple microscopes to the same SmartScope installation. Simply add an additional entry to the volumes section.

#. (Optional) Edit the configuration files to your needs.

    Detailed information about the configuration variables can be found `here <./environment.html>`_

#. Start SmartScope

    The first start will download all the container images and is expected to 

    .. code-block:: shell-session

        ./smartscope.sh start

        #Outputs should look like this
        Starting smartscope
        [+] Running 5/5
        ⠿ Network installation_smartscopenet  Created      0.0s
        ⠿ Container installation-cache-1      Started      0.7s
        ⠿ Container smartscope-db             Started      0.6s
        ⠿ Container smartscope                Started      1.0s
        ⠿ Container installation-nginx-1      Started      1.4s

#. Log in to the web interface with the initial admin account.

    You should now be able to access the smartscope interface at `<http://localhost:48000/>`_.

    The initial account is :code:`admin` with password :code:`smartscope`. 

    .. note:: You may need to change the domain and port number to reflect the docker-compose file with the port specified in the nginx service and one of the domains specified in the ALLOWED_HOSTS of the smartscope service.

#. The installation is done!
    
    There is a few more set up steps to do in SerialEM and in the web portal to get up and running. `Click here <../setup.html>`_. for the instructions

Installation from source
************************

#. Clone or download the `git repository <https://github.com/NIEHS/SmartScope>`_ and navigate to the directory

    .. code-block:: shell-session

        git clone https://github.com/NIEHS/SmartScope.git
        cd SmartScope


#. Using a text editor, copy the :code:`docker-compose-template.yml` to :code:`docker-compose.yml` and edit the values in the volumes and environment to your needs. The file includes description of each entry.
    
    .. warning:: This is the most important step. Please follow the link below for a full description or the docker-compose file requirements.

    .. code-block:: shell-session
        
        #Copy the template file
        cp docker-compose-template.yml docker-compose.yml
        #Open and edit with vim or other text editor
        vim docker-compose.yml

    .. toctree::
        :maxdepth: 1

        ./docker-compose_details.rst
        ./environment.rst


#. Run the docker-compose file. On the first run, this should build the images and start the pods.

    .. note:: 
        This process takes a few minutes to complete when the smartscope images needs to be built. 
        You may be promtped to download images with multiple choices. Select the option that would pull from docker.io.

    .. code-block:: shell-session

        #This will build and run the pod as a daemon
        docker compose up -d

    After the process is finished, you can list the running containers using the following command:

    .. code-block:: shell-session

        docker ps
        #Should produce the following output
        CONTAINER ID  IMAGE                               COMMAND               CREATED       STATUS           PORTS                  NAMES
        c4eaa0478684  k8s.gcr.io/pause:3.2                                      6 hours ago   Up 6 hours ago   0.0.0.0:48000->80/tcp  3e292605506f-infra
        7bb77fe800e6  docker.io/library/mariadb:10.5      mysqld                6 hours ago   Up 6 hours ago   0.0.0.0:48000->80/tcp  smartscope-db
        345730a43ad1  docker.io/library/redis:6.2-alpine  redis-server --sa...  6 hours ago   Up 6 hours ago   0.0.0.0:48000->80/tcp  smartscope-beta_cache_1
        53310f8baf12  localhost/smartscope:0.62           gunicorn -c /opt/...  6 hours ago   Up 6 hours ago   0.0.0.0:48000->80/tcp  smartscope
        ed4cf9175516  docker.io/library/nginx:latest      nginx -g daemon o...  6 hours ago   Up 6 hours ago   0.0.0.0:48000->80/tcp  smartscope-beta_nginx_1

    .. note:: 
        Anytime the docker compose.yml is changed, the pod needs to be stopped and restarted.
        Stop with `docker-compose down` and start `docker-compose up -d`


    Altenatively, it is possible to build separately. To rebuild, add the --no-cache argument to the following command:

    .. code-block:: shell-session

        #This will only the image building
        docker compose build
        #To force rebuilding an existing image
        docker compose build --no-cache

#. Apply database migrations

    There is a chance that something changed in the database and, to avoid errors, try applying the migrations

    .. code-block:: shell-session

        sudo docker exec smartscope manage.py migrate

    .. note:: The output may throw warnings. This is ok as long that there isn't errors.

#. Log in to the web interface with the initial admin account.

    You should now be able to access the smartscope interface at `<http://localhost:48000/>`_.

    The initial account is :code:`admin` with password :code:`smartscope`. 

    .. note:: You may need to change the domain and port number to reflect the docker-compose file with the port specified in the nginx service and one of the domains specified in the ALLOWED_HOSTS of the smartscope service.

#. The installation is done!
    
    There is a few more set up steps to do in SerialEM and in the web portal to get up and running. `Click here <../setup.html>`_. for the instructions