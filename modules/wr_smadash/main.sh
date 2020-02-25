#!/bin/sh
BASEDIR=$(dirname "$0")

. $BASEDIR/../../openwb.conf
python3 $BASEDIR/read.py $tri9000ip
