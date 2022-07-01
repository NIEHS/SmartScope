How to prepare your docker-compose file
#######################################

.. note:: This section aims a breaking down and explaining the different components of the docker-compose.yml file.

The docker-compose.yml file allows the deployment of multiple containers at once.

.. raw:: html

     <p><details><summary><a>docker-compose-template.yml</a></summary>

.. literalinclude:: docker-compose.yml
    :language: yaml
    :linenos:

.. raw:: html
    
    </details></p>


The file is essentially a list of services that need to be run. Each service contains a list of settings, some of which need to be adapted for each system.


Services
********

SmartScope requires 4 different services/containers to run.

smartscope
==========

This container is the most important as it runs the SmartScope workflow and Web Server.

db
==

This container runs a MariaDB SQL database server to which SmartScope connects to save and query data.

cache
=====

This container runs a Redis cache mainly involved in websocket communication between the SmartScope workflow and the Web Interface.

nginx
=====

This container runs the Nginx reverse-proxy to serve as a proxy for the Web Server and all the different static files that need to be served to the WebUI.
It also handles the https/SSL encryption (needs to be specifically enabled).


At this point the docker-compose file could be simplified to this:

.. literalinclude:: docker-compose-baseservices.yml
    :language: yaml
    :linenos:

Services settings
*****************

In each service, there are multiple sections to fill, some of which need to be edited to each systems. This section will break down the options and 

image
=====

The name of the image that is going to be used. When running the `podman-compose up`, podman will look if the image is already present in the local computer 
and otherwise will download the the image from the selected repository.

.. note:: When prompted to download the images, select the docker.io option as the other repository may not work properly.

build
=====

When the image is specified at localhost/imagename and is not found, it will build it from the Dockerfile at the specificed context location.
Other arguments can be passed to the image building process.

Only the :ref:`smartscope<smartscope>` service has a build section:

.. code-block:: yaml
    :caption: Minimal build block

    smartscope:
      build:
        context: .

The section has optional arguments which can be added as follows

.. code-block:: yaml
    :caption: Optional build arguments

    smartscope:
      build:
        context: .
        args:
          - USER_ID=
          - GROUP_ID=

These arguments are used to control the uid and gid other user account within the conatiner.
The advantage of these arguments are mostly for a file permission standpoint. By setting these values to a user and group on the host system, 
it streamlines the permissions and file access later on without having to create new permission set.

For example, if you would like to files to be owned by a user named *smartscope_user* with a uid of 1003 set the group to *cryoem_staff* with a gid 1005, you may use those values in the args section.  

.. code-block:: yaml
    :caption: Example

    build:
      context: .
      args:
        - USER_ID=1003
        - GROUP_ID=1005

To find uid and gid:

.. code:: bash

    #Find the uid of a user
    $ id -u smartscope_user
    1003

    #Find the gid of a group
    $ getent group cryoem_staff
    cryoem_staff:*:1005:list,of,users,in,group

        


container-name
==============

If not specified, it will assign a name to the container usually under the form of directory_service_1. 
The most likely containers that, as a user, you may want to interact with the command line are the smartscope and db. This is why the container-name has been fixed to for these services:

.. code-block:: yaml
    :caption: container-name

    version: "3"
    services:
      smartscope: 
        container_name: smartscope
      db: 
        container_name: smartscope-db

To connect to the shell of these services:

.. code-block:: bash
    :caption: Example
    
    $ podman exec -it smartscope /bin/bash
    smartscope_user@53310f8baf12:/opt/smartscope$


volumes
=======

.. warning:: This is most important section to modify according to your system specifications. All services except cache have changes in the volume section. 

.. warning:: All directories and files bound to the :ref:`smartscope<smartscope>` container must have read-write permission to user in the container (default uid:1000) or the uid/gid specified in the :ref:`build<build>` section.

Every item in the volume section serves to bind (or mount) a path from the host system to the container. 
The synthax goes as follows: `/path/on/host/system/:/path/on/container`

For example, `/data/smartscope/:/mnt/data/` will bound the content of `/data/smartscope/` to the `/mnt/data/` location inside the container.

.. note:: When modifying the the docker-compose.yml file, only the path before the colon ":" should be modified.

Here is the list of volumes for each services:

