FROM nvidia/cuda:10.1-base-ubuntu18.04


ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
	python3-dev default-libmysqlclient-dev build-essential wget libglib2.0-0 ffmpeg libsm6 libxext6 curl && \
	apt-get clean && rm -rf /var/cache/apt/lists

RUN wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
	bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/miniconda3 && \
	rm Miniconda3-latest-Linux-x86_64.sh

RUN	mkdir /opt/logs/ /mnt/fake_scope/

ADD . /opt/smartscope/

#General environment variables
ENV IMOD_DIR=/usr/local/IMOD \	
	CTFFIND=/opt/smartscope/config/singularity/ctffind \
	APP=/opt/smartscope/ \
	AUTOSCREENDIR=/mnt/data/ \
	TEMPDIR=/tmp/ \
	LOGDIR=/opt/logs/ \
	AUTOSCREENSTORAGE=/mnt/longterm/ \
	TEMPLATE_FILES=/opt/Template_files/

ENV	ALLOWED_HOSTS=localhost \
	DJANGO_SETTINGS_MODULE=Smartscope.core.settings.server_docker \
	USE_STORAGE=True \
	USE_LONGTERMSTORAGE=False \
	USE_MICROSCOPE=True \ 
	DEFAULT_UMASK=003 \
	LOGLEVEL=INFO \
	DEBUG=False \
	TEST_FILES=/mnt/testfiles/ \
	MYSQL_HOST=db \
	MYSQL_PORT=3306 \
	MYSQL_USERNAME=root \
	MYSQL_ROOT_PASSWORD=pass \ 
	DB_NAME=smartscope \
	REDIS_HOST=cache \
	REDIS_PORT=6379 \
	USE_AWS=False 

ENV PATH=$PATH:/opt/smartscope/Smartscope/bin:$IMOD_DIR/bin:/opt/miniconda3/bin

RUN conda update -y conda && \
	yes | conda install cudatoolkit=10.2 cudnn=7.6 && \
	yes | pip install numpy==1.21.0 && \
	yes | pip install torch==1.8.2 torchvision==0.9.2 torchaudio==0.8.2 --extra-index-url https://download.pytorch.org/whl/lts/1.8/cu102 && \
	yes | pip install -r /opt/smartscope/config/docker/requirements.txt && \
	pip install -e /opt/smartscope/ --no-dependencies && \
	pip install /opt/smartscope/SerialEM-python --no-dependencies && \
	wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.15_RHEL7-64_CUDA10.1.sh && \
	yes | bash imod_4.11.15_RHEL7-64_CUDA10.1.sh -name IMOD && \
	rm imod_4.11.15_RHEL7-64_CUDA10.1.sh && conda clean --all


# create a non-root user
ARG USER_ID=1000
ARG GROUP_ID=1001

RUN addgroup --gid $GROUP_ID smartscope_group &&\
	useradd -m --no-log-init --system  --uid $USER_ID smartscope_user -g smartscope_group

RUN chown smartscope_user /mnt/ && \
	chown -R smartscope_user /opt/logs && \
	chown -R smartscope_user /mnt/fake_scope

USER smartscope_user

WORKDIR /opt/smartscope/

ENTRYPOINT [ "gunicorn", "-c", "/opt/smartscope/config/docker/gunicorn.conf.py" ]
