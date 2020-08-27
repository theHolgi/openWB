from . import Modul, DataPackage, setCore, getCore
from .openWBlib import *
from .regler import Regler
import logging
import time

logging.basicConfig(level=logging.INFO)


class OpenWBCore:
   """openWB core and scheduler"""
   def __init__(self, basePath: str):
      self.basePath = basePath
      self.modules = []
      self.data = openWBValues()
      self.config = openWBconfig(basePath + 'pyconfig.conf')
      self.logger = logging.getLogger(self.__class__.__name__)
      self.pvmodule = 0
      self.ladepunkte = []
      setCore(self)

   @staticmethod
   def add_module(module: Modul, configprefix: str) -> None:
      core = getCore()
      core.modules.append(module)
      if hasattr(module, 'type'):
         if module.type == "wr":
            core.pvmodule += 1
         elif module.type == "lp":
            core.ladepunkte.append(Regler(module))
      module.configprefix = configprefix
      module.setup(core.config)

   def run(self):
      while True:
         for module in self.modules:
            module.trigger()
         self.data.derive_values()
         self.controlcycle()
         self.logger.debug("Values: " + str(self.data))
         time.sleep(5)

   def sendData(self, package: DataPackage):
      self.data.update(package)
      self.logger.info('Daten von %s: ' % package.source.name + str(package))

   def controlcycle(self):
      """Regelzyklus"""
      requests = [lp.request(self.data) for lp in self.ladepunkte]
      requests.sort(key=lambda req: req.priority)
      zugeteilt = 0
      for request in requests:
         if request.power <= self.data.uberschuss:
            zugeteilt += request.power
            self.ladepunkte[request.id-1].set(request.power)



