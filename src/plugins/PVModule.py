from openWB import DataPackage
from openWB.Modul import PVModul, for_all_modules
from openWB.openWBlib import OpenWBconfig, openWBValues


class PVModule:
   """
   Class that represents all PV modules present in the system.
   """
   def __init__(self):
      self.modules = []
      self.data = openWBValues()
      for_all_modules("wr", self.add)

   def add(self, module: PVModul) -> None:
      module.master = self
      self.modules.append(module)
      module.setup(OpenWBconfig())

   def send(self, data: DataPackage) -> None:
      """
      Wird von den PV-Modulen aufgerufen um Daten zu senden.
      Aggregiert und reicht die Daten weiter.
      :param data: PV-Module senden:
         "W"         - aktuelle Leistung [W]
         "kwh" - erzeugte Energie  [kWh]
      kann:
         "DailyKwh"  - tägliche Erzeugung [kWh]
         "MonthlyKwh" - monatliche Erzeugung [kWh]
      """
      package = DataPackage(data.source, dict(map(lambda item: ('pv/%i/%s' % (data.source.id, item[0]), item[1]), data.items())))
      self.data.update(package)
      package = DataPackage(self, {})
      package['pv/W'] = self.data.sum('pv/%i/W')
      package['pv/WhCounter'] = self.data.sum('pv/%i/kwh')
      package['pv/DailyYieldKwh'] = self.data.sum('pv/%i/DailyKwh')
      package['pv/MonthlyYieldKwh'] = self.data.sum('pv/%i/MonthlyKwh')
      self.data.update(package)
