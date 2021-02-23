#!/bin/bash

param=$1

if [ "start" == "$param" ] ; then
      sudo -u encoder python /home/user/watchbucket/watchstatusd.py /home/user/watchbucket/logs/run/watchstatus.pid /home/user/watchbucket/logs/watchstatus.log start
      sudo -u encoder python /home/user/watchbucket/watchbucketd.py /home/user/watchbucket/logs/run/watchbucket.pid /home/user/watchbucket/logs/watchbucket.log start
      exit 0;
elif [ "stop" == "$param" ] ; then
      sudo -u encoder python /home/user/watchbucket/watchstatusd.py /home/user/watchbucket/logs/run/watchstatus.pid /home/user/watchbucket/logs/watchstatus.log stop
      sudo -u encoder python /home/user/watchbucket/watchbucketd.py /home/user/watchbucket/logs/run/watchbucket.pid /home/user/watchbucket/logs/watchbucket.log stop
      exit 0;
elif [ "status" == "$param" ] ; then
      sudo -u encoder python /home/user/watchbucket/watchstatusd.py /home/user/watchbucket/logs/run/watchstatus.pid /home/user/watchbucket/logs/watchstatus.log status
      sudo -u encoder python /home/user/watchbucket/watchbucketd.py /home/user/watchbucket/logs/run/watchbucket.pid /home/user/watchbucket/logs/watchbucket.log status
      exit 0;
elif [ "restart" == "$param" ] ; then
      sudo -u encoder python /home/user/watchbucket/watchstatusd.py /home/user/watchbucket/logs/run/watchstatus.pid /home/user/watchbucket/logs/watchstatus.log restart
      sudo -u encoder python /home/user/watchbucket/watchbucketd.py /home/user/watchbucket/logs/run/watchbucket.pid /home/user/watchbucket/logs/watchbucket.log restart
      exit 0;
else
      echo "no such command $param"
      exit 1;
fi