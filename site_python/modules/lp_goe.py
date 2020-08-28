from openWB import *
from urllib import request, error
import json

class GO_E(DataProvider, Ladepunkt):
   """SMA Smart home Meter (or Energy Meter)"""
   def setup(self, config):
      self.ip = config.get(self.configprefix + '_ip')
      self.timeout = config.get(self.configprefix + '_timeout', 2)
      self.laststate = {}

   # DataProvier trigger
   def trigger(self):
      try:
         with request.urlopen('http://%s/status' % self.ip, timeout=self.timeout) as req:
            if req.getcode() != 200:
               self.core.logger.info('HTTP error on %s' % self.ip)
               return
            goe = json.loads(req.read().decode())
            self.laststate = goe
            u1 = int(goe['nrg'][0])   # V
            u2 = int(goe['nrg'][1])
            u3 = int(goe['nrg'][2])
            a1 = int(goe['nrg'][4])/10  # 0.1A
            a2 = int(goe['nrg'][5])/10
            a3 = int(goe['nrg'][6])/10
            power = int(goe['nrg'][11]) * 10  # 0.01kW

            # car status 1 Ladestation bereit, kein Auto
            # car status 2 Auto lädt
            # car status 3 Warte auf Fahrzeug
            # car status 4 Ladung beendet, Fahrzeug verbunden
            plugged = 0 if goe['car'] == '1' else 1
            charging = 1 if goe['car'] == '2' else 0
            self.core.sendData(DataPackage(self, {
               'llv1': u1, 'llv2': u2, 'llv3': u3,
               'lla1': a1, 'lla2': a2, 'lla3': a3,
               'llkwh': int(goe['eto'])/10,  # 0.1kWh
               'plugstat': plugged,
               'chargestat': charging,
               'llaktuell': power}))
      except error.URLError:
         pass

   def event(self):
      pass

   # Ladepunkt setter
   def set(self, ampere: int) -> None:
      self.core.logger.info("%i lädt mit %i Ampere" % (self.id, ampere))
      payload = {}
      aktiv = '1' if ampere > 0 else '0'
      if self.laststate['alw'] != aktiv:  # Allow
         payload['alw'] = aktiv
      if self.laststate['amp'] != str(ampere):  # Power
         payload['amp'] = str(ampere)

def getClass():
   return GO_E