.. _smartscope volumes:
smartscope
----------

    **Required mounts**

    * Main data location:
        This is where all the images and metadata for smartscope will be saved.
        Binds to :code:`/mnt/data/`` in the container.
    * Microscope data locations:
        For each microscope to connect to the smartscope instance, one volume must be created. This is where SerialEM will save the files so it must be a location that is available to both SerialEM and the SmartScope computer.
        You may choose the location name within the container in :code:`/mnt/`.

        .. code-block:: yaml
            :caption: Example

            # Let's say we created a Smartscope folder in our serialEM computer 
            # which is mounted in /mnt/microscope_glacios/ on our linux system.
            # We may want to mount it to /mnt/glacios/ in the smartscope container.
            smartscope:
              volumes:
                - /mnt/microscope_glacios/Smartscope/:/mnt/glacios/

    * AI models and other template files:
        That is the directory downloaded in the `installation <./podman_docker.html#installation-models-download>`_ procedure which contains the current AI models for the squares and holes detectors and some other template files.
        It should be bound to :code:`/opt/Template_files/`

    **Optional mounts**

    * Log files locations:
        It is recommended to bind a directory to :code:`/opt/logs/` to keep a record of the logs in case of errors and crashes.
    * Long term data location:
        If the plan is to offload the main data location to another storage location, you can bind that location to :code:`/mnt/longterm/` and set :code:`USE_LONGTERMSTORAGE: 'True'` in the enviroment section.
        This will allow smartscope to still load and display the images in the WebUI after the data has been moved.
    * Test files:
        The test files are required to run smartscope in `fake-scope mode <../testing/fake_scope_mode.html>`_. Mount the downloaded test files to /mnt/testfiles/.
    * SmartScope source code:
        Although the image contains the SmartScope source code already. Most small updates and hotfixes can be pulled without having to re-build the entire image.
        Mounting the downloaded repository to the container serves that purpose. Mount to :code:`/opt/smartscope/` and it will override the default version.

.. _db volumes:
db
--- 
    
    **Required mounts**

    * Database location:
        This is where all the database data will be saved. Needs to be mounted to :code:`/var/lib/mysql/`     

.. _nginx volumes:
nginx
-----
    **Required mounts**

    * Main data location:
        This is the same as the Main data location in the :ref:`smartscope volumes`
    
    * Static files location:
        **Doesn't need change**
        To be able to properly render the webpage javascript and css content. 
        It mounts the SmartScope repository's static directory as such :code:`/opt/smartscope/static/`

    * Nginx config file:
        **Needs change to use SSL encryption**
        Default: :code:`./config/docker/templates_noSSL/:/etc/nginx/templates/`

        To enable SSL in your server:
            Replace by: :code:`./config/docker/templates_SSL/:/etc/nginx/templates/`
            Add certificate and private key to the volumes:
                `/path/to/certs/cert.pem:/opt/certs/smartscope.crt`
                `/path/to/certs/privkey.pem:/opt/certs/smartscope.key`
        
    
    **Optional mounts**

    * Long term data location:
        If specified previously, this is the same as the Long term data location in the :ref:`smartscope volumes`
    


environment
===========

.. note:: This is another section where some values may be changed

List of environment variables to pass to the container. `Click here <./environment.html>`_ for details about the environment variables.

depends_on
==========

Other containers that need to run prior to starting this one

networks
========

A private network allocation for the communication between the process. Needs a network section in the root of the yaml file as well.

command
=======

If a specific command needs to run when the container is started

deploy
======

Used in the :ref:`smartscope`` service to pass the nvidia GPU to to the container.

.. note:: The deploy section is optional as smartscope can also run on cpu only.

To enable add:

.. code-block:: yaml
    :caption: Example

    smartscope:
      deploy:
        resources:
          reservations:
            devices:
              - driver: nvidia
                count: 1
                capabilities: [ gpu ]   

ports
=====

A list of ports that are forwarded from the container to the host system. Currently used in nginx to pass the webserver port 80 to 48000 on the host.
The synthax goes as follows: `HostPort:ContainerPort` and, as for volumes, only the host side should be changed.

In the :ref:`nginx` container section, if you use ssl, use :code:`- 443:443` instead of the default :code:`- 48000:80`

    
