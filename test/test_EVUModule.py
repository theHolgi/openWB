import unittest
from openWB.openWBlib import *

from plugins import EVUModule
from openWB.Scheduling import Scheduler
from fakes import FakeRamdisk

class Test_EVUModule(unittest.TestCase):
   def setUp(self):
      RamdiskValues._inst = FakeRamdisk()
      Scheduler(simulated=True)
      if '_inst' in vars(OpenWBconfig):
         del OpenWBconfig._inst

   def test_invalidmodule(self):
      OpenWBconfig('resources/test_invalidmodule.conf')
      with self.assertRaises(ModuleNotFoundError):
         module = EVUModule()

   def test_dummyEVU(self):
      OpenWBconfig('resources/test.conf')
      module = EVUModule()
      self.assertIsNotNone(module.modul)

      EVU = module.modul
      data = openWBValues()
      EVU.P = 1000
      Scheduler().test_callAll()

      self.assertEqual(EVU.P, data.get('evu/W'), "EVU power has been reported")
      self.assertIsNone(data.get('evu/ASchieflast', None), "Keine Schieflast ohne Phasenströme")

      EVU.A1 = 1
      EVU.A2 = 3
      EVU.A3 = 6

      Scheduler().test_callAll()
      self.assertEqual(5, data.get('evu/ASchieflast'), "EVU Schieflast has been calculated")
      EVU.kwhIn = 5
      EVU.kwhOut = 10
      Scheduler().test_callAll()
      self.assertEqual(EVU.kwhIn,  data.get('evu/WhImported'), "EVU energy imported has been reported")
      self.assertEqual(EVU.kwhOut, data.get('evu/WhExported'), "EVU energy exported has been reported")

      self.assertEqual(EVU.kwhIn, data.get('evu/DailyYieldImportKwh'), "EVU energy imported has been reported (Daily)")
      self.assertEqual(EVU.kwhOut, data.get('evu/DailyYieldExportKwh'), "EVU energy exported has been reported(Daily)")
      self.assertEqual(EVU.kwhIn, data.get('evu/MonthlyYieldImportKwh'), "EVU energy imported has been reported (Monthly)")
      self.assertEqual(EVU.kwhOut, data.get('evu/MonthlyYieldExportKwh'), "EVU energy exported has been reported (Monthly)")

if __name__ == '__main__':
   unittest.main()
