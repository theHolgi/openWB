from openWB import *
from .modbuswr import ModbusWR
from .smadash import SMADASH


class TRIPOWER(PVModul):
   """SMA Tripower"""

   def setup(self, config):
      super().setup(config)
      host = config[self.configprefix + '_ip']
      assert host is not None, "Host für %s notwenig! (Setting %s_ip)" % (self.configprefix, self.configprefix)
      if config.get(self.configprefix + '_type') == 'modbus':
         self.instance = ModbusWR(host)
      else:  # dashboard
         self.instance = SMADASH(host)

   def loop(self):
      try:
         self.send(self.instance.read())
      except ConnectionError:
         self.send({})


def getClass():
   return TRIPOWER
