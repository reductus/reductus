FROM python:3.5
RUN apt-get update && apt-get install -y --no-install-recommends \
		gcc \
	&& rm -rf /var/lib/apt/lists/*
RUN pip install uwsgi hug pytz numpy h5py redis msgpack-python
COPY . /reduction/
RUN cd /reduction && rm -rf build/ && python setup.py install
COPY docker-compose/gevent/config.py /reduction/reflweb
EXPOSE 8001
WORKDIR /reduction/reflweb
ENTRYPOINT ["uwsgi", "--uid", "1000", "--gid", "1000", "--http-socket", "0.0.0.0:8001", "--wsgi-file", "server_hug.py", "--callable", "__hug_wsgi__"]
