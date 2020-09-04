from . import Modul, DataPackage, setCore, getCore
from .openWBlib import *
from .regler import *
import logging
from typing import Iterable
import time

logging.basicConfig(level=logging.INFO)


class OpenWBCore:
   """openWB core and scheduler"""
   def __init__(self, configFile: str):
      self.modules = []
      self.data = openWBValues()
      self.config = openWBconfig(configFile)
      self.logger = logging.getLogger(self.__class__.__name__)
      self.pvmodule = 0
      self.regelkreise = dict()
      setCore(self)

   @staticmethod
   def add_module(module: Modul, configprefix: str) -> None:
      core = getCore()
      core.modules.append(module)
      if hasattr(module, 'type'):
         if module.type == "wr":
            core.pvmodule += 1
         elif module.type == "lp":
            lpmode = core.config.get(configprefix + '_mode')
            if lpmode not in core.regelkreise:
               core.regelkreise[lpmode] = Regelgruppe(lpmode)
            core.regelkreise[lpmode].add(module)
      module.configprefix = configprefix
      module.setup(core.config)

   def run(self, loops: int = 0):
      """Run the given number of loops (0=infinite)"""
      if loops == 0:
         condition = lambda: True
      else:
         done = (i < loops for i in range(loops+1))
         condition = lambda: next(done)
      while condition():
         for module in self.modules:
            module.trigger()
         self.data.derive_values()
         self.logger.debug("Values: " + str(self.data))
         for gruppe in self.regelkreise.values():
            gruppe.controlcycle(self.data)
         time.sleep(20)

   def sendData(self, package: DataPackage):
      self.data.update(package)
      self.logger.info('Daten von %s: ' % package.source.name + str(package))



