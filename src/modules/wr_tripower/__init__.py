from openWB.Modul import PVModul
from openWB.Scheduling import Scheduler
from .modbuswr import ModbusWR
from .smadash import SMADASH


class TRIPOWER(PVModul):
   """SMA Tripower"""

   def setup(self, config):
      super().setup(config)
      host = config[self.configprefix + '_ip']
      assert host is not None, "Host für %s notwenig! (Setting %s_ip)" % (self.configprefix, self.configprefix)
      self.instances = config.get(self.configprefix + '_instances', 1)
      if config.get(self.configprefix + '_type') == 'modbus':
         self.instance = ModbusWR(host, self.instances)
      else:  # dashboard
         self.instance = SMADASH(host)
         assert self.instances == 1, "Dashboard Tripower can only have one instance."
      super().setup(config)
      Scheduler().registerTimer(10, self.loop)

   def loop(self):
      try:
         power, generation = self.instance.read()
         self.send({'W': power, 'kwh': generation})
      except ConnectionError:
         self.send({})
      except Exception as e:
         self.logger.exception("O-o, something really wrong!", exc_info=e)


def getClass():
   return TRIPOWER
