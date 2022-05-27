.. SmartScope documentation master file, created by
   sphinx-quickstart on Tue Jan 11 13:10:51 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to SmartScope!
======================================
**This documentation website is still under construction.**

SmartScope is a framework for automated cryo-electron microscopy (Cryo-EM). 
The main purpose is to automate specimen screening, document the process, and provide a portal for visualization and interaction with the microscope.
The software bundles a database, the main imaging workflow and a web user-inteface for easy access. 
To run Smartscope, simply fill the form about which grids to be screened, press start and wait for live results to come in.

.. figure:: /_static/webui.png
   :width: 90%
   :align: center
   :figclass: align-center

   SmartScope webUI example

Beta testing program
=========================
**SmartScope is currently holding a closed beta testing program.**

We want SmartScope to provide a great user experience and want to polish the software and documentation before release.

During the closed beta phase, the source code will only be made available with the testers. The goal will be to test in different environments and on multiple hardware types (detectors and microscopes).

We will work closely with testers with their initial setup and obtain feedback.

If you would like to contribute to the codebase during the closed beta period, please email us for inquiries.

To enroll in the closed beta, please send an email to:

* Jonathan Bouvette (jonathan.bouvette@nih.gov)
* Mario Borgnia (mario.borgnia2@nih.gov)
* Alberto Bartesaghi (alberto.bartesaghi@duke.edu)

Timeline
########
Here is the expected timeline of SmartScope beta program and release:

.. csv-table::
   :header: "Phase", "Start", "End", "Source code"
   :widths: 20, 20, 20, 20

   "Closed beta", "*null*", "2022-06-30", "Private"
   "Open beta", "2022-07-01", "2022-08-30", "Public"
   "Release", "2022-09-01", "*null*", "Public" 
*Dates are subject to change*

Site map
========

.. toctree::
   :maxdepth: 2

   webinterface/overview.rst
   installation.rst
   setup.rst
   run_smartscope.rst
   citation.rst
   license.rst

   



.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`