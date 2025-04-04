#!/bin/bash

PYTHON=python3
ROOT_DIR=$PWD
LOGS_DIR=${ROOT_DIR}/logs
NAME=watchbucket
SCRIPT=${ROOT_DIR}/${NAME}/${NAME}_daemon.py
PID_FILE=${LOGS_DIR}/run/${NAME}.pid
LOG_FILE=${LOGS_DIR}/${NAME}.log

$PYTHON $SCRIPT $PID_FILE $LOG_FILE $1
