from . import Modul, DataPackage

class OpenWBCore:
   def __init__(self, configFile: str)): ...

   @staticmethod
   def add_module(module: Modul, configprefix: str) -> None: ...

   def run(self): ...

   def sendData(self, package: DataPackage): ...

   def controlcycle(self): ...
