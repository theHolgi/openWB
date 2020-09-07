from openWB import *
import socket


def fhem_send(ip: str, cmd: str) -> None:
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   s.connect((ip, 7072))
   s.send((cmd + "\n").encode())
   s.shutdown(1)
   s.close()


class LP_FHEMSWITCH(DataProvider, Ladepunkt):
   """Ladepunkt als FHEM-Schaltsteckdose"""
   def setup(self, config):
      self.ip = config.get(self.configprefix + '_ip')
      self.swname = config.get(self.configprefix + '_name')
      self.power = config.get(self.configprefix + '_power', 2000)
      self.blockcnt = 0
      self.setP = 0

   @property
   def is_blocked(self):
      return self.blockcnt <= 5

   def trigger(self):
      # Da wir den Verbrauch selber nicht messen können, erkenne wenigstens unplausiblen Hausverbrauch
      if self.core.data.get('hausverbrauch') < 0:
         self.blockcnt += 1
         if self.is_blocked:
            self.actP = 0
      else:
         if self.blockcnt > 0:
            self.blockcnt -= 1
         
      self.core.sendData(DataPackage(self, {
         'plugstat': not self.is_blocked,
         'chargestat': self.is_charging,
         'llaktuell': self.actP,
         'lpphasen': 1}))

   def powerproperties(self) -> PowerProperties:
      return PowerProperties(minP=self.power,
                             maxP=self.power,
                             inc=0)

   def set(self, power: int) -> None:
      charging = power > self.power/2
      ampere = power2amp(power, self.phasen)
      self.core.sendData(DataPackage(self, {'llsoll': ampere, 'ladestatus': 1 if charging else 0 }))
      self.setP = power
      if (charging and not self.is_charging and not self.is_blocked) \
            or (not charging and self.setP > 0):
         fhem_send(self.ip, "set %s on" % self.swname)
         self.actP = power
      # Blockierung wird bei Abschaltung aufgehoben
      if not charging:
         self.blockcnt = 0
         self.actP = 0


def getClass():
   return LP_FHEMSWITCH

