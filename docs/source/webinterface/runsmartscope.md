# Run Smartscope

Clicking the Run Autoscreening tab on the top navigational bar sends the user to a blank session setup page. A side panel appears on the left of the screen, with a link to return to the setup page, as well as links to the ten most recent sessions.

<!-- ### Session Information Page

The session tabs on the left side of the screen are notated with the starting date and the session name indicated during session setup.

Clicking on a session tab in the left side panel opens an informational page about the session, including the session status, queue information, output logs, and error logs. From this page, the user can stop or start the session using buttons near the top of the page, and toggle pauses after grids.

Pause between grids is an option that is automatically disabled, and the button is red when disabled. When enabled by clicking, the button turns green.

When Pause between grids is enabled, after SmartScope has imaged all holes in the queue, it will wait until the user navigates to the informational page and chooses to either continue imaging the current grid (after queuing more squares/holes in the Automatic Screening Browser) or to move on to the next grid. 

When pause between grids is disabled, SmartScope will automatically unload the grid once it has imaged all holes in the queue, and either load the next grid or finish the session. -->

## Setup Smartscope

The session setup page includes three main sections: General, Collection Parameters, and Autoloader. Of these settings, only collection parameters may be changed later, and cannot be changed for a grid that is currently being imaged. Information on each section is available by hovering over the *i* near each field.

### General
*	Session Name
*	Group
*	Microscope
*	Detector

### Collection Parameters
*	Atlas x -> number of tiles in x for the Atlas image
*	Atlas y -> number of tiles in y direction for the Atlas image
*	Squares num -> number of squares that will be automatically queued
*	If SmartScope cannot identify the number of squares requested, it will queue as many as possible
*	Holes per square -> number of holes that will be automatically queued *-1 selects all holes identified*
*	Bis max distance -> Maximum image shift distance in microns *0 disables image shift*
*	Min bis group size -> Smallest number of holes to group in an image shift template. Disabled if Bis max distance is set to zero.
*	Target defocus min -> Defocus value closest to zero
*	Target defocus max -> Defocus value furthest from zero
*	Step defocus -> Step to take when cycling defocus values
*	Drift crit -> Drift threshold in A/s before acquiring image *-1 disables drift crit*
*	Tilt angle -> Angle of stage tilt


### Autoloader


* Name
* Position -> Position of the grid in the autoloader
* Hole Type
  *  MultiA
  *  Negative Stain
  *  R 0.6/1
  *  R 1.2/1.3
  *  R 2/1
  *  R 2/2
  *  R 2/4
* Mesh Size
    * 200
    * 300
    * 400
* Mesh Material
  * Carbon
  * Gold

Empty autoloader slots and grids that are not part of an intended screening sessions should be left completely blank. Otherwise, all fields must be filled in order to run a session.

One autoloader template is available by default. More can be added by pressing the large + button to the right of the first template. Smartscope will automatically fill in the grid information based on the preceeding grid. The template can also be filled by pressing the clipboard button to the right of the grid name field. Grids can be removed by pressing the X button at the top right of the grid template.