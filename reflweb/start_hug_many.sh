#!/bin/bash

UWSGI_BIN=/home/bbm/.local/bin/uwsgi

for (( c=0; c<$2; c++))
do
    p=$(($1+$c));
    $UWSGI_BIN --socket "127.0.0.1:$p" --wsgi-file server_hug.py --callable __hug_wsgi__  -d /dev/null
done
