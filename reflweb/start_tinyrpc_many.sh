#!/bin/bash

for (( c=0; c<$2; c++))
do
    p=$(($1+$c));
    nohup python server_tinyrpc.py $p > /dev/null 2>&1&
done
