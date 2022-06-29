How to prepare SerialEM
========================

There are a few steps that are requied within SerialEM prior to running SmartScope.

#. Load the SmartScope settings file that contains the Low-dose presets and imaging conditions. Guidelines on how to set up this file are found in the `setup section <../setup/serialem.html>`_.


#. Align beam and correct astigmatism and coma, as per your usual procedures.


#. Align your Record -> View -> Search image-shifts.
    
    This is the same way as for any SerialEM experiment. It applies image shift to keep the registration between the magnification levels. This ensures proper targeting.


#. Open a navigator and the imaging states.

    You should have a mont-map imaging state pre-saved. Double-click it to enable it.


#. Go to file -> setup montage

    In the dialog, click the use montage mapping, not record option.

    Click ok until prompted to save a file. Don't save any file and cancel. The options in the dialog will be saved.

    .. note:: We are aware that this is an odd procedure but it avoids many errors and warnings.


#. You're all set!

    Refer on how to prepare the SmartScope run from the web page.