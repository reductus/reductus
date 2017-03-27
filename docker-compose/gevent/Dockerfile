FROM python:2.7
RUN apt-get update && apt-get install -y --no-install-recommends \
		gcc git \
	&& rm -rf /var/lib/apt/lists/*
RUN pip install wheel gevent werkzeug tinyrpc pytz numpy h5py redis msgpack-python
COPY . /reduction/
RUN cd /reduction && rm -rf build/ && python setup.py install
COPY docker-compose/gevent/config.py /reduction/reflweb
EXPOSE 8001
WORKDIR /reduction/reflweb
ENTRYPOINT ["python", "server_tinyrpc.py"]
