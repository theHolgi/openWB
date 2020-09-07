from openWB import *
from urllib import request, error
import json
from threading import Thread


class GO_E_SET(Thread):
   """Threaded parameter setting on a GO-E charger"""
   def __init__(self, url, timeout):
      super().__init__()
      self.url = url
      self.timeout = timeout

   def run(self):
      try:
         with request.urlopen(self.url, timeout=self.timeout) as req:
            pass
      except error.URLError:
         pass


class GO_E(DataProvider, Ladepunkt):
   """GO-E wallbox"""
   def setup(self, config):
      self.ip = config.get(self.configprefix + '_ip')
      self.timeout = config.get(self.configprefix + '_timeout', 2)
      self.laststate = {}
      self.plugged = False
      self.charging = False

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
            self.actP = int(goe['nrg'][11]) * 10  # 0.01kW

            # car status 1 Ladestation bereit, kein Auto
            # car status 2 Auto lädt
            # car status 3 Warte auf Fahrzeug
            # car status 4 Ladung beendet, Fahrzeug verbunden
            self.plugged = goe['car'] != '1'
            self.charging = goe['car'] == '2'
            self.core.sendData(DataPackage(self, {
               'llv1': u1, 'llv2': u2, 'llv3': u3,
               'lla1': a1, 'lla2': a2, 'lla3': a3,
               'llkwh': int(goe['eto'])/10,  # 0.1kWh
               'plugstat': self.plugged,
               'chargestat': self.charging,
               'llaktuell': self.actP,
               'lpphasen': self.phasen}))
            # restzeitlp
      except:
         pass

   def event(self):
      pass

   def powerproperties(self) -> PowerProperties:
      if not self.plugged:
         return PowerProperties(0, 0, 0)
      else:
         return PowerProperties(minP=self.minP,
                                maxP=self.maxP,
                                inc=self.phasen*230)

   # Ladepunkt setter
   def set(self, power: int) -> None:
      ampere = power2amp(power, self.phasen)
      aktiv = '1' if ampere > 0 else '0'
      self.core.sendData(DataPackage(self, {'llsoll': ampere, 'ladestatus': aktiv}))
      if self.laststate['alw'] != aktiv:  # Allow
         GO_E_SET('http://%s/mqtt?payload=alw=%s' % (self.ip, aktiv), self.timeout).start()
      if self.laststate['amp'] != str(ampere):  # Power
         GO_E_SET('http://%s/mqtt?payload=amp=%s' % (self.ip, ampere), self.timeout).start()

def getClass():
   return GO_E
