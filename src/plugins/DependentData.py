from openWB import DataPackage
from openWB.Scheduling import Scheduler
from openWB.openWBlib import openWBValues, OpenWBconfig


class DependentData:
   priority = 1  # Dependent data has highest data dependency priority

   def __init__(self):
      Scheduler().registerData(['evu/W', 'pv/W', 'global/WAllChargePoints', 'housebattery/W'], self)
      self.data = openWBValues()
      self.config = OpenWBconfig()

   def _speicherreserve(self) -> int:
      """Passe Überschuss an um die Reserven, die der Speicher zur Verfügung stellt"""
      Pbatt = self.data.get('housebattery/W')
      speicherprio = self.config.get('speicherpveinbeziehen')
      if Pbatt < 0:
         return Pbatt  # Speicherentnahme ist negativer Überschuss
      if speicherprio == 0:    # Speicher hat Priorität
         return 0
      elif speicherprio == 1:  # EV hat unbedingte Priorität
         return Pbatt
      elif speicherprio == 2:  # Auto -> Je leerer der Speicher, desto mehr reservierte Leistung
         speicher_reserve = int(((100 - self.data.get('housebattery/%Soc')) * self.config.get('speichermaxp', 3000)) / 100)
         return max(Pbatt - speicher_reserve, 0)



   def newdata(self, updated: dict) -> None:
      packet = DataPackage(self, {
         'global/uberschuss': self._speicherreserve() - self.data.get('evu/W'),
         'global/WHouseConsumption': self.data.get('evu/W') + self.data.get('pv/W') -
                                     self.data.get('global/WAllChargePoints') - self.data.get('housebattery/W')
      })
      self.data.update(packet)
