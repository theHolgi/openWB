from openWB.Modul import PVModul
from openWB.Scheduling import Scheduler
from .modbuswr import ModbusWR

class HUAWEIWR(ModbusWR):
   REG_P = 32080
   REG_TotWh = 37113 # unknown
   REG_DCA = 37107  # Phase 1/2/3

class HUAWEI(PVModul):
   """SMA Tripower"""

   def setup(self, config):
      super().setup(config)
      host = config[self.configprefix + '_ip']
      assert host is not None, "Host für %s notwenig! (Setting %s_ip)" % (self.configprefix, self.configprefix)
      self.instanceid = config.get(self.configprefix + '_id', 1)
      self.instance = HUAWEIWR(host, self.instanceid)

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
