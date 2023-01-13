Automatic protocol selection
============================

When setting up a SmartScope run, a protocol can be selected for each grid to screen. There is also an :code:`'auto'` option. 
The behavior of this option can be managed from the :code:`config/smartscope/default_protocols.yaml`.

At the moment, the synthax for the automated selection is quite limited and will improve over time.

First, here's how the file looks like:

.. literalinclude:: ../../../config/smartscope/default_protocols.yaml


It contains a list of conditions that will yield to the selection of a given protocol.

Synthax
#######

Each entry in the file has 3 sections:

conditions
----------

A list of conditions that need to be met for a protocol to be selected.

Each condition contains a :code:`key` and a :code:`value`. If the condition needs to be evaluating on a false response, the valued can be prefixed with :code:`!__`

mode
----

Can have two values: :code:`any` or :code:`all` whether any or all conditions specified in the conditions needs to be met

protocol
--------

The protocol that will be used if the conditions are met.