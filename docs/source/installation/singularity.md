# Installation with Singularity

This section describes the step for installation with Singularity/Apptainer.
The examples detail the steps for Ubuntu 20.04 but are similar for other ditributions

*Note: For simplicity, the singularity version of SmartScope only runs on cpu. Version using CUDA will come at a later point. Performance is not greatly affected since it's using pre-trained models*

To learn how to use singularity, please refer to their [detailed documentation](https://sylabs.io/guides/3.0/user-guide/index.html)

## Installation of singularity
Singularity offers pre-compiled versions for the most commonly used linux distributions in the [release section of their github](https://github.com/sylabs/singularity/releases).

Smartscope has been tested on SingularityCE 3.9.4, and should require at least version 3.1.

To download and install singularity:
```
wget https://github.com/sylabs/singularity/releases/download/v3.9.4/singularity-ce_3.9.4-focal_amd64.deb
sudo apt install ./singularity-ce_3.9.4-focal_amd64.deb
# Test the installation
singularity --version
# Should output
# singularity-ce version 3.9.4-focal
```

## Common steps to all the singularity installs

This sections describe the basic setup for installation with singularity.

### Setting up a local account to run SmartScope (OPTIONAL)

To avoid potential permission conflicts, it is recommended to always run the SmartScope server from the same account.
Creating a local account is the best way to achieve this. As an example, we're creating the smartscope_user account:

```
sudo useradd smartscope_user
```

### Create a directory 
Fist, create a directory to store all the files and travel to it.
```
mkdir /where/you/want/smartscope
cd /where/you/want/smartscope
```

### Mount binds

Mount binds are used in singularity to connect the container to the host filesystem for persistent storage. This ensures that the data being generated from the container will remain if the container is shut down. There are a few required and optional paths that must be defined to run SmartScope properly:

Description | Location in the container | Required/Optional
---|---|---
SmartScope repository location | /opt/smartscope/ | required
Logging directory | /opt/log/ | required
Data directory | /mnt/data/ | required
Microscope directory | /mnt/scope/ | required (1 per scope)*
Database directory | /opt/mariadb/ | required
Long term storage | /opt/longterm/ | optional
*If multiple microscope are going to be used, one bind per microscope needs to be specified and have unique names. The following example uses scope1 and scope2 but it could be any other name. i.e. /mnt/scope1/:/path/to/scope/,/mnt/scope2/:/path/to/scope2/

To specify where each of these paths are going to be located on the host computer, a pair needs to be created. For example, if the SmartScope directory is in /home/user/Smartscope and the data will be saved in /data/, the mounts would be defined as:
```
SINGULARITY_BINDS=/home/user/Smartscope:/opt/smartscope,/data/:/mnt/data/
```
To avoid having to write the list of binds everytime from the command line, the SINGULARITY_BINDS enviroment variable can be set and the binds will be read from there.
This variable can be added to the smartscope_user .bashrc file
```bash
#open ~/.bashrc with a text editor
#scroll to the botton of the file and add the following line
export SINGULARITY_BINDS=/home/user/Smartscope:/opt/smartscope,/data/:/mnt/data/,/data/log/:/opt/logs/,/data/smartscopedb/:/mnt/mariadb/
#Re-source the .bashrc to load the changes
source ~/.bashrc
```

## Download the SmartScope singularity image and repository


The smartscope image and the different definition files are available for download [here](#)

There are a few options to choose on how smartscope can be installed:
- *(Easiest)* Full stack (web-interface, smartscope worker, redis, mariadb)
    Contains everything to run smartscope.
- Mininal package (web-interface, smartscope worker, redis)
    Contains the minimal core for smartscope. Will need to be connected to a mariadb server.
- Worker only (smartscope worker)
    If you want to use a different computer to run the smartscope workflow and the webserver. Will need to connect to a mariadb server and one of the other two installations above.

*Note: Building images require root access to the system but pre-built images are available for download.*

Then, clone the code from the git repository
```
#This page has not yet been made publicly available
git clone https://github.com/NIEHS/SmartScope
```

## Edit the environment file

First, copy the template environement file
```
cp Smartscope/config/singularity/env-template.sh Smartscope/config/singularity/env.sh
```
Using a test editor, open the `env.sh` configuration file and edit the variables to suit your needs.
The file is located in Smartscope/config/singularity/singularityConf.sh
The content of this file is detailed [here](./configFile_singularity.html)

## Installing the "Full Stack"

This way of installing smartscope is by far the simplest as all the dependencies are included. 
The caveats is that everything will run from a single computer and cannot use port 80 and 443 for regular http/https protocols. 

### Install the initial database and set up the secret key

Along with initiating the database, the following script will generate a 50-character random key. This key is needed to hash the session tokens to ensure proper website security. This is required for the webserver to run properly. The secret key file will be saved in the same directory as the database. 
```
singularity exec --writable-tmpfs smartscope-full.sif /opt/smartscope/config/singularity/installDB.sh
```

### Run the container
You can find more information about how to run singularity instance on the [singularity documentation](https://sylabs.io/guides/3.0/user-guide/running_services.html)

```
singularity instance start --writable-tmpfs smartscope-full.sif smartscope
```
If everything has been successfull, the server should be available at [http://localhost:48000](http://localhost:48000)
The default account is:
    username: admin
    password: admin

We suggest using the admin portal(link coming soon) to change the password

### To stop the container

```
singularity instance stop smartscope
```
