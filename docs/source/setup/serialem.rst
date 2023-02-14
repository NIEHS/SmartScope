SerialEM setup
==============

In this section, you'll find how to set up SerialEM for SmartScope use. 


Calibrations
************

To ensure maximal precision of targeting and coordinate conversion, it is crucial that LM pixel size and rotation angle calibrations are verified before using SmartScope.
In the event of targeting problems between the atlas and squares, where squares are off-centered, it is very likely due these calibrations being off.

1- Setting up external python for SerialEM
******************************************

Documentation on how to set up can be found on the `SerialEM website <https://bio3d.colorado.edu/SerialEM/hlp/html/about_scripts.htm#Python>`_. We have now installed on a few systems and here are some examples for setting up the :code:`SerialEMproperties.txt`.

:code:`SocketServerIP 1 xxx.xxx.xxx.xxx`, is the IP where the :code:`FEI-SEM-server.exe` is running

Otherwise, :code:`SockerServerIP 7` should be the IP of the SerialEM PC.


**Example: Talos Arctica with K2 or K3**

    * Microscope PC IP: 192.168.0.3
    * Gatan PC IP: 192.168.0.32
    * SerialEM is installed on the Gatan PC

    The following lines should be added to :code:`SerialEMproperties.txt`.

    .. code-block::

        SocketServerIP                  1 192.168.0.3
        SocketServerPort                1 48892
        SocketServerIP                  7 192.168.0.3
        SocketServerPort                7 48888
        EnableExternalPython            1


.. note:: SerialEM needs to be restarted after changing properties.

Testing the connection to serialEM
##################################

To quickly test if your settings are good for the python connection to SerialEM, you can use the following commands and replace IP by the gatan PC address and port by 48888.

From our examples above, the Talos Arctica IP would be 192.168.0.32 and port would be 48888.

.. code-block::

    docker exec smartscope smartscope.py test_serialem_connection IP port

    ### EXAMPLE ###
    docker exec smartscope smartscope.py test_serialem_connection 192.138.0.32 48888

If the connection is successful, a :code:`Hello from smartscope` message should appear in the SerialEM log window. Now, you can proceed to adding a microscope.

2- Register a microscope to the SmartScope database
****************************************************************

Now that the connection to SerialEM works, we can add our microscope to the database.

To do so, navigate to the admin portal and then the Microscopes section and add microscope. It should bring you to `<localhost:48000/admin/API/microscope/add/>`_.

.. figure:: /_static/add_scope.png
   :width: 60%
   :align: center
   :figclass: align-center

General
#######
* **Name:** Should be however your facility calls the microscope. i.e. Arctica, Krios-1
* **Location:** Usually the name of the center. i.e. NIEHS

Hardware constants
##################
* **Voltage:** Microscope Voltage on kV
* **Spherical abberation:** Microscope spherical abberation
* **Loader Size:** For Autloader microscopes, the value should be 12. Side entry should be 1. If you have a JOEL scope and cannot run a LoadCartridge command from SerialEM, it should be set to 1

Smartscope Worker
#################

* **Worker Hostname:** Should remain localhost unless SmartScope is set up as a master-worker configuration. *More details soon*
* **Executable:** Should remain smartscope.py unless SmartScope is set up as a master-worker configuration. *More details soon* 

SerialEM external python connection
###################################

* **Serialem IP:** IP of the SerialEM computer. 
* **Serialem PORT:** Port of the serialEM python socket. default is 48888. It depends on how is was set up in :code:`SerialEMproperties.txt` in :ref:`step 1 <1- Setting up external python for SerialEM>`. 

Filesystem Paths
################

These two paths should be pointing to the same directory. One is for SerialEM to save the files in the windows computer. The other is for SmartScope to find the files saved by SerialEM.

* **Windows path:** Path of the directory where SerialEM will save the files, viewed from the SerialEM PC
* **Scope path:** Path of the directory where SerialEM will save the files, viewed from the SmartScope container.

