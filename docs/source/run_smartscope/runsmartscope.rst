Set up SmartScope
=================

Clicking the Run SmartScope tab on the top navigation bar sends the user to a blank session setup page. A side panel appears on the left of the screen, with a link to return to the setup page, as well as links to the ten most recent sessions.

.. figure:: /_static/setupsession.png
   :width: 100%
   :align: center
   :figclass: align-center

Setup Smartscope
****************

The session setup page includes three main sections: General, Collection Parameters, and Autoloader. Of these settings, only collection parameters may be changed later, and cannot be changed for a grid that is currently being imaged. Information on each section is available by hovering over the *i* near each field.

General
*******

*	Session Name
*	Group
*	Microscope
*	Detector

Collection Parameters
*********************

*	**Atlas x ->** number of tiles in x for the Atlas image
*	**Atlas y ->** number of tiles in y direction for the Atlas image
*	**Squares num ->** number of squares that will be automatically queued
*	**Holes per square ->** number of holes that will be automatically queued *-1 selects all holes identified*
*	**Bis max distance ->** Maximum image shift distance in microns *0 disables image shift*
*	**Min bis group size ->** Smallest number of holes to group in an image shift template. Disabled if Bis max distance is set to zero.
*	**Target defocus min ->** Defocus value closest to zero
*	**Target defocus max ->** Defocus value furthest from zero
*	**Step defocus ->** Step to take when cycling defocus values
*	**Drift crit ->** Drift threshold in A/s before acquiring image *-1 disables drift crit*
*	**Tilt angle ->** Angle of stage tilt
* **Save frames ->** Check whether to save the frames or just the average
* **Force process from average ->** Will force the frames to be processed from average even when the frames are saved
* **Offset targeting ->** Will add an image-shift offset to sample the edges of the holes as well as the centers
* **Offset distance ->** If left to -1, will add a random offset on each acquisition depending on the specified hole type. 
  If a value is specificed, the distance will be applied to all acquisitions. This is mainly useful for data collection where the particles tend to be at the edge of the holes.
* **Zeroloss delay ->** Delay in hours between zero-loss peak refinements.

Autoloader
**********

* **Name ->** Name to be given to the grid
* **Position ->** Position of the grid in the autoloader
* **Hole Type ->** Grid Type by hole spacing or other type is not holey substrate
* **Mesh Size ->** Grid mesh size as from vendor specification
* **Mesh Material ->** Whether it is a gold foil or carbon based.
* **Protocol ->** Place to select a specific protocol or use the automatic assignment :code:`'auto'` as specified in the :doc:`/protocolAPI/auto_protocol`

Empty autoloader slots and grids that are not part of an intended screening sessions should be left completely blank. Otherwise, all fields must be filled in order to run a session.

One autoloader template is available by default. More can be added by pressing the large + button to the right of the first template. Smartscope will automatically fill in the grid information based on the preceeding grid. The template can also be filled by pressing the clipboard button to the right of the grid name field. Grids can be removed by pressing the X button at the top right of the grid template.


Submitting 
**********

Once you have entered all of the information for the session, click on the Submit button. This will create the session and redirect to the `run session page <./run_session.html>`_.


