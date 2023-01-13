Plugin configuration
====================
    
The configuration of each plugin is provided as a yaml file in the :code:`config/smartscope/plugins/` directory. The configuration will depend widely upon the integration method (class or function).

The fastest way to build a plugin is by writing a function. In this case more information will be required in the configuration.

Plugins can also be provided as a class. In this case, more information can be built directly into the classe, which makes the configuration file shorter.

Here is a list of all the fields that can be used in a configuration.yaml file:

- name: `string` `(required)`

    This is the name of the plugin. This will be used in the database entries to refer to a specific plugin. 
    The name should not be changed after use as it may break the references and would require a database migration of all the entries.

- importPaths: `list`

    If any paths need to be added to the PYTHONPATH to import the modules for the plugin. `i.e. importPaths: ['/opt/smartscope/external_plugins/ptolemy/']`

- description: `string`

    This is used to provide a description of the plugin on the web interface for the users to see

- reference: `string`

    Reference to the publication for the given algorithm. This is currently not rendered on the web interface but will be added soon.

- kwargs: `dict`

    A list of default arguments to provide to the run function. Values can be set directly in the wrapper function but this provides an easy place to change defaults.

Specific to class-based plugin
------------------------------

- pluginClass: `string` 
  
    If providing the plugin as a class, this value should be set.

Specific to function-based plugin
---------------------------------

- module: `string`

    The module from where the function will be imported `i.e. module: Smartscope.lib.Finders.AIFinder.wrapper`

- method: `string`

    The function name `i.e. find_holes`

- targetClass: `list`

    The type of plugin that should be initialized. For algorithm that provide multiple outputs such as a Finder/Classifier combo, then 2 values can be provided.

    - Finder
    - Classifiers
    - Selector

Specific to Classifiers
-----------------------

- classes: `dict`

    Description and colors scheme for all the possible classes in a classifier. Each possible class is a key that contains a dict of 3 entries:

    - classLabel: `dict`

        - name: `string`
        
            Name of the class that will be displayed on the web interface
        
        - value: `int`

            Usually 1 or -1 whether the class should be included or excluded from the selection pool.

        - color: `str`

            CSS color name or hex value for the display of the class on the web page.

Specific to Selectors
---------------------

- clusters: `dict`

    How to display the different clusters of values.

    - values: `acsending|descending`

        How to sort the clusters

    - colors: 
    
        A list of CSS color name or hex value the display different clusters. ['blue', 'lightblue', 'CornflowerBlue', 'blueviolet', 'purple', 'white']

- exclude: `list`

        A list of clusters to exclude by default from the target selection.


Examples
========

Finder and classifier combination
---------------------------------
.. literalinclude:: ../../../config/smartscope/plugins/ai_square_finder.yaml
    :language: yaml


External plugin
---------------

.. code-block:: yaml
    
    name: Ptolemy hole finder
    pluginClass: smartscope_plugin.plugin.PtolemyHoleFinder