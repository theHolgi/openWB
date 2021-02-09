from openWB import DataPackage
from openWB.Modul import for_module, EVUModul
from openWB.openWBlib import OpenWBconfig, openWBValues

datamapping = {
   # EVU
   "evu/W": "W",
   "evu/WhExported": "kwhOut",
   "evu/WhImported": "kwhIn",
   "evu/APhase1": "A1",
   "evu/APhase2": "A2",
   "evu/APhase3": "A3",
   "evu/VPhase1": "V1",
   "evu/VPhase2": "V2",
   "evu/VPhase3": "V3",
   "evu/WPhase1": "W1",
   "evu/WPhase2": "W2",
   "evu/WPhase3": "W3",
   "evu/PfPhase1": "Pf1",
   "evu/PfPhase2": "Pf2",
   "evu/PfPhase3": "Pf3",
   "evu/Hz": "Hz",
   "evu/DailyYieldImportKwh": "daily_kwhIn",
   "evu/DailyYieldExportKwh": "daily_kwhOut",
   "evu/MonthlyYieldImportKwh": "monthly_kwhIn",
   "evu/MonthlyYieldExportKwh": "monthly_kwhOut"
}

class EVUModule:
   """
   Class that represents the EVU module present in the system.
   """
   def __init__(self):
      self.modul = None
      self.data = openWBValues()
      for_module("bezug", self.add)

   def add(self, module: EVUModul) -> None:
      self.modul = module
      module.master = self
      module.setup(OpenWBconfig())

   def send(self, data: DataPackage) -> None:
      """
      Wird vom EVU-Modul aufgerufen um Daten zu versenden.

      :param data: EVU-Module senden:
         - W - [W] Leistung am EVU-Übergabepunkt (>0: Bezug)
         KANN:
         - V1 ... V3  - [V] Spannung
         - A1 ... A3  - [A] Strom
         - Pf1 .. Pf3 - [%] Leistungsfaktor
         - W1 ... W3  - [W] Leistung an Phase n
         - evuhz           - [Hz] Netzfrequenz
         - kwhOut          - [kWh] Gesamte eingespeiste Energie
         - kwhIn           - [kWh] Gesamte bezogene Energie
      """
      package = DataPackage(data.source, dict((k, data[v]) for (k, v) in datamapping.items() if v in data))

      if 'A1' in data:
         maxI = max(data['A' + str(phase)] for phase in range(1, 4))
         lowI = min(data['A' + str(phase)] for phase in range(1, 4))
         package['evu/ASchieflast'] = maxI - lowI

      self.data.update(package)
