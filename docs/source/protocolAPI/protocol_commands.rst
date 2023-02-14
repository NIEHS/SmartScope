Protocol Commands
=================

Protocol commands are used in the :code:`protocol.yaml` files as building block for the acquisition. Different protocols can be built with different combinations of commands.

All protocol commands have the same input arguments:

- scope: The microscope interface instance
- params: The data collection parameters specified during session setup.
- instance: The instance of the database object that is being worked on. Atlas, Square, Hole, Highmag object


Available commands
##################

.. automodule:: Smartscope.core.protocol_commands
    :members: