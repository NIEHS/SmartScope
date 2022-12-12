Creating a new function-based plugin
####################################

An algorithm can be wrapped into a function to run within SmartScope. It is required to provide an output that SmartScope can read and use.

A basic wrapper goes as follows, it take a Montage class as the minimal argument as well as the kwargs necessary to run the function from the configuration file:

.. code-block:: python

    def mywrapper(montage:Montage, *args, **kwargs) -> Tuple[List,bool,dict]:
        # excexute your code here on the image
        output = myAlgorithm(montage.image, **kwargs)
        #logic to convert_ouputs
        success = bool#check that the method provided the right outputs
        additional_output = dict()#if any other outputs that may be useful are returned
        return outputs, success, additional_output

Accepted output formats
=======================

- List of center coordinates i.e. [[x1,y1],[x2,y2],...]
- List of boxes with upper-left and lower-right corners, i.e. [[x1ul,y1ul,x1lr,y1lr],[x2ul,y2ul,x2lr,y2lr]]
- coordinates can be provided as numpy arrays, i.e.[np.array([x1,y1]),np.array([x2,y2]),...] 

additional_ouptut
=================

This is currently a placeholder for additional_outputs that may be used by smartscope when/if provided. The format with be a dict of values where specific keys will be used. More on this soon...


Creating a new class-based plugin
#################################

Class-based plugins are similar to function-based plugin with more flexibility. The first part is to subclass from one of the plugin classes that meets your algorithm's :

- Finder
- Classifier
- Selector
- Finder_Classifier


All of these classes stem from the BaseFeatureAnalyzer class shown below:

.. literalinclude:: ../../../Smartscope/lib/Datatypes/base_plugin.py
    :pyobject: BaseFeatureAnalyzer

The properties are the same that can be set in the configuration.yaml file for a plugin. The :code:`run()` method will be called when the plugin is being run so this is the main method to override when creating a class-based plugin.

Example
=======

Here is the example of how the ptolemy hole finder was created.

.. literalinclude:: ../../../external_plugins/ptolemy/smartscope_plugin/plugin.py
