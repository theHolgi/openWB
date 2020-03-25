#!/usr/bin/python
import sys
from smadash import SMADASH
from modbuswr import ModbusWR

ramdisk = '/var/www/html/openWB/ramdisk/'
wrs = []

if len(sys.argv) > 1:
   wrs.append(SMADASH(sys.argv[1]).read())
if len(sys.argv) > 2 and sys.argv[2] != "none":
   wrs.append(ModbusWR(sys.argv[2]).read())
if len(sys.argv) > 3 and sys.argv[3] != "none":
   wrs.append(ModbusWR(sys.argv[3]).read())
if len(sys.argv) > 4 and sys.argv[4] != "none":
   wrs.append(ModbusWR(sys.argv[4]).read())

totalpower, totalgeneration = 0,0
index = 1
for w,g in wrs:
   totalpower += w
   totalgeneration += g
   with open(ramdisk + 'pvwatt%i' % index, 'w') as f:
     f.write(str(w))
   with open(ramdisk + 'pvkwhk%i' % index, 'w') as f:
     f.write(str(g))
   index += 1
   
with open(ramdisk + 'pvwatt', 'w') as f:
    f.write(str(totalpower))
with open(ramdisk + 'pvkwhk', 'w') as f:
    f.write(str(totalgeneration))





