# syntax=docker/dockerfile:experimental
FROM python:3
ENV PYTHONUNBUFFERED 1
RUN mkdir /analog
WORKDIR /analog
COPY requirements/requirements.txt /analog/
RUN pip install -r requirements.txt
COPY . /analog/