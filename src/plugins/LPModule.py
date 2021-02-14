from openWB import DataPackage
from openWB.Modul import Ladepunkt, for_all_modules
from openWB.openWBlib import openWBValues, OpenWBconfig

mapping = {
   'A': 'AConfigured',
   'V1': 'VPhase1',
   'V2': 'VPhase2',
   'V3': 'VPhase3',
   'A1': 'APhase1',
   'A2': 'APhase2',
   'A3': 'APhase3',
   'Pf1': 'PfPhase1',
   'Pf2': 'PfPhase2',
   'Pf3': 'PfPhase3'
}

class LPModule:
   """
   Class that represents all Chargeport modules present in the system.
   """
   def __init__(self):
      self.modules = []
      self.data = openWBValues()
      for_all_modules("lp", self.add)

   def add(self, module: Ladepunkt) -> None:
      module.master = self
      self.modules.append(module)
      module.setup(OpenWBconfig())
      self.data.update({
         "lp/%i/boolChargePointConfigured" % module.id: 1, # Configured -> vorhanden
         "lp/%i/ChargePointEnabled" % module.id: 1         # Enabled -> Ladebereit; nicht z.B. nach Ablauf der Lademenge
      })

   def send(self, data: DataPackage) -> None:
      """
      Wird von den PV-Modulen aufgerufen um Daten zu senden.
      Aggregiert und reicht die Daten weiter.
      :param data: LP-Module senden:
         "W"         - aktuelle Ladeleistung [W]
         "A"         - gesetzter Strom     [A]
      KANN:
        - boolPlugStat   - Stecker eingesteckt [bool]
        - boolChargeStat - Auto lädt wirklich [bool]
        - ChargeStatus   - Auto soll laden [bool]
        - kwh - Gesamte Lademenge [kWh]
        - V1, V2, V3    - Spannung [V]
        - A1, A2, A3    - Strom    [A]
        - Pf1, Pf2, Pf3 - Leistungsfaktor [%]
      """
      package = DataPackage(data.source,
                            dict(map(lambda item: ('lp/%i/%s' % (data.source.id, mapping.get(item[0], item[0])), item[1]), data.items())))
      package['lp/%i/countPhasesInUse' % data.source.id] = data.source.phasen
      self.data.update(package)

      package = DataPackage(self, {})
      package['global/WAllChargePoints'] = self.data.sum('lp/%i/W')
      package['lp/WhCounter'] = self.data.sum('lp/%i/kwh')
      package['lp/DailyYieldKwh'] = self.data.sum('lp/%i/DailyKwh')
      self.data.update(package)
