FROM devhub-docker.cisco.com/iox-docker/ir1101/base-rootfs
WORKDIR /code

RUN opkg update && opkg install python3 python3-pip
RUN cd /usr/bin && ln -s python3 python && cd -
RUN easy3_install pip

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY config.py .
COPY codec_ws.py .
COPY codec_ui.py .

CMD ["python3", "./codec_ws.py"]
