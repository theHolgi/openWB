from openWB import *
from .modbuswr import ModbusWR
from .smadash import SMADASH

class TRIPOWER(PVModul):
   """SMA Tripower"""

   def setup(self, config):
      host = config[self.configprefix + '_ip']
      assert host is not None, "Host für %s notwenig! (Setting %s_ip)" % (self.configprefix, self.configprefix)
      if config.get(self.configprefix + '_type') == 'modbus':
         self.instance = ModbusWR(host)
      else:  # dashboard
         self.instance = SMADASH(host)
      self.kwh = 0
      self.offsetkwh = 0

   def trigger(self):
      try:
         power, generation = self.instance.read()
         self.kwh = generation
         self.core.sendData(DataPackage(self, {'pvwatt': power,
                                               'pvkwh': generation,
                                               'daily_pvkwh': generation - self.offsetkwh
                                               }))
      except ConnectionError:
         pass

   def event(self, event: Event):
      if event.type == EventType.resetDaily:
         self.offsetkwh = self.kwh

def getClass():
   return TRIPOWER
