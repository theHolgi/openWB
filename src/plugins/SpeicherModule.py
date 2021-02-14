from openWB import DataPackage
from openWB.Modul import for_all_modules, Speichermodul
from openWB.openWBlib import OpenWBconfig, openWBValues

# datamapping = {
#    # EVU
#    "housebattery/W": "W",
#    "housebattery/%Soc": "soc",
#    "housebattery/WhExported": "kwhOut",
#    "housebattery/WhImported": "kwhIn",
#    "housebattery/DailyYieldExportKwh": "daily_kwhOut",
#    "housebattery/DailyYieldImportKwh": "daily_kwhIn",
#    "housebattery/MonthlyYieldExportKwh": "monthly_kwhOut",
#    "housebattery/MonthlyYieldImportKwh": "monthly_kwhIn"
# }

class SpeicherModule:
   """
   Class that represents the EVU module present in the system.
   """
   def __init__(self):
      self.modules = []
      self.data = openWBValues()
      for_all_modules("speicher", self.add)

   def add(self, module: Speichermodul) -> None:
      module.master = self
      self.modules.append(module)
      module.setup(OpenWBconfig())
      self.data.update({"housebattery/boolHouseBatteryConfigured": 1})

   def send(self, data: DataPackage) -> None:
      """
      Wird vom Speicher-Modul aufgerufen um Daten zu versenden.
      :param data: Speicher-Module senden:
         - W - [W] Ladeleistung (>0: Laden)
         SOLLTE:
         - soc      - [%] State of charge
         KANN:
         - kwhOut          - [kWh] Gesamte abgegebene Energie
         - kwhIn           - [kWh] Gesamte aufgenommene Energie
      """
      package = DataPackage(data.source,
                            dict(map(lambda item: ('housebattery/%i/%s' % (data.source.id, item[0]), item[1]), data.items())))
      self.data.update(package)
      package = DataPackage(self, {})
      package['housebattery/W'] = self.data.sum('housebattery/%i/W')
      package['housebattery/%Soc'] = self.data.sum('housebattery/%i/soc') / len(self.modules)  # Average SOC
      package['housebattery/WhImported'] = self.data.sum('housebattery/%i/kwhIn')
      package['housebattery/WhExported'] = self.data.sum('housebattery/%i/kwhOut')
      package['housebattery/DailyYieldExportKwh'] = self.data.sum('housebattery/%i/dailykwhOut')
      package['housebattery/DailyYieldImportKwh'] = self.data.sum('housebattery/%i/dailykwhIn')
      package['housebattery/MonthlyYieldExportKwh'] = self.data.sum('housebattery/%i/monthlykwhOut')
      package['housebattery/MonthlyYieldImportKwh'] = self.data.sum('housebattery/%i/monthlykwhIn')
      self.data.update(package)
