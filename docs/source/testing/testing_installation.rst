Test commands for SmartScope
############################

SmartScope bundles a few testing commands that are useful for troubleshooting. 
If you're using the docker installation, you may either log into the container with :code:`docker exec -it smartscope /bin/bash` or preface any of the following commands with :code:`docker exec smartscope ADD_COMMAND_HERE`.

Testing GPU capabilities
--------------------------

If you added a gpu passthrough to your smartscope installation and want to see if it works properly, use the following command which will print True or False:

.. code-block:: shell-session

   $ smartscope.py is_gpu_enabled
   
   GPU enabled: True 


Testing the connection to serialEM
##################################

To quickly test if you can connect from python to SerialEM, you can use the following commands and replace IP by the gatan PC address and port by 48888 or the port specified in your :code:`SerialEMproperties.txt`.

From our examples above, the Talos Arctica IP would be 192.168.0.32 and port would be 48888.

.. code-block:: shell-session

   $ smartscope.py test_serialem_connection IP port

    ### EXAMPLE ###
   $ smartscope.py test_serialem_connection 192.138.0.32 48888

If the connection is successful, a :code:`Hello from smartscope` message should appear in the SerialEM log window.


List plugins and protocols
##########################

If you'd like to make sure which plugins and protocols are set up, you can use the following commands:

.. code-block:: shell-session

   $ smartscope.py list_plugins
      ...

   $ smartscope.py list_protocols

   ############################################################
   NegativeStain:

         squareFinders=['AI square finder'] holeFinders=['Regular pattern'] highmagFinders=[] squareSelectors=['Size selector'] holeSelectors=['Graylevel selector']
   ############################################################

   ############################################################
   SPA:

         squareFinders=['AI square finder'] holeFinders=['AI hole finder', 'Regular pattern'] highmagFinders=['Ptolemy hole finder'] squareSelectors=['Size selector'] holeSelectors=['Graylevel selector']
   ############################################################