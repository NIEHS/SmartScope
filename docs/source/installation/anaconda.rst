Installation with Anaconda/Miniconda
####################################

.. warning:: This Section is still a work in progress and will only work with SmartScope >=0.62

Requirements
************

- Anaconda or Miniconda
- IMOD
- Other system dependencies:

    .. code-block:: bash

        # For ubuntu
        sudo apt-get install default-libmysqlclient-dev build-essential libglib2.0-0 ffmpeg libsm6 libxext6 


Setting up the SmartScope environment
*************************************

#. Clone or download the `git repository <https://github.com/NIEHS/SmartScope>`_ and navigate to the directory

    .. code-block:: bash

        git clone https://github.com/NIEHS/SmartScope.git
        cd SmartScope

#. Create the environment and install the python dependencies

    .. code-block:: bash

        conda create -n smartscope python=3.9 cudatoolkit=10.2 cudnn=7.6 numpy==1.21
        conda activate smartscope
        pip install torch==1.8.2 torchvision==0.9.2 torchaudio==0.8.2 --extra-index-url https://download.pytorch.org/whl/lts/1.8/cu102
        pip install -r config/docker/requirements.txt
        pip install -e . --no-dependencies
        pip install ./SerialEM-python --no-dependencies

#. Set up the environment variables

    #. Create your own copy of the environment template
    
        .. code-block:: bash

            cp config/conda/conf-template.env conf.env
    
    #. Open the file in a text editor and fill up the variables to suit your system

        `Click here <./environment.html>`_ for details about the variables.


    


        