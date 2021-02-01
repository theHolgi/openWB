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
      power = 0
      generated = 0
      dailykwh = 0
      monthlykwh = 0
      for i in range(1, len(self.modules) + 1):
         power += self.data.get('pv/%i/W' % i, 0)
         generated += self.data.get('pv/%i/kwh' % i, 0)
         dailykwh  += self.data.get('pv/%i/DailyKwh' % i, 0)
         monthlykwh += self.data.get('pv/%i/MonthlyKwh' % i, 0)
      self.data.update(DataPackage(self, {
         'pv/W': power,
         'pv/WhCounter': generated,
         'pv/DailyYieldKwh': dailykwh,
         'pv/MonthlyYieldKwh': monthlykwh
      }))
