from time import sleep

import logging
import queue
from socket import socket
from urllib import request
import json

from threading import Thread
from openWB.Modul import Ladepunkt, PowerProperties, power2amp
from openWB.Scheduling import Scheduler


class GO_E_SET(Thread):
   """Threaded parameter setting on a GO-E charger"""
   def __init__(self, url: str, timeout: int, master: Ladepunkt):
      super().__init__()
      self.url = url
      self.master = master
      self.timeout = timeout
      self.requests = queue.Queue()
      self.last = {}

   def request(self, key: str, value: int) -> None:
      self.requests.put((key, value))

   def run(self) -> None:
      while True:
         key, value = self.requests.get()
         try:
            with request.urlopen(self.url + "?payload=%s=%s" % (key, value), timeout=self.timeout) as req:
               self.last[key] = value
               data = {}
               if key == 'alw':
                  data['ChargeStatus'] = value
                  if value == 0:
                     data['Areq'] = value
               elif key == 'amx':
                  data['Areq'] = value
               self.master.send(data)
         except Exception as e:
            logging.exception("GO-E say Bumm!", exc_info=e)


class GO_E(Ladepunkt):
   """GO-E wallbox"""
   cycletime = 5
   def setup(self, config):
      self.ip = config.get(self.configprefix + '_ip')
      self.timeout = config.get(self.configprefix + '_timeout', 2)
      self.laststate = {}
      self.setter = GO_E_SET('http://%s/mqtt' % self.ip, self.timeout, self)
      self.setter.start()
      super().setup(config)

   def loop(self):
      try:
         with request.urlopen('http://%s/status' % self.ip, timeout=self.timeout) as req:
            if req.getcode() != 200:
               self.logger.info('HTTP error on %s' % self.ip)
               return
            goe = json.loads(req.read().decode())
            self.laststate = goe
            self.actP = int(goe['nrg'][11]) * 10  # 0.01kW
            
            # goe['car']: 1 Ladestation bereit, kein Auto
            #             2 Auto lädt
            #             3 Warte auf Fahrzeug
            #             4 Ladung beendet, Fahrzeug verbunden
            self.send({
               'V1': int(goe['nrg'][0]),    'V2': int(goe['nrg'][1]),    'V3': int(goe['nrg'][2]),    # [V]
               'A1': int(goe['nrg'][4])/10.0, 'A2': int(goe['nrg'][5])/10.0, 'A3': int(goe['nrg'][6])/10.0, # [0.1A]
               'Pf1': int(goe['nrg'][12]),  'Pf2': int(goe['nrg'][13]),  'Pf3': int(goe['nrg'][14]),  # %
               'kwh': int(goe['dws'])/360000.0,  # [Deka-Watt-s]
               'boolPlugStat': goe['car'] != '1',
               'boolChargeStat': goe['car'] == '2',
               'W': self.actP,
               'error': goe['err'] != '0'})
            # Aus ist aus
            if int(goe['alw']) > 0 and self.setP == 0:
               self.logger.info("Force off")
               self.set(0)
            # restzeitlp
#      except socket.timeout: Not a BaseException
#         pass
      except Exception as e: # e.g. socket.timeout
         logging.exception("GO-E say Bumm!", exc_info=e)
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
      self.logger.info(f"GO-E request {power}W ({ampere}A)")
      aktiv = 1 if ampere > 0 else 0
      self.setter.request('alw', aktiv)
      if aktiv:
         self.setter.request('amx', ampere)


def getClass():
   return GO_E
