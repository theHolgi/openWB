from openWB.Modul import Displaymodul, for_all_modules
from openWB.openWBlib import OpenWBconfig, openWBValues


class DisplayModule:
   """
   Class that represents any displays (pure data receivers) present in the system.
   """
   def __init__(self):
      self.modul = None
      self.data = openWBValues()
      for_all_modules("display", self.add)

   def add(self, module: Displaymodul) -> None:
      self.modul = module
      module.master = self
      module.configprefix = "displaymodul" + str(module.id)
      module.setup(OpenWBconfig())
