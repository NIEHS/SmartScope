Plugin Interface
################

SmartScope aims at connecting new algorithms developped by the Cryo-EM community in the easiest possible way. This section aims at explaining the basics of the plugin interface.

.. note:: 

    The plugin interface will likely evolve in the near future as we integrate new features. It is worth revisiting this page often for the latest additions and changes.


Types of algorithms
===================

SmartScope has 3 different types of plugins or algorithms that perform different tasks:

- Finders

    As the name specifies, this category is used for algrithm that detect features in an image. These methods usually return list of coordinates.

- Classifiers

    This category is used to classifiy features that were detected with a Finder. These algorithms have a finite number of labels that can be assigned. For example, `good`, `cracked`, `empty`

- Selectors

    This category, unlike the classifiers, doesn't have a finity number of classes. Can be used for clustering or providing values such as ice thickness or other scoring metric.



