How to prepare your docker-compose file
#######################################

 .. note:: This section aims a breaking down and explaining the different components of the docker-compose.yml file.

The docker-compose.yml file allows the deployment of multiple containers at once.

.. raw:: html

    <details>
    <summary><a>docker-compose.yml</a></summary>

.. literalinclude:: docker-compose.yml
    :language: yaml
    :linenos:

.. raw:: html

    </details>


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

container-name
==============

If not specified, it will assign a name to the container usually under the form of directory_service_1.

volumes
=======

.. warning:: This is most important section to modify according to your system specifications. All services except cache have changes in the volume section.

Every item in the volume section serves to bind (or mount) a path from the host system to the container. 
The synthax goes as follows: `/path/on/host/system/:/path/on/container`

For example, `/data/smartscope/:/mnt/data/` will bound the content of `/data/smartsope/` to the `/mnt/data/` location inside the container.

.. note:: When modifying the the docker-compose.yml file, only the path before the colon ":" should be modified.

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

Currently used in the smartscope service to pass the nvidia GPU to to the container.

.. note:: The deploy section is optional as smartscope can also run on cpu only. Can be removed or commented out.

ports
=====

A list of ports that are forwarded from the container to the host system. Currently used in nginx to pass the webserver port 80 to 48000 on the host.
The synthax goes as follows: `HostPort:ContainerPort` and, as for volumes, only the host side should be changed.


    
