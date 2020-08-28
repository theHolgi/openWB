from openWB import *
from .modbuswr import ModbusWR
from .smadash import SMADASH

class TRIPOWER(DataProvider, PVModul):
   """SMA Tripower"""

   def setup(self, config):
      host = config[self.configprefix + '_ip']
      assert host is not None, "Host für %s notwenig! (Setting %s_ip)" % (self.configprefix, self.configprefix)
      if config.get(self.configprefix + '_type') == 'modbus':
         self.instance = ModbusWR(host)
      else:  # dashboard
         self.instance = SMADASH(host)

   def trigger(self):
      power, generation = self.instance.read()
      self.core.sendData(DataPackage(self, {'pvwatt': power,
                                            'pvkwh': generation}))

   def event(self):
      pass

def getClass():
   return TRIPOWER
