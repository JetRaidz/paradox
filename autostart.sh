#!/bin/bash

while true;
do
    ./startup.sh "$@"
    sleep 10
    echo "PARADOX AUTOSTART: RESTARTING WITH ARGS '$@'"
done;
