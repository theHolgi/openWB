from openWB import *
import socket


def fhem_send(ip: str, cmd: str) -> None:
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   s.connect((ip, 7072))
   s.send(cmd + "\n")
   s.shutdown(1)
   s.close()


class LP_FHEMSWITCH(DataProvider, Ladepunkt):
   """Ladepunkt als FHEM-Schaltsteckdose"""
   def setup(self, config):
      self.ip = config.get(self.configprefix + '_ip')
      self.swname = config.get(self.configprefix + '_name')
      self.power = config.get(self.configprefix + '_power', 2000)

   def trigger(self):
      self.core.sendData(DataPackage(self, {
         'plugstat': True,
         'chargestat': self.is_charging,
         'llaktuell': self.actP,
         'lpphasen': 1}))

   def powerproperties(self) -> PowerProperties:
      return PowerProperties(minP=self.power,
                             maxP=self.power,
                             inc=0)

   def set(self, power:int) -> None:
      charging = power > self.power/2
      if charging != self.is_charging:
         cmd = "set %s %s" % (self.swname, "on" if self.is_charging else "off")
         fhem_send(self.ip, cmd)
      self.actP = power


def getClass():
   return LP_FHEMSWITCH