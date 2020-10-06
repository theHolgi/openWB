from . import Modul, DataPackage
from dataclasses import dataclass
from enum import Enum


class OpenWBCore:
   def __init__(self, configFile: str)): ...

   @staticmethod
   def add_module(module: Modul, configprefix: str) -> None: ...

   def run(self): ...

   def sendData(self, package: DataPackage): ...

   def setconfig(self, key:str, value) -> None:
      """Set the configuration, but also announce this in the system."""
      ...

   def triggerEvent(self, event: Event): ...
