FROM pytorch/pytorch:1.8.1-cuda10.2-cudnn7-runtime


ENV DEBIAN_FRONTEND=noninteractive
ADD . /opt/smartscope/

RUN apt-get update && apt-get install -y \
	python3-dev default-libmysqlclient-dev build-essential wget libglib2.0-0 ffmpeg libsm6 libxext6 curl

# create a non-root user
ARG USER_ID=1000
ARG GROUP_ID=1001

RUN addgroup --gid $GROUP_ID smartscope_group &&\
	useradd -m --no-log-init --system  --uid $USER_ID smartscope_user -g smartscope_group &&\
	echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

RUN chown smartscope_user /mnt/ &&\
	chown smartscope_user /opt/ &&\
	mkdir /opt/logs/

#General environment variables
ENV IMOD_DIR=/usr/local/IMOD \	
	CTFFIND=/usr/local/ctffind \
	APP=/opt/smartscope/ \
	AUTOSCREENDIR=/mnt/data/ \
	TEMPDIR=/tmp/ \
	LOGDIR=/opt/logs/ \
	AUTOSCREENSTORAGE=/mnt/longterm/
ENV PATH=$PATH:/opt/smartscope/Smartscope/bin:$IMOD_DIR/bin

RUN wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.15_RHEL7-64_CUDA10.1.sh && \
	yes | bash imod_4.11.15_RHEL7-64_CUDA10.1.sh -name IMOD && \
	cp /opt/smartscope/config/singularity/ctffind /usr/local && \
	yes | conda install cudatoolkit=10.2 cudnn=7.6 && \
	yes | pip install -r /opt/smartscope/config/singularity/requirements.txt && \
	pip install -e /opt/smartscope/ --no-dependencies && \
	pip install -e /opt/smartscope/SerialEM-python --no-dependencies

USER smartscope_user

WORKDIR /opt/smartscope/