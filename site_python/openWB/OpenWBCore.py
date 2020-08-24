from . import Modul, DataPackage, setCore, getCore
from .openWBlib import *
import logging
import time
from collections import namedtuple
import enum

logging.basicConfig(level=logging.INFO)

Request = namedtuple('Request', 'id power priority')


class Priority(enum.IntEnum):
   low = 1
   medium = 2
   high = 3
   forced = 4


class Regler:
   """Eine Reglerinstanz"""

   def __init__(self, wallbox):
      self.mode = "pv"
      self.wallbox = wallbox

   def request(self, data) -> Request:
      if self.mode == "pv":
         if data.uberschuss > 1000:
            return Request(self.wallbox.id, data.uberschuss/2, Priority.low)
         else:
            return Request(self.wallbox.id, 0, Priority.low)

   def set(self, power: int) -> None:
      """Set the given power"""
      self.wallbox.set(power)

class OpenWBCore:
   """openWB core and scheduler"""
   def __init__(self, basePath: str):
      self.basePath = basePath
      self.modules = []
      self.data = openWBValues()
      self.logger = logging.getLogger(self.__class__.__name__)
      self.pvmodule = 0
      self.ladepunkte = []
      setCore(self)

   @staticmethod
   def add_module(module: Modul):
      getCore().modules.append(module)
      if hasattr(module, 'type'):
         if module.type == "wr":
            getCore().pvmodule += 1
         elif module.type == "lp":
            getCore().ladepunkte.append(Regler(module))

   def run(self):
      while True:
         for module in self.modules:
            module.trigger()
         self.data.derive_values()
         self.controlcycle()
         print("Values: " + str(self.data))
         time.sleep(5)

   def sendData(self, package: DataPackage):
      self.data.update(package)
      self.logger.info('Received a data package: ' + str(package))

   def controlcycle(self):
      """Regelzyklus"""
      requests = [lp.request(self.data) for lp in self.ladepunkte]
      requests.sort(key=lambda req: req.priority)
      zugeteilt = 0
      for request in requests:
         if request.power <= self.data.uberschuss:
            zugeteilt += request.power
            self.ladepunkte[request.id-1].set(request.power)



