#!/bin/bash
BASEDIR=$(dirname "$0")
RAMDISK=$BASEDIR/../../ramdisk

. $BASEDIR/../../openwb.conf

if [[ $wrsmatype == "webbox" ]]; then
	rekwh='^[-+]?[0-9]+\.?[0-9]*$'
	boxout=$(curl --silent --connect-timeout 3 -H "Content-Type: application/json" -X POST -d RPC='{"version": "1.0","proc": "GetPlantOverview","id": "1","format": "JSON"}' http://$tri9000ip/rpc)
	if [[ $? == "0" ]] ; then
		pvwatt=$(echo $boxout | jq -r '.result.overview[0].value ' | sed 's/\..*$//')
		pvwatt=$(( pvwatt * -1 ))
		pvkwh=$(echo $boxout | jq -r '.result.overview[2].value ')
		pvwh=$(echo "scale=0;$pvkwh * 1000" |bc)
		if [[ $pvwh =~ $rekwh ]]; then
			echo $pvwh > $RAMDISK/pvkwh
		fi
		if [[ $pvkwh =~ $rekwh ]]; then
			echo $pvwatt > $RAMDISK/pvwatt
		fi
	fi




else
	python $BASEDIR/tri9000.py 
fi




pvwatt=$(<$RAMDISK/pvwatt)
echo $pvwatt
ekwh=$(<$RAMDISK/pvkwh)


pvkwh=$(echo "scale=3;$ekwh / 1000" |bc)
echo $pvkwh > $RAMDISK/pvkwh





