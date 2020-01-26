#!/bin/bash

. /var/www/html/openWB/openwb.conf


illwh=$(cat /run/shm/em-$smaemdllid-pconsumecounter)
llwatt=$(cat /run/shm/em-$smaemdllid-pconsume |sed 's/\..*$//')
bezuga1=$(cat /run/shm/em-$smaemdllid-p1consume |sed 's/\..*$//')
bezuga2=$(cat /run/shm/em-$smaemdllid-p2consume |sed 's/\..*$//')
bezuga3=$(cat /run/shm/em-$smaemdllid-p3consume |sed 's/\..*$//')

echo $illwh > /var/www/html/openWB/ramdisk/llkwh
echo $llwatt > /var/www/html/openWB/ramdisk/llaktuell
echo $bezuga1 > /var/www/html/openWB/ramdisk/lla1
echo $bezuga2 > /var/www/html/openWB/ramdisk/lla2
echo $bezuga3 > /var/www/html/openWB/ramdisk/lla3


