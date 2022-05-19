FROM pytorch/pytorch:1.8.1-cuda10.2-cudnn7-runtime


ENV DEBIAN_FRONTEND=noninteractive
# RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys A4B469963BF863CC && \
ADD . /opt/smartscope/
# RUN ls /opt/smartscope/

RUN apt-get update && apt-get install -y \
	python3-dev default-libmysqlclient-dev build-essential wget libglib2.0-0 ffmpeg libsm6 libxext6 curl sudo ssh	

# create a non-root user
ARG USER_ID=1000
RUN useradd -m --no-log-init --system  --uid ${USER_ID} smartscope_user -g sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

RUN chown smartscope_user /mnt/ && chown smartscope_user /opt/

RUN mkdir /opt/logs/

#General
ENV PATH=$PATH:/opt/smartscope/Smartscope/bin
ENV IMOD_DIR=/usr/local/IMOD
ENV PATH=$IMOD_DIR/bin:$PATH
ENV CTFFIND=/usr/local/ctffind
ENV APP=/opt/smartscope/
# ENV TEMPLATE_FILES=/opt/smartscope/Template_files
#Storage
ENV AUTOSCREENDIR=/mnt/data/
ENV TEMPDIR=/tmp/
ENV LOGDIR=/opt/logs/
#LongTermStorage
ENV AUTOSCREENSTORAGE=/mnt/longterm/

# WORKDIR /home/smartscope_user
RUN wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.15_RHEL7-64_CUDA10.1.sh && \
    yes | bash imod_4.11.15_RHEL7-64_CUDA10.1.sh -name IMOD && \
    cp /opt/smartscope/config/singularity/ctffind /usr/local

RUN yes | conda install cudatoolkit=10.2 cudnn=7.6 && \
	yes | pip install -r /opt/smartscope/config/singularity/requirements.txt && \
	pip install -e /opt/smartscope/ --no-dependencies && \
	pip install -e /opt/smartscope/SerialEM-python --no-dependencies

USER smartscope_user

WORKDIR /opt/smartscope/