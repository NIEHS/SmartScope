Installation with Podman or Docker
###################################

This is the fastest way to get started with SmartScope.

Requirements
************

**Warning:** This has been tested only with Podman thus far. We assume that it will work with Docker as well using the same commands and simply replacing podman with docker.

**Versions tested:** The installation requires Podman version >=3.0 and podman-compose 0.1.x. If you are using podman >=3.4, you can use podman-compose from the main branch on github.

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

2. Download the AI models

    .. code-block:: bash

        Add the AI models download procedure

3. Using a text editor, open the docker-compose.yml file and edit the values to your needs. The file includes description of each entry.

    .. raw:: html

        <details>
        <summary><a>docker-compose.yml</a></summary>

    .. literalinclude:: docker-compose.yml
        :language: yaml
        :linenos:

    .. raw:: html

        </details>


4. Run the docker-compose file. On the first run, this should build the images and start the pods.

    .. code-block:: bash

        #This will build and run all the pods as a daemon
        sudo podman-compose up -d

    Altenatively, it is possible to build separately. To rebuild, add the --no-cache argument to the following command:

    .. code-block:: bash

        #This will only the image building
        sudo podman-compose build
        #To force rebuilding an existing image
        sudo podman-compose build --no-cache
 