from openWB import DataPackage
from openWB.Scheduling import Scheduler
from openWB.openWBlib import openWBValues, OpenWBconfig


class DependentData:
   priority = 1  # Dependent data has highest data dependency priority

   def __init__(self):
      Scheduler().registerData(['evu/W', 'pv/W', 'global/WAllChargePoints', 'housebattery/W'], self)

   def newdata(self, updated: dict) -> None:
      data = openWBValues()
      packet = DataPackage(self, {
         'global/uberschuss': -data.get('evu/W'),
         'global/WHouseConsumption': data.get('evu/W') + data.get('pv/W') -
                                     data.get('global/WAllChargePoints') - data.get('housebattery/W')
      })
      # Batterie entlädt, oder EV-Vorrang (1),
      # oder auto-EV-Vorrang und Speicher SOC > 50% -> Ladeleistung ist nicht Überschuss
      if data.get('housebattery/W') < 0 or \
         OpenWBconfig().get('speicherpveinbeziehen') == 1 or \
         (OpenWBconfig().get('speicherpveinbeziehen') == 2 and data.get('housebattery/%Soc') > 50):
         packet['global/uberschuss'] += data.get('housebattery/W')
      data.update(packet)
