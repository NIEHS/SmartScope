Latest Changes
##############

Main changes
~~~~~~~~~~~~

- Simplified installation procedure
	- Added a docker repositoty with prebuilt images
	- Astracted the docker commands behind a simple bash script
- Grid metadata can now be exported and re-imported into the same or new SmartScope instance.
	- This feature will require more work for automatically creating the directory structure and move the data automatically but this is a start.
- Added a :doc:`/protocolAPI/index` to add more flexibility to the workflow.
- Ptolemy is now integrated as an :doc:`external plugin</external_plugins/index>`.
	- Used as a medium mag hole finder for refinining the hole positions. Targeting of the holes is now much more precise.
- Support for Falcon detectors
	- Created an interface without the gatan-only serialem commands
	- V0.8b2 has a consolidated interface for gatan and Falcon
- Added CTFFit display on the square maps
- Added a square recentering procedure to the square acquisition routine and changed the eucentricity back to the default sem.Eucenticity(1) command instead of the custom one in Search.
- Added a default_collection_params.yaml under config/smartscope to easily modify the default values and disable fields in the Run Smartscope page for the collection parameters section.
- Extended the API query by adding a /detailed sub-route to the /api/squares and /api/holes route. Can be used both single or multiple objects query.
- Added download buttons for the Atlas and Square maps to easily download the raw, mrc and png files from the web interface
- Added scale bars and extra metadata to the High-mag cards
- Added image-shift offsets for the hole imaging to get a sampling of the ice across the hole.
	- Can also set a hard offset value to acquire all targets with specific offset.
- Changed the plugin interface to make it more usable and flexible.


Minor changes
~~~~~~~~~~~~~

- Added notification for commands that are currently issued to the backend and waiting for response.
- Added a link to submit issues on gihub in the navbar
- Now using an updated version of the SerialEM python module to access new commands
- Frames default name is now automatically set to `date_gridname_???.tif`
- The display options are now preserved if the webpage is refreshed instead of resetting to default.
- Added more default environment variables to the Dockerfile to simplify the docker-compose.yml file.
- Can now click on the hole to view medium mag before all the high mag images are acquired


Bug fixes
~~~~~~~~~

- Fixed not being able to click on the edge of maps on smaller browser windows
- Fixed issue with the Regular Pattern plugin not setting targets on the entire width of the K3 images
- Fixed issues with the Regrouping BIS command not putting all the targets correctly back into the queue
- Moved all the database writing actions back to restAPI for authentication simplicity. More secure until authentication can be confirmed in the websocket layer.
  - Websocket still used for receiving data from the backend
- Mouse cursor properly changing when hovering over the sidepanel links
- Fixed issue where toggling the legend display on a map didn't remove the scale bar, thus preventing clicking the areas beneath it.
- Fixed issue with column valves not closing after session.
- Fixed issue with being unable to click sqaures on the right part of the atlas while using a small browser window.
- Added atlas and medium mag completion times
- Fixed where the active square would not turn yellow until eucentricity was finished
- Fixed  where data could be fetched by all logged-in users to any groups through the REST api. Now gives permission denied if the user isn't staff or in the group.
- Fixed where Regrouping the BIS grouping from the webUI was not working.
- Fixed few bugs with the preprocessing pipeline crashing
- Fixed error with protocol selection when Lacey carbon and negative stain grids are selected.
- Fixed issue with django-filters not being active when querying the REST API.
- Fixed issue with the Dockerfile where pip was not found during build.
- Found a very old issues with the build montage and the piece centers were not correctly calculated


