from openWB import DataPackage
from openWB.Scheduling import Scheduler
from openWB.openWBlib import openWBValues


class DependentData:
   def __init__(self):
      Scheduler().registerData(['evu/W', 'housebattery/W', 'pv/W'], self.houseconsumption)

   def houseconsumption(self, updated: dict) -> None:
      data = openWBValues()
      packet = DataPackage(self, {})
      packet['global/uberschuss'] = data.get('housebattery/W') - data.get('evu/W')
      packet['global/WHouseConsumption'] = data.get('evu/W') + data.get('pv/W') - data.get('global/WAllChargePoints') - data.get('housebattery/W')
      data.update(packet)
