from openWB.Modul import *
from openWB.OpenWBCore import OpenWBCore
from openWB.Scheduling import Scheduler


import socket


def fhem_send(ip: str, cmd: str) -> None:
   try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.connect((ip, 7072))
      s.send((cmd + "\n").encode())
      s.shutdown(1)
      s.close()
   except:
      pass

ON_DELAY = 5


class LP_FHEMSWITCH(Ladepunkt):
   """Ladepunkt als FHEM-Schaltsteckdose"""
   def setup(self, config):
      self.ip = config.get(self.configprefix + '_ip')
      self.swname = config.get(self.configprefix + '_name')
      self.power = config.get(self.configprefix + '_power', 2000)
      self.blockcnt = 0
      self.on_delay = 0
      self.setP = 0
      super().setup(config)

   @property
   def is_blocked(self):
      return self.blockcnt >= 5

   def loop(self):
      # Da wir den Verbrauch selber nicht messen können, erkenne wenigstens unplausiblen Hausverbrauch
      data = openWBValues()
      if data.get('global/WHouseConsumption') < 0:
         if self.blockcnt < 30:
            self.blockcnt += 1
         if self.is_blocked:
            self.actP = 0
      elif data.get('global/WHouseConsumption') > (self.power if self.is_blocked else 0):
         if self.blockcnt > 0:
            self.blockcnt -= 1
         else:
            self.actP = self.setP
      self.send({'W': self.actP})

   def powerproperties(self) -> PowerProperties:
      return PowerProperties(minP=self.power,
                             maxP=self.power,
                             inc=0)

   def set(self, power: int) -> None:
      charging = power >= self.power
      update = {}
      self.logger.info("FHEM send %i W" % power)
      if power > self.power:
         power = self.power
      if charging and not self.is_charging and not self.is_blocked:
         if self.on_delay == 0:
            cmd = "set %s on" % self.swname
            self.logger.info("FHEM cmd " + cmd)
            fhem_send(self.ip, cmd)
            update['boolChargeStat'] = 1
            update['Areq'] = power2amp(power, self.phasen)
         if self.on_delay < ON_DELAY:
            self.on_delay += 1
         else:
            self.actP = self.power
      elif not charging and self.setP > 0:
            cmd = "set %s off" % self.swname
            self.logger.info("FHEM cmd " + cmd)
            fhem_send(self.ip, cmd)
            update['boolChargeStat'] = 0
            update['Areq'] = 0
      self.setP = power
      # Blockierung wird bei Abschaltung aufgehoben
      if not charging:
         self.blockcnt = 0
         self.on_delay = 0
         self.actP = 0
      if update:
         self.send(update)


def getClass():
   return LP_FHEMSWITCH

