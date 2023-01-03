External plugins
================

Third-party or external plugins should be installed in the :code:`external_plugins` directory of the SmartScope repository.

The plugin directory name needs to be added in a new line to the :code:`config/smartscope/plugins/external_plugins.txt`. This allows to only load the plugins within specific subdirectories of the external_plugins.

Capabilities
############

The external plugins can bring a few new capabilities to SmartScope. 

- Add new Finder, Classifier, Selector algorithms.
- Add new predefined protocols
- Add new protocol commands to use within protocols

Conventions for automatic registration
######################################

To be registered properly by SmartScope, the directory containing the plugin should contain the following a :code:`smartscope_plugin` sub-directory.

In there should be all the python files that are part of the plugin. These python files can make use of everything that is part of :code:`Smartscope.lib` and :code:`Smartscope.core` if necessary.

Then, depending on what capabilities are to be added here are the other requirements:

Finder, Classifier, Selector algorithms plugins
-----------------------------------------------

All configuration files for the different plugins should be added in :code:`smartscope_plugin/plugins` sub-directory. With one `.yaml` file per plugin.

Predefined protocols
--------------------

All configuration files for new protocols should be added in :code:`smartscope_plugin/protocols` sub-directory. With one `.yaml` file per protocol.

Protocol commands
-----------------

All protocol commands should be found in a :code:`smartscope_plugin/protocol_commands.py` and contain a :code:`protocolCommandsFactory` dictionary for registering the methods.

