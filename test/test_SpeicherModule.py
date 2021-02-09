import unittest

from plugins import SpeicherModule
from openWB.Scheduling import Scheduler
from openWB.openWBlib import *

from fakes import FakeRamdisk

class Test_SpeicherModule(unittest.TestCase):

   def setUp(self):
      RamdiskValues._inst = FakeRamdisk()
      Scheduler(simulated=True)

   def test_invalidmodule(self):
      OpenWBconfig().setup('resources/test_invalidmodule.conf')
      with self.assertRaises(ModuleNotFoundError):
         module = SpeicherModule()

   def test_dummySpeicher(self):
      OpenWBconfig().setup('resources/test.conf')
      module = SpeicherModule()
      self.assertEqual(2, len(module.modules))

      BAT1, BAT2 = module.modules
      data = openWBValues()
      BAT1.P = 1000
      BAT2.P = 2000
      BAT1.soc = 25
      BAT2.soc = 75
      Scheduler().test_callAll()

      self.assertEqual(BAT1.P, data.get('housebattery/1/W'), "BAT1 power has been reported")
      self.assertEqual(BAT2.P, data.get('housebattery/2/W'), "BAT2 power has been reported")
      self.assertEqual(BAT1.P + BAT2.P, data.get('housebattery/W'), "sum power has been reported")
      self.assertEqual(50, data.get('housebattery/%Soc'), "sum SOC has been reported")

      Scheduler().test_callAll()
      BAT1.kwhOut = 5
      BAT2.kwhOut = 10
      BAT1.kwhIn = 15
      BAT2.kwhIn = 20
      Scheduler().test_callAll()

      self.assertEqual(BAT1.kwhIn + BAT2.kwhIn,  data.get('housebattery/WhImported'), "EVU energy imported has been reported")
      self.assertEqual(BAT1.kwhOut + BAT2.kwhOut, data.get('housebattery/WhExported'), "EVU energy exported has been reported")

      self.assertEqual(BAT1.kwhIn, data.get('housebattery/1/dailykwhIn'), "BAT1 generation has been reported (Daily)")
      self.assertEqual(BAT1.kwhOut, data.get('housebattery/1/monthlykwhOut'), "BAT1 generation has been reported (Monthly)")
      self.assertEqual(BAT1.kwhIn + BAT2.kwhIn, data.get('housebattery/DailyYieldImportKwh'), "Sum generation has been reported (Daily)")
      self.assertEqual(BAT1.kwhOut + BAT2.kwhOut, data.get('housebattery/MonthlyYieldExportKwh'), "Sum generation has been reported (Monthly)")


if __name__ == '__main__':
   unittest.main()
