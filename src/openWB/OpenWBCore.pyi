from openWB import Singleton
from openWB.Modul import Modul, DataPackage
from openWB.Event import OpenWBEvent


class OpenWBCore(Singleton):
   def __init__(self, configFile: str): ...

   @staticmethod
   def add_module(module: Modul, configprefix: str) -> None: ...

   def run(self): ...

   def setconfig(self, key:str, value) -> None:
      """Set the configuration, but also announce this in the system."""
      ...

   def triggerEvent(self, event: OpenWBEvent): ...
