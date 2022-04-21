# FROM javert899/pm4py as base

FROM python:3.8 as base
MAINTAINER Gyunam Park

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install nano vim
RUN apt-get -y install git
RUN apt-get -y install zip unzip
RUN apt-get -y install gcc gfortran python-dev libopenblas-dev liblapack-dev
RUN apt-get -y install g++ libboost-all-dev libncurses5-dev wget
RUN apt-get -y install libtool flex bison pkg-config g++ libssl-dev automake
RUN apt-get -y install libjemalloc-dev libboost-dev libboost-filesystem-dev libboost-system-dev libboost-regex-dev python3-dev autoconf flex bison cmake
RUN apt-get -y install libxml2-dev libxslt-dev libfreetype6-dev libsuitesparse-dev

FROM base as builder

RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt

# Upgrade installed packages
RUN apt-get update && apt-get upgrade -y && apt-get clean

# Install git
RUN apt-get install -y git && apt-get install -y libpq-dev

# Install libgraphviz
RUN apt-get install -y libgraphviz-dev pkg-config

# Install requirements
RUN pip install --upgrade pip
RUN pip install --target=/install -r /requirements.txt

# change stage to use copy from below?
FROM base

COPY --from=builder /install /usr/local

# Change working directory to new user
WORKDIR /home/dtween

ENV PYTHONPATH "${PYTHONPATH}:/install:/home/dtween:/usr/local:/home/dtween"

COPY . .


# Add user for safe celery execution
RUN useradd -ms /bin/bash dtweenworker

# Install git
#RUN apt-get install -y git && apt-get install -y libpq-dev

# We copy just the requirements.txt first to leverage Docker cache


# Get gcc
#ENV DEBIAN_FRONTEND noninteractive
#RUN apt-get update && \
#    apt-get -y install gcc mono-mcs && \
#    rm -rf /var/lib/apt/lists/*

# Install dependencies of Flask project
#RUN pip install -e .

# WORKDIR /home/dtween/backend/tasks

# Set the rest of environment variables
ENV FLASK_ENV="${FLASK_ENV}" \
    PYTHONPATH="${PYTHONPATH}:/home/dtween/src:/home/dtween/backend:" \
    UID_DTWEEN="$(id -u)"

# Only expose port 8050 for dash application
EXPOSE 8050

