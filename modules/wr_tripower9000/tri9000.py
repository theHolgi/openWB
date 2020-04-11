#!/usr/bin/python
import sys
from smadash import SMADASH
from modbuswr import ModbusWR
import openWBlib

ramdisk = '/var/www/html/openWB/ramdisk/'
wrs = []

def GetWR(host, typ):
   if typ == "modbus":
      instance = ModbusWR(host)
   else:  # if typ == "dash":
      instance = SMADASH(host)
   return instance

config = openWBlib.openWBconfig()
settings = [ 
   ['tri9000ip', 'wrsmatype'],
   ['wrsma2ip',  'wrsma2type'],
   ['wrsma3ip',  'wrsma3type'],
   ['wrsma4ip',  'wrsma4type'],
]

for nameconf, typeconf in settings:
   if config[nameconf] != "none":
      # Set default type
      if config[typeconf] == None:
         config[typeconf] = "modbus"
      try:
         wrs.append(GetWR(config[nameconf], config[typeconf]).read())
      except Exception as e:
          openWBlib.log("Error connecting to SMA inverter " + config[nameconf] + ": " + str(e)) 

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
with open(ramdisk + 'pvkwh', 'w') as f:
    f.write(str(totalgeneration))





