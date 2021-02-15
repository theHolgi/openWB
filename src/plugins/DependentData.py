from openWB import DataPackage
from openWB.Scheduling import Scheduler
from openWB.openWBlib import openWBValues


class DependentData:
   priority = 1     # Dependent data has highest data dependency priority

   def __init__(self):
      Scheduler().registerData(['evu/W', 'housebattery/W', 'pv/W'], self)

   def newdata(self, updated: dict) -> None:
      data = openWBValues()
      packet = DataPackage(self, {
         'global/uberschuss': data.get('housebattery/W') - data.get('evu/W'),
         'global/WHouseConsumption': data.get('evu/W') + data.get('pv/W') - data.get('global/WAllChargePoints') - data.get('housebattery/W')
      })
      data.update(packet)
