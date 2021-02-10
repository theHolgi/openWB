import unittest

from plugins import PVModule
from openWB.Scheduling import Scheduler
from openWB.openWBlib import *

from fakes import FakeRamdisk


class Test_PVModule(unittest.TestCase):
   def setUp(self):
      RamdiskValues._inst = FakeRamdisk()
      Scheduler(simulated=True)

   def test_data(self):
      OpenWBconfig().setup('resources/test.conf')
      module = PVModule()
      self.assertEqual(2, len(module.modules))

      WR1, WR2 = module.modules
      data = openWBValues()
      WR1.P = 1000
      WR2.P = 2000
      Scheduler().test_callAll()

      self.assertEqual(WR1.P, data.get('pv/1/W'), "WR1 power has been reported")
      self.assertEqual(WR2.P, data.get('pv/2/W'), "WR2 power has been reported")
      self.assertEqual(WR1.P + WR2.P, data.get('pv/W'), "sum power has been reported")

      Scheduler().test_callAll()
      WR1.Wh = 5
      WR2.Wh = 10
      Scheduler().test_callAll()

      self.assertEqual(WR1.Wh, data.get('pv/1/kwh'), "WR1 generation has been reported")
      self.assertEqual(WR2.Wh, data.get('pv/2/kwh'), "WR2 generation has been reported")
      self.assertEqual(WR1.Wh + WR2.Wh, data.get('pv/WhCounter'), "Sum generation has been reported")

      self.assertEqual(WR1.Wh, data.get('pv/1/DailyKwh'), "WR1 generation has been reported (Daily)")
      self.assertEqual(WR1.Wh, data.get('pv/1/MonthlyKwh'), "WR1 generation has been reported (Monthly)")
      self.assertEqual(WR1.Wh + WR2.Wh, data.get('pv/DailyYieldKwh'), "Sum generation has been reported (Daily)")
      self.assertEqual(WR1.Wh + WR2.Wh, data.get('pv/MonthlyYieldKwh'), "Sum generation has been reported (Monthly)")


if __name__ == '__main__':
   unittest.main()
