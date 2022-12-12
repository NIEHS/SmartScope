Accessing the REST API through the browser
##########################################

SmartScope uses `Django REST framework<https://www.django-rest-framework.org/>`_. It provides a web portal to access the REST API and interact with the datase entry.

The web-portal is the easiest way to change a value for something that is either misbehaving or doesn't yet have a proper built-in function in the smartscope interface.

It can also be used to query elements again specific filters.

The API is reached at the `<http://smartscopeURL/api/>`_. It has endpoints for most database tables:

- users
- groups
- holetypes
- meshsizes
- meshmaterial
- microscopes
- detectors
- sessions
- grids
- atlas
- squares
- holes
- highmag

Examples
--------

Manually changing the status of an area
=======================================

To manually skip a square or hole that is in a bad state and prevent SmartScope from progressing, it is possible to use the web portal to force the area to be skipped.

#. Identify the area id

  #. Right-clik on the smartscope insterface and select inspect

  #. Select the inspection tool

    .. figure:: /_static/inspect_html.png
     :width: 70%
     :align: center
     :figclass: align-center

  #. Hover on the area of interest and look at the html element id

    .. figure:: /_static/inspect_id.png
     :width: 80%
     :align: center
     :figclass: align-center

  #. Copy the id and type the url for a hole in this case. :code:`http://smartscopeURL/api/holes/AR1_1209_1_square64_4s1ba4UbDD`

#. You are now seeing the database object corresponding to this area.

  .. figure:: /_static/restAPI_object.png
   :width: 70%
   :align: center
   :figclass: align-center

#. From this page, it is possible to unselect the element, change its status, or even delete the element entirely. Simply make the change in the form and click the PUT button.

Query holes from a squares that have not been selected for acquisition
======================================================================

For example, we have a square of id `AR1_1209_1_square64KHuPyJmbQGR` and we want a list of the holes that were not yet selected or acquired.

We can use query filters in the url to the REST API. :code:`http://smartscopeURL/api/holes/?square_id=AR1_1209_1_square64KHuPyJmbQGR&status=null`

It is also possible to use the REST API web portal at the :code:`http://smartscopeURL/api/holes/` endpoint and filter from there:

.. figure:: /_static/restAPI_filter.png
 :width: 80%
 :align: center
 :figclass: align-center

.. figure:: /_static/restAPI_filterlist.png
 :width: 80%
 :align: center
 :figclass: align-center