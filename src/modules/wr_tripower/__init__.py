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
      super().setup(config)

   def loop(self):
      try:
         power, generation = self.instance.read()
         self.send({'pvwatt': power, 'pvkwh': generation})
      except ConnectionError:
         self.send({})


def getClass():
   return TRIPOWER
