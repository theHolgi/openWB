from openWB.Modul import PVModul
from openWB.Scheduling import Scheduler
from .modbuswr import ModbusWR
import logging


class HUAWEI(PVModul):
   """Huawei SUN2000"""

   def setup(self, config):
      super().setup(config)
      host = config[self.configprefix + '_ip']
      assert host is not None, "Host für %s notwenig! (Setting %s_ip)" % (self.configprefix, self.configprefix)
      self.instanceid = config.get(self.configprefix + '_id', 1)
      self.logger = logging.getLogger()
      self.instance = ModbusWR(host, self.instanceid)

      super().setup(config)
      Scheduler().registerTimer(15, self.loop)

   def loop(self):
      try:
         power, generation = self.instance.read()
         self.send({'W': power, 'kwh': generation})
      except ConnectionError:
         self.send({})
      except Exception as e:
         self.logger.exception("O-o, something really wrong!", exc_info=e)


def getClass():
   return HUAWEI
