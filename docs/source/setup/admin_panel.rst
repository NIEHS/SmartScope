Admin portal
############

This section aims at describing the options offered in the admin portal of SmartScope.

Accessing the admin portal
==========================

To access the admin portal, you'll need to log in with either an administrator or staff account.
After login, the admin portal link is fount at the right corner of the screen in the top navigation panel.

Users
**********************

Users are created by admin users. Currently, the admin creates a password for the user during creation.
Password resets are also executed by the admins.
Each users needs to be added to the groups they belong to to access sessions from these groups.

Groups
**********************

Groups are usually principal investigatiors under which the microscopy sessions will be saved. Each member of this lab or group can access the sessions from the group.
Creating a group will also create a directory with the same name in the $AUTOSCREENDIR location.

Microscope
****************
These objects contain the basic information about the microscope and how to connect to them with the SerialEM python connection.

Detector
***************
For each detector on a given microscope that mayu be used with SmartScope, on Detector object must be created containing the atlas acquisition parameters that will be used by SerialEM to acquire the montage.

