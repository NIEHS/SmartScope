Testing SmartScope without the microscope
#########################################

It is possible to test the SmartScope installation and setup by running the workflow without the microscope.

The initial database provided with SmartScope should already contain a fake_scope and fake_detector for selection.

Selecting this scope during a `session setup <../run_smartscope/runsmartscope.html>`_ will pick random images from a bank of images.

Setting up the image bank
*************************

You can download an initital image bank to which you can add your own images.

To download:

.. code-block:: bash

    wget docs.smartscope.org/downloads/smartscope_testfiles.tar
    tar -xvf smartscope_testfiles.tar

**Podman/Docker Installation**

    Mount the location of smartscope_testfiles to /mnt/fake_scope/.

**Anaconda**

    Change the TEST_FILES enviroment variable to the smartscope_testfiles location.

