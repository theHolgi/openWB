from openWB import DataPackage
from urllib import request
import json

from threading import Thread
from openWB.Modul import *


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
      except:
         pass


class GO_E(Ladepunkt):
   """GO-E wallbox"""
   def setup(self, config):
      self.ip = config.get(self.configprefix + '_ip')
      self.timeout = config.get(self.configprefix + '_timeout', 2)
      self.laststate = {}
      super().setup(config)

   def loop(self):
      try:
         with request.urlopen('http://%s/status' % self.ip, timeout=self.timeout) as req:
            if req.getcode() != 200:
               self.core.logger.info('HTTP error on %s' % self.ip)
               return
            goe = json.loads(req.read().decode())
            self.laststate = goe
            self.actP = int(goe['nrg'][11]) * 10  # 0.01kW
            
            # goe['car']: 1 Ladestation bereit, kein Auto
            #             2 Auto lädt
            #             3 Warte auf Fahrzeug
            #             4 Ladung beendet, Fahrzeug verbunden
            self.send({
               'llv1': int(goe['nrg'][0]),    'llv2': int(goe['nrg'][1]),    'llv3': int(goe['nrg'][2]),    # [V]
               'lla1': int(goe['nrg'][4])/10, 'lla2': int(goe['nrg'][5])/10, 'lla3': int(goe['nrg'][6])/10, # [0.1A]
               'llpf1': int(goe['nrg'][12]),  'llpf2': int(goe['nrg'][13]),  'llpf3': int(goe['nrg'][14]),  # %
               'llkwh': int(goe['eto'])/10,  # [0.1kwh]
               'plugstat': goe['car'] != '1',
               'chargestat': goe['car'] == '2',
               'llaktuell': self.actP})
            # restzeitlp
      except:  # e.g. socket.timeout
         self.send({})

   def powerproperties(self) -> PowerProperties:
      if not self.plugged:
         return PowerProperties(0, 0, 0)
      else:
         return PowerProperties(minP=self.minP,
                                maxP=self.maxP,
                                inc=self.phasen*230)

   # Ladepunkt setter
   def set(self, power: int) -> None:
      self.setP = power
      ampere = power2amp(power, self.phasen)
      self.core.logger.info(f"GO-E request {power}W ({ampere}A)")
      aktiv = 1 if ampere > 0 else 0
      self.core.sendData(DataPackage(self, {'llsoll': ampere, 'ladestatus': aktiv}))
      if self.laststate['alw'] != str(aktiv):  # Allow
         GO_E_SET('http://%s/mqtt?payload=alw=%s' % (self.ip, aktiv), self.timeout).start()
      if self.laststate['amp'] != str(ampere):  # Power
         GO_E_SET('http://%s/mqtt?payload=amp=%s' % (self.ip, ampere), self.timeout).start()


def getClass():
   return GO_E
