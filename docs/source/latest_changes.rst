Latest Changes
##############

dev branch
**********

Main changes
~~~~~~~~~~~~
	- Support for Falcon detectors
      - Created an interface without the gatan-only serialem commands
      - V0.8b2 has a consolidated interface for gatan and Falcon
	- Added CTFFit disaplay on the square maps
	- Added a square recentering procedure to the square acquisition routine and changed the eucentricity back to the default sem.Eucenticity(1) command instead of the custom one in Search.
	- Added a default_collection_params.yaml under config/smartscope to easily modify the default values and disable fields in the Run Smartscope page for the collection parameters section.
	- Extended the API query by adding a /detailed sub-route to the /api/squares and /api/holes route. Can be used both single or multiple objects query.
	- Added download buttons for the Atlas and Square maps to easily download the raw, mrc and png files from the web interface
	- Added scale bars and extra metada to the High-mag cards
	- Added image-shift offsets for the hole imaging to get a sampling of the ice across the hole.
      - Can also set a hard offset value to acquire all targets with specific offset.
	- Changed the plugin interface to make it more usable
      - Will need to integrate external packages to really test the viability of the interface.
Minor changes
~~~~~~~~~~~~~
	- Now using an updated version of the SerialEM python module to access new commands
	- Frames default name is now automatically set to `date_gridname_???.tif`
	- The display options are now preserved if the webpage is refreshed instead of resetting to default.
	- Added more default environment variables to the Dockerfile to simplify the docker-compose.yml file.
Bug fixes
~~~~~~~~~
	- Fixed where the active square would not turn yellow until eucentricity was finished
	- Fixed  where data could be fetched by all logged-in users to any groups through the REST api. Now gives permission denied if the user isn't staff or in the group.
	- Fixed where Regrouping the BIS grouping from the webUI was not working.
	- Fixed few bugs with the preprocessing pipeline crashing
	- Fixed error with protocol selection when Lacey carbon and negative stain grids are selected.
	- Fixed issue with django-filters not being active when querying the REST API.
	- Fixed issue with the Dockerfile where pip was not found during build.


