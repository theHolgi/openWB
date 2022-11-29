import unittest
from openWB.openWBlib import *

from plugins import LPModule
from openWB.Scheduling import Scheduler
from fakes import FakeRamdisk


class Test_LPModule(unittest.TestCase):
   def setUp(self):
      RamdiskValues._inst = FakeRamdisk()
      if '_inst' in vars(OpenWBconfig):
         del OpenWBconfig._inst
      if '_inst' in vars(Scheduler):
         del Scheduler._inst
      Scheduler(simulated=True)

   def test_invalidmodule(self):
      OpenWBconfig('resources/test_invalidmodule.conf')
      with self.assertRaises(ModuleNotFoundError):
         module = LPModule()

   def test_dummyLP(self):
      OpenWBconfig('resources/test.conf')
      data = openWBValues()
      module = LPModule()
      self.assertEqual(1, len(module.modules))
      self.assertEqual(1, data.get('lp/1/boolChargePointConfigured'), 'LP1 configured')

      LP1 = module.modules[0]
      LP1.set(1300)
      with self.subTest('Geringe Leistung'):
         LP1.actP = 200
         Scheduler().test_callAll()
         self.assertFalse(data.get('lp/1/boolChargeStat'), "Fahrzeug lädt nicht")

      with self.subTest('Höhere Leistung'):
         LP1.actP = 1200
         LP1.A = 6
         LP1.A1 = 5.5

         Scheduler().test_callAll()

         self.assertEqual(LP1.actP, data.get('lp/1/W'), "LP1 Leistung wird übertragen")
         self.assertEqual(LP1.A, data.get('lp/1/AConfigured'), "LP1 Strom wird übertragen")
         self.assertEqual(LP1.actP, data.get('global/WAllChargePoints'), "Summenleistung wird übertragen")
         self.assertTrue(data.get('lp/1/boolChargeStat'), "Fahrzeug lädt")

      with self.subTest('Lademenge'):
         LP1.kwh = 10
         Scheduler().test_callAll()
         self.assertEqual(LP1.kwh, data.get('lp/1/kwh'), "Energie (Gesamt) wird übertragen")
         self.assertEqual(LP1.kwh, data.get('lp/1/DailyKwh'), "Energie (Daily) wird übertragen")
         self.assertEqual(LP1.kwh, data.get('lp/1/kWhActualCharged'), "Energie (Seit Ladebeginn) wird übertragen")
         self.assertEqual(LP1.kwh, data.get('lp/WhCounter'), "Energie (Gesamtsumme) wird übertragen")
         self.assertEqual(LP1.kwh, data.get('lp/DailyYieldKwh'), "Energie (Daily Summe) wird übertragen")

      with self.subTest('Neuer Ladezyklus'):
         LP1.actP = 10
         Scheduler().test_callAll()
         self.assertFalse(data.get('lp/1/boolChargeStat'), "Fahrzeug lädt nicht")
         LP1.actP = 2400
         Scheduler().test_callAll()
         self.assertTrue(data.get('lp/1/boolChargeStat'), "Fahrzeug lädt")
         LP1.kwh += 5
         Scheduler().test_callAll()
         self.assertEqual(15, data.get('lp/1/kwh'), "Energie (Gesamt) wird übertragen")
         self.assertEqual(15, data.get('lp/1/DailyKwh'), "Energie (Daily) wird übertragen")
         self.assertEqual(5, data.get('lp/1/kWhActualCharged'), "Energie (Seit Ladebeginn) wird übertragen")
         self.assertEqual(15, data.get('lp/1/kWhChargedSincePlugged'), "Energie (Seit Plugged) wird übertragen")
         self.assertEqual(15, data.get('lp/WhCounter'), "Energie (Gesamtsumme) wird übertragen")
         self.assertEqual(15, data.get('lp/DailyYieldKwh'), "Energie (Daily Summe) wird übertragen")

   def test_charging(self):
      """Erkenne Ladezustand"""
      OpenWBconfig('resources/test.conf')
      data = openWBValues()
      module = LPModule()
      LP1 = module.modules[0]
      LP1.actP = 200
      Scheduler().test_callAll()
      self.assertFalse(data.get('lp/1/boolChargeStat'), "Fahrzeug lädt nicht")

      LP1.actP = 500
      Scheduler().test_callAll()
      self.assertTrue(data.get('lp/1/boolChargeStat'), "Fahrzeug lädt")

   def test_plugged(self):
      """Erkenne Plugged Status"""
      OpenWBconfig('resources/test.conf')
      data = openWBValues()
      module = LPModule()
      LP1 = module.modules[0]
      LP1.A = 6
      LP1.A1 = 1
      Scheduler().test_callAll(2)
      self.assertFalse(data.get('lp/1/boolPlugStat'), "Fahrzeug nicht eingesteckt")

      LP1.A1 = 5.2
      Scheduler().test_callAll(2)
      self.assertTrue(data.get('lp/1/boolPlugStat'), "Fahrzeug eingesteckt")

      LP1.A1 = 4.9
      Scheduler().test_callAll(2)
      self.assertFalse(data.get('lp/1/boolPlugStat'), "Fahrzeug nicht eingesteckt")

   def test_phasecount(self):
      """Zähle angeschlossene Phasen"""
      OpenWBconfig('resources/test.conf')
      data = openWBValues()
      module = LPModule()
      LP1 = module.modules[0]
      LP1.A = 6
      LP1.A1 = 1
      Scheduler().test_callAll()
      LP1.zaehle_phasen()
      Scheduler().test_callAll()
      self.assertEqual(1, data.get('lp/1/countPhasesInUse'), "1 Phase wird erkannt")

      LP1.A2 = 1
      Scheduler().test_callAll()
      LP1.zaehle_phasen()
      Scheduler().test_callAll()
      self.assertEqual(1, data.get('lp/1/countPhasesInUse'), "2 Phasen werden erkannt")

      LP1.A3 = 1
      Scheduler().test_callAll()
      LP1.zaehle_phasen()
      Scheduler().test_callAll()
      self.assertEqual(1, data.get('lp/1/countPhasesInUse'), "3 Phasen werden erkannt")
