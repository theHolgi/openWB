#!/bin/bash
. /var/www/html/openWB/openwb.conf
dailyfile="/var/www/html/openWB/web/logging/data/daily/$(date +%Y%m%d)"

bezug=$(</var/www/html/openWB/ramdisk/bezugkwh)
einspeisung=$(</var/www/html/openWB/ramdisk/einspeisungkwh)
pv=$(</var/www/html/openWB/ramdisk/pvkwh)
ladeleistunglp1=$(</var/www/html/openWB/ramdisk/llaktuell)
ladeleistunglp2=$(</var/www/html/openWB/ramdisk/llaktuells1)
ladeleistunglp3=$(</var/www/html/openWB/ramdisk/llaktuells2)
llg=$(</var/www/html/openWB/ramdisk/llkwhges)
soc=$(</var/www/html/openWB/ramdisk/soc)
soc1=$(</var/www/html/openWB/ramdisk/soc1)
speicheri=$(</var/www/html/openWB/ramdisk/speicherikwh)
speichere=$(</var/www/html/openWB/ramdisk/speicherekwh)
speichersoc=$(</var/www/html/openWB/ramdisk/speichersoc)
llg=$(echo "$llg * 1000" | bc)
verbraucher1=$(</var/www/html/openWB/ramdisk/verbraucher1_wh)
verbraucher2=$(</var/www/html/openWB/ramdisk/verbraucher2_wh)
verbraucher3=$(</var/www/html/openWB/ramdisk/verbraucher3_wh)
verbrauchere1=$(</var/www/html/openWB/ramdisk/verbraucher1_whe)
verbrauchere2=$(</var/www/html/openWB/ramdisk/verbraucher2_whe)
ll4=$(</var/www/html/openWB/ramdisk/llkwhlp4)
ll5=$(</var/www/html/openWB/ramdisk/llkwhlp5)
ll6=$(</var/www/html/openWB/ramdisk/llkwhlp6)
ll7=$(</var/www/html/openWB/ramdisk/llkwhlp7)
ll8=$(</var/www/html/openWB/ramdisk/llkwhlp8)
ll4=$(echo "$ll4 * 1000" | bc)
ll5=$(echo "$ll5 * 1000" | bc)
ll6=$(echo "$ll6 * 1000" | bc)
ll7=$(echo "$ll7 * 1000" | bc)
ll8=$(echo "$ll8 * 1000" | bc)
echo $(date +%H%M),$bezug,$einspeisung,$pv,$ladeleistunglp1,$ladeleistunglp2,$ladeleistunglp3,$llg,$speicheri,$speichere,$verbraucher1,$verbrauchere1,$verbraucher2,$verbrauchere2,$verbraucher3,$ll4,$ll5,$ll6,$ll7,$ll8,$speichersoc,$soc,$soc1 >> $dailyfile.csv

netzabschaltunghz=0
if (( netzabschaltunghz == 1 )); then
hz=$(</var/www/html/openWB/ramdisk/llhz)
hz=$(echo "$hz * 100" | bc | sed 's/\..*$//')
netzschutz=$(</var/www/html/openWB/ramdisk/netzschutz)
	if (( netzschutz == 0 )); then
		if (( hz > 4500 )) && (( $hz < 5300 )); then
			if (( $hz > 5180 )); then
				lademodus=$(</var/www/html/openWB/ramdisk/lademodus)
				echo $lademodus > /var/www/html/openWB/ramdisk/templademodus
				echo 3 > /var/www/html/openWB/ramdisk/lademodus
				echo 1 > /var/www/html/openWB/ramdisk/netzschutz
			fi
			if (( hz < 4920 )); then
				lademodus=$(</var/www/html/openWB/ramdisk/lademodus)
				echo $lademodus > /var/www/html/openWB/ramdisk/templademodus
				echo 1 > /var/www/html/openWB/ramdisk/netzschutz
				(sleep $(shuf -i1-90 -n1) && echo 3 > /var/www/html/openWB/ramdisk/lademodus) &
			fi

		fi
	else
		if (( hz > 4500 )) && (( $hz < 5300 )); then
			if (( $hz < 5100 )); then
				templademodus=$(</var/www/html/openWB/ramdisk/templademodus)
				echo $templademodus > /var/www/html/openWB/ramdisk/lademodus
				echo 0 > /var/www/html/openWB/ramdisk/netzschutz
			fi
			if (( $hz > 4960 )); then
				templademodus=$(</var/www/html/openWB/ramdisk/templademodus)
				echo $templademodus > /var/www/html/openWB/ramdisk/lademodus
				echo 0 > /var/www/html/openWB/ramdisk/netzschutz
			fi
		fi
	fi
fi
if (( awattaraktiv == 1 )); then
	/var/www/html/openWB/runs/awattargetprices.sh
fi







