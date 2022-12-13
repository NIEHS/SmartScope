External plugin installation
============================

Third-party or external plugins should be installed in the :code:`external_plugins` directory of the SmartScope repository.

To be registered properly by SmartScope, the directory containing the plugin should contain a :code:`smartscope_plugin/config/` directory containing the plugin or plugins :doc:`configuration yaml </plugins/configuration>`

Finally, the plugin directory name needs to be added in a new line to the :code:`config/smartscope/plugins/external_plugins.txt`. This allows to only load the plugins within specific subdirectories of the external_plugins.

Installing the ptolemy hole finder external plugin
==================================================

.. note:: This process is manual but will be more automated with install scripts in the near future.

.. code-block:: shell-session
    $ cd /path/to/Smartscope/external_plugins
    $ git clone https://github.com/JoQCcoz/ptolemy-smartscope.git
    $ echo 'ptolemy-smartscope' > ../config/smartscope/plugins/external_plugins.txt

