SerialEM setup
==============

In this section, you'll find guidance about how to set up SerialEM for SmartScope use. 

The idea is to generate a settings file with low-dose mode presets that will work well with the current version of SmartScope.

Calibrations
************

To ensure maximal precision of targeting and coordinate conversion, it is crucial that LM pixel size and rotation angle calibrations are verified before using SmartScope.
In the event of targeting problems between the atlas and squares, where squares are off-centered, it is very likely due these calibrations being off.

Low-dose Presets
****************

Search
#######
The search mag is set in LM mode to allow the capture of an entire square in a single acquisition.
On a K2 detector, we suggest using linear mode for search to maximize contrasts.

View
#######
The view mag is using a low SA mode magnification to view a few holes. It is currently only used to re-center on a hole.

Preview
#######
Currently, Preview is used to acquire the main high-magnification acquisition because of initial limitations with SerialEM.
Ensure that dose-fraciionation and exposure times are set for that purpose.

Record
#######
(Under deprecation) Currenly used to acquire the atlas. Atlas is acquired outside of low-dose mode and current scripting commands for acquiring montage will use Record by default.

Focus/Trial
############
Used for autofocus and drift correction. For autofocus, the specified image-shift position that is set will be used for each sample. We suggest changing it when doing data collection to ensure that the focus area illuminates between holes.

Non Low-dose presets
********************

The easiest way to set up for the atlas is to create an imaging state for mont-mapping. This way, when acquiring the atlas, it will use the mont-map setting instead of Record.

.. note:: There is a workaround that needs to be executed prior to starting SmartScope for this to happen successfully. `Click here for more details <>`_



