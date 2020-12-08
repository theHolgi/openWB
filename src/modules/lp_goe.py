from urllib import request, error
import json
import logging

from threading import Thread
from openWB import *
from openWB.OpenWBCore import Event, EventType


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
      self.plugged = False
      self.charging = False
      self.logger = logging.getLogger('GO_E')
      
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
            pf1 = int(goe['nrg'][12])   # %
            pf2 = int(goe['nrg'][13])
            pf3 = int(goe['nrg'][14])
            self.actP = int(goe['nrg'][11]) * 10  # 0.01kW
            
            # car status 1 Ladestation bereit, kein Auto
            # car status 2 Auto lädt
            # car status 3 Warte auf Fahrzeug
            # car status 4 Ladung beendet, Fahrzeug verbunden
            chargedkwh = int(goe['eto'])/10  # 0.1kwh
            plugged = goe['car'] != '1'
            charging = goe['car'] == '2'
            
            # Reset von Werten beim Einstecken
            self.chargedkwh = chargedkwh
            if plugged and not self.plugged:
               self.kwhatplugin = chargedkwh
               self.logger.info('Plugged in at %i kwh' % chargedkwh)
            if charging and not self.charging:
               self.kwhatchargestart = chargedkwh
               self.logger.info('Start charging in at %i kwh' % chargedkwh)
               self.setP = amp2power(int(goe['amp']), self.phasen)   # Initialisiere setP falls externer Start

            pluggedgeladen = chargedkwh - self.kwhatplugin if plugged else 0
            aktgeladen = chargedkwh - self.kwhatchargestart if hasattr(self, 'kwhatchargestart') else 0
            self.plugged = plugged
            self.charging = charging
            self.core.sendData(DataPackage(self, {
               'llv1': u1, 'llv2': u2, 'llv3': u3,
               'lla1': a1, 'lla2': a2, 'lla3': a3,
               'llpf1': pf1, 'llpf2': pf2, 'llpf3': pf3,
               'llkwh': chargedkwh,
               'pluggedladungbishergeladen': pluggedgeladen,
               'aktgeladen': aktgeladen,
               'plugstat': plugged,
               'chargestat': charging,
               'llaktuell': self.actP,
               'lpphasen': self.phasen}))
            # restzeitlp
      except:  # e.g. socket.timeout
         pass

   def event(self, event: Event):
      if event.type == EventType.resetEnergy and event.info == self.id:
         self.kwhatchargestart = self.chargedkwh

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
