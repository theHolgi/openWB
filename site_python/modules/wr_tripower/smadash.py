#!/usr/bin/python3

import sys
from urllib import request
import ssl
import json

def getVal(result, id):
   if result[id]['1'][0]['val'] is None:
      return 0
   else:
      return int(result[id]['1'][0]['val'])

class SMADASH:
   """
   Read values from SMA inverter from the dashboard
   In order to work, inverter must show the current production without login.
   """
   valueURL = '/dyn/getDashValues.json'

   def __init__(self, ip): 
      self.host = ip

   def read(self):
      power, generation = 0, 0
      context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
      context.verify_mode = ssl.CERT_NONE
      try:
         with request.urlopen('https://' + self.host + self.valueURL, context = context) as r:
            if r.getcode() == 200:
               content = json.loads(r.read().decode())
               for unitName, unitResult in content['result'].items():
                  # powerOut = getVal(unitResult, '6100_40463600')  # grid Supply
                  # powerIn  = getVal(unitResult, '6100_40463700')  # grid Consumption
                  power    = getVal(unitResult, '6100_40263F00')  # PV generation in W
                  if power is None:
                     power = 0
                  else:
                     power = -int(power) # generated power is negative
                  generation = getVal(unitResult, '6400_00260100')/1000  # Total yield in Wh
      except:
         pass
      return power, generation
if __name__ == '__main__':
   power, generation = SMADASH(sys.argv[1]).read()
   print("Current power: %sW; Total generation: %.2fkWh" % (power, generation/1000.0))

