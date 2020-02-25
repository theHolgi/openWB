#!/usr/bin/python3
import urllib3
import json

host = 'https://sma.garnix.de'
valueURL = '/dyn/getDashValues.json'

urllib3.disable_warnings()
http = urllib3.PoolManager(cert_reqs='CERT_NONE')
r = http.request('GET', host + valueURL)
if r.status == 200:
   content = json.loads(r.data.decode('utf-8'))
   for unitName, unitResult in content['result'].items():
      powerOut = int(unitResult['6100_40463600']['1'][0]['val']) # Generation
      powerIn = int(unitResult['6100_40463700']['1'][0]['val'])  # Consumption
      generation = unitResult['6100_40263F00']['1'][0]['val']
      if generation is None:
         generation = 0
      else:
         generation = int(generation)
      print(generation)
