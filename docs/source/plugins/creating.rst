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

.. code-block:: python

  from Smartscope.lib.Datatypes.base_plugin import Finder
  from Smartscope.lib.montage import create_targets_from_center, Target
  from typing import Optional, Dict, Any, List, Tuple
  from pathlib import Path
  import numpy as np

  class PtolemyHoleFinder(Finder):
      description: str = 'Hole finder that uses the ptolemy hole finder to find the holes at medium magnification.'
      reference: str = 'https://arxiv.org/abs/2112.01534'
      kwargs: Optional[Dict[str, Any]] = { 
          'model_path': Path(__file__).resolve().parents[1] / 'weights/211026_unet_9x64_ep6.torchmodel',
          'cuda': False,
          'height': 1024,
      }

      def run(self, montage, create_targets_method=create_targets_from_center)-> Tuple[List[Target], bool, Dict]:
          """Where the main logic for the algorithm is"""
          from .wrapper import ptolemy_find_holes         
          exposure = ptolemy_find_holes(montage, **self.kwargs)
          ptolemy_image_coords = np.array([exposure.crops.center_coords.y*exposure.scale,exposure.crops.center_coords.x*exposure.scale],dtype=int).transpose()
          targets = create_targets_method(ptolemy_image_coords,montage)
          return targets, True, {'lattice_angle': exposure.rot_ang_deg}
