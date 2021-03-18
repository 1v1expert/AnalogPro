#!/usr/bin/env bash

docker rm -f analog-base

docker run -d --name analog-base -v /root/analog_data:/var/lib/postgresql/data --env="POSTGRES_PASSWORD=@WSX2wsx123" --env="POSTGRES_DB=AnalogDB" --env="POSTGRES_USER=Analog" -p 127.0.0.1:5432:5432 postgres:12