Here's a example:

    Let's say the data is going to be saved in :code:`X:\\smartscope` and the :code:`X:\\` drive is mounted to the linux computer at :code:`/mnt/gatan_RaidX/`. 

    Also, let's assume that the :code:`/mnt/gatan_RaidX/:/mnt/krios/` bind was set up in the volumes of the smartscope service in the :code:`docker-compose.yaml`. 

    In that case, :code:`X:\\smartscope` is equivalent to :code:`/mnt/krios/smartscope` in the smartscope container.

    Then, the microscope :code:`Windows path= X:\\smartscope` and :code:`Scope path= /mnt/krios/smartscope`

.. note:: Please make sure that this path is writable by both SerialEM and SmartScope.

3- Register a detector to the SmartScope database
****************************************************************

Each microscope must have least one detector.

Similarly to adding a microscope, navigate to the admin portal and then the Detectors section and add. It should bring you to `<localhost:48000/admin/detector/add/>`_.

.. figure:: /_static/add_detector.png
   :width: 60%
   :align: center
   :figclass: align-center

To accomodate for Falcon detectors which have hard-coded frames root directory, the frames directory can be set seperately from the Microscope 
with the `Frames windows directory` and `Frames directory`. If you are not using a Falcon detector, it is recommended to set this value to the same as for the microscope
with the addition of `/movies`. As with the example above, it would become :code:`Frames windows directory= X:\\smartscope\movies` and :code:`Frames directory= /mnt/krios/smartscope/movies`

4- Low-dose Presets
*******************

The idea is to generate a settings file with low-dose mode presets that will work well with the current version of SmartScope.

The following table provides guidelines on how to set up the low-dose mode settings for different microscopes:

.. csv-table::
   :widths: 20, 20, 20
   :align: center

   "", "**Example 1**", "**Example 2**"
   "**Instrument**", "",""
   "Microscope", "Talos Arctica", "Titan Krios G4"
   "Detector", "Gatan K2 Summit", "Gatan K3"
   "Energy Filter", "","Gatan Bioquantum"
   "**Low Dose Preset**", "", ""
   "**Search**", "", "" 
   "magnification", 210, 580
   "Pixel size (A/pix)", 196, 152
   "Mode", "Linear", "Counting"
   "**View**", "", "" 
   "magnification", 1250,2250
   "Pixel size (A/pix)", 34.2, 38.9
   "Mode", "Linear", "Counting"
   "**Focus/Record**", "", "" 
   "magnification", "36,000","81,000"
   "Pixel size (A/pix)", 1.19, 1.08
   "Mode", "Counting", "Counting"
   "**Mont-map/Full grid montage**", "", ""
   "magnification", 62, 135
   "Pixel size (A/pix)", 644, 654
   "Mode", "Linear", "Counting"

Search
#######
The search mag is set in LM mode to allow the capture of an entire square in a single acquisition.
On a K2 detector, we suggest using linear mode for search to maximize contrasts.

View
#######
The view mag is using a low SA or M mode magnification to view a few holes. It is currently only used to re-center on a hole.

Preview
#######
Currently, Preview is used to acquire the main high-magnification acquisition because of initial limitations with SerialEM.
Ensure that dose-fraciionation and exposure times are set for that purpose.

Record
#######

Currenly used to acquire the atlas. Atlas is acquired outside of low-dose mode and current scripting commands for acquiring montage will use Record by default.

.. note:: We're currently testing how to reliably use the mont-map preset for the atlas acquisition, which will allow us to use Record instead of Preview for the acquisition.

Focus/Trial
############

Used for autofocus and drift correction. For autofocus, the specified image-shift position that is set will be used for each sample. We suggest changing it when doing data collection to ensure that the focus area illuminates between holes.

.. note:: This will also be changed in the near future. We plan on including automatic focus positioning relative to the mesh spacing and orientation.

5- Non Low-dose Presets
************************

The easiest way to set up for the atlas is to create an imaging state for mont-mapping. This way, when acquiring the atlas, it will use the mont-map setting instead of Record.

