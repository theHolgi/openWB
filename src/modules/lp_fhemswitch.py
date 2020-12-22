from openWB import *
import socket


def fhem_send(ip: str, cmd: str) -> None:
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   s.connect((ip, 7072))
   s.send((cmd + "\n").encode())
   s.shutdown(1)
   s.close()

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
      super().setup()

   @property
   def is_blocked(self):
      return self.blockcnt >= 5

   def trigger(self):
      # Da wir den Verbrauch selber nicht messen können, erkenne wenigstens unplausiblen Hausverbrauch
      if self.core.data.get('hausverbrauch') < 0:
         self.blockcnt += 1
         if self.is_blocked:
            self.actP = 0
      elif not self.is_blocked:
         if self.blockcnt > 0:
            self.blockcnt -= 1
         
      self.send({
         'llaktuell': self.actP,
         'lpphasen': 1})

   def powerproperties(self) -> PowerProperties:
      return PowerProperties(minP=self.power,
                             maxP=self.power,
                             inc=0)

   def set(self, power: int) -> None:
      charging = power > self.power/2
      ampere = power2amp(power, self.phasen)
      self.core.sendData(DataPackage(self, {'llsoll': ampere, 'ladestatus': charging}))
      self.core.logger.info("FHEM send %i W" % power)
      if charging and not self.is_charging and not self.is_blocked:
         if self.on_delay == 0:
            cmd = "set %s on" % self.swname
            self.core.logger.info("FHEM cmd " + cmd)
            fhem_send(self.ip, cmd)
         if self.on_delay < ON_DELAY:
            self.on_delay += 1
         else:
            self.actP = power
      elif not charging and self.setP > 0:
            cmd = "set %s off" % self.swname
            self.core.logger.info("FHEM cmd " + cmd)
            fhem_send(self.ip, cmd)
      self.setP = power
      # Blockierung wird bei Abschaltung aufgehoben
      if not charging:
         self.blockcnt = 0
         self.on_delay = 0
         self.actP = 0


def getClass():
   return LP_FHEMSWITCH

