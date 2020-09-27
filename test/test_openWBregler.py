import unittest
import os
from openWB.openWBlib import openWBconfig
from openWB import *
from openWB.OpenWBCore import OpenWBCore
from openWB.regler import *
global core

mypath = os.path.dirname(os.path.realpath(__file__)) + '/'

class StubCore():
   config = openWBconfig(mypath + 'test.conf')

   @staticmethod
   def add_module(module: Modul, configprefix: str):
      module.configprefix = configprefix

class StubPV(PVModul):
   P = 0
   def trigger(self):
      self.core.sendData(DataPackage(self, {'pvwatt': -self.P}))

class StubLP(Ladepunkt):
   actP = 0
   phasen = 1
   override_blocked = None

   def trigger(self):
      amp = self.actP / self.phasen / 230
      self.core.sendData(DataPackage(self, {'llaktuell': self.actP, 'lla1': amp}))

   def powerproperties(self):
      return PowerProperties(minP=self.phasen*230*6,
                             maxP=self.phasen*230*25,
                             inc=self.phasen*230)

   def set(self, power: int):
      self.setP = power
      self.core.sendData(DataPackage(self, {'llsoll': power2amp(power, self.phasen)}))

   @property
   def is_blocked(self):
      if self.override_blocked is not None:
         return self.override_blocked
      else:
         return super().is_blocked

class StubEVU(DataProvider):
   P = 0
   def trigger(self):
      self.core.sendData(DataPackage(self, {'wattbezug': self.P}))

   @property
   def pvuberschuss(self):
      return (-self.P) - 200

class Test_Regler(unittest.TestCase):
   """Teste Regler Klasse"""
   EVU = StubEVU(1)
   LP = StubLP(1)
   LP.core = StubCore()
   LP.id = 1

   def setUp(self):
      self.regler = Regler(self.LP)
      StubCore.add_module(self.LP, 'lpmodul1')
      self.LP.actP = 0
      self.LP.setP = 0
      self.LP.override_blocked = False

   def test_idle(self):
      req = self.regler.get_props()
      self.assertEqual(self.LP.id, req.id, "Request kommt von LP")
      self.assertIn('off', req.flags, "Request hat off-Flag")
      self.assertEqual(self.LP.minP, req['min+P'].value, "Minimal+P ist Einschaltschwelle")
      self.assertEqual(self.LP.maxP, req['max+P'].value, "Maximal+P ist Max-Leistung")
      self.assertEqual(self.LP.prio, req['min+P'].priority, "Minimal+P prio ist vom LP")
      self.assertEqual(self.LP.prio, req['max+P'].priority, "Maximal+P prio ist vom LP")
      self.assertNotIn('min-P', req, "Keine Leistungsverringerung")
      self.assertNotIn('max-P', req, "Keine Leistungsverringerung")

   def test_ladeende(self):
      """Noch bestehene Anforderung ohne Strom"""
      self.LP.setP = 3000
      self.LP.actP = 100
      req = self.regler.get_props()
      self.assertIn('off', req.flags, "Request hat off-Flag")
      self.assertNotIn('min+P', req, "Keine Leistungserhöhung")
      self.assertNotIn('max+P', req, "Keine Leistungserhöhung")
      self.assertEqual(self.LP.setP, req['min-P'].value, "Minimal-P ist komplette Leistung")
      self.assertEqual(self.LP.setP, req['max-P'].value, "Maximal-P ist komplette Leistung")

   def test_atminP(self):
      self.LP.setP = self.LP.minP + 50  # A bit more, but not enough
      self.LP.actP = self.LP.setP
      req = self.regler.get_props()
      self.assertEqual(self.LP.id, req.id, "Request kommt von LP")
      self.assertIn('on', req.flags, "Kein off-Flag")
      self.assertIn('min', req.flags, "Läuft auf min-P")
      self.assertEqual(230, req['min+P'].value, "Minimal+P ist Inkrement")
      self.assertEqual(self.LP.maxP - self.LP.actP, req['max+P'].value, "Maximal+P ist Delta zu Max")
      self.assertEqual(50, req['min-P'].value, "Minimal-P ist Rest zu min")
      self.assertEqual(self.LP.minP + 50, req['max-P'].value, "Maximal-P ist Abschaltung")

   def test_atmiddle(self):
      self.LP.setP = self.LP.minP + 1000  # Somewhere
      self.LP.actP = self.LP.setP
      req = self.regler.get_props()
      self.assertEqual(self.LP.id, req.id, "Request kommt von LP")
      self.assertIn('on', req.flags, "Kein off-Flag")
      self.assertNotIn('min', req.flags, "Läuft nicht auf min-P")
      self.assertNotIn('max', req.flags, "Läuft nicht auf max-P")
      self.assertEqual(230, req['min+P'].value, "Minimal+P ist Inkrement")
      self.assertEqual(230, req['min-P'].value, "Minimal-P ist Inkrement")
      self.assertEqual(self.LP.setP - self.LP.minP, req['max-P'].value, "Maximal-P ist Delta zu Min")
      self.assertEqual(self.LP.maxP - self.LP.setP, req['max+P'].value, "Maximal+P ist Delta zu Max")

   def test_blocked(self):
      self.LP.setP = self.LP.minP + 1000  # Somewhere
      self.LP.actP = self.LP.setP - 300
      self.LP.override_blocked = True
      req = self.regler.get_props()
      self.assertEqual(self.LP.id, req.id, "Request kommt von LP")
      self.assertIn('on', req.flags, "Kein off-Flag")
      self.assertNotIn('min', req.flags, "Läuft nicht auf min-P")
      self.assertNotIn('max', req.flags, "Läuft nicht auf max-P")
      self.assertNotIn('min+P', req, "Kein min-Inkrement")
      self.assertNotIn('max+P', req, "Kein max-Inkrement")
      self.assertEqual(self.LP.setP - self.LP.minP, req['max-P'].value, "Maximal-P ist Delta zu Min")
      self.assertEqual(230, req['min-P'].value, "Min-P ist Inkrement")

   def test_atmaxP(self):
      self.LP.setP = self.LP.maxP - 50  # A bit less, but not enough
      self.LP.actP = self.LP.setP
      req = self.regler.get_props()
      self.assertEqual(self.LP.id, req.id, "Request kommt von LP")
      self.assertIn('on', req.flags, "Kein off-Flag")
      self.assertIn('max', req.flags, "Läuft auf max-P")
      self.assertEqual(230, req['min-P'].value, "Minimal-P ist Inkrement")
      self.assertEqual(self.LP.setP - self.LP.minP, req['max-P'].value, "Maximal-P ist Delta zu Min")
      self.assertNotIn('min+P', req, "Keine Leistungserhöhung")
      self.assertNotIn('max+P', req, "Keine Leistungserhöhung")

class TEST_LP1(unittest.TestCase):
   """System mit 1 PV und 1 Ladepunkt"""
   def setUp(self):
      self.core = OpenWBCore(mypath + "/test.conf")
      self.core.config["lpmodul1_mode"] = "pv"
      self.core.config["lpmodul1_alwayson"] = False
      self.PV = StubPV(1)
      self.LP = StubLP(1)
      self.EVU = StubEVU(1)
      self.core.add_module(self.PV, 'wrmodul1')
      self.core.add_module(self.LP, 'lpmodul1')
      self.core.add_module(self.EVU, 'bezugmodul1')

      self.PV.P = 0
      self.LP.actP = 0
      self.EVU.P = 0

      # Zur leichteren Verfügbarkeit
      self.LPregler = self.core.regelkreise['pv'].regler[1]

   def test_consume(self):
      """Bezug, kein Laden, Ruheverbrauch"""
      self.PV.P = 500
      self.EVU.P = 500
      self.core.run(2)
      self.assertEqual(-500, self.core.data.uberschuss, "Kein Überschuss")
      self.assertEqual(1000, self.core.data.hausverbrauch, "Ruheverbrauch")

   def test_supply_toolow(self):
      """Wenig Überschuss, kein Ladestart"""
      self.PV.P = 2200
      self.EVU.P = -1900
      self.core.run(5)
      self.assertEqual(1900, self.core.data.uberschuss, "Überschuss")
      self.assertEqual(300, self.core.data.hausverbrauch, "Ruheverbrauch")
      self.assertEqual(0, self.LP.setP, "Keine Leistungsanforderung")
      self.assertEqual(0, self.LPregler.oncount, "Kein Ladestart")

      with self.subTest("Min-config"):
         self.core.config['lpmodul1_alwayson'] = True
         self.core.run(2)
         self.assertEqual(self.LP.minP, self.LP.setP, "Leistungsanforderung auf Min")

   def test_supply_tooshort(self):
      """Überschuss, Ladestart abgebrochen"""
      self.PV.P = 2300
      self.EVU.P = -2000
      self.core.run(5)
      self.assertEqual(2000, self.core.data.uberschuss, "Überschuss")
      self.assertEqual(self.PV.P + self.EVU.P, self.core.data.hausverbrauch, "Ruheverbrauch")
      self.assertNotEqual(0, self.LPregler.oncount, "Ladestart")
      self.EVU.P = -1000
      self.core.run(1)
      self.assertEqual(0, self.LPregler.oncount, "Kein Ladestart")
      self.assertEqual(0, self.LP.setP, "Keine Leistungsanforderung")

   def test_supply_start(self):
      """Überschuss, Ladestart erfolgreich"""
      self.PV.P = 2300
      self.EVU.P = -2000
      self.core.run(12)
      self.assertEqual(self.LP.minP, self.LP.setP, "Anforderung")

      with self.subTest("Fahrzeug startet"):
         self.LP.actP = 200  # etwas
         self.core.run(1)
         self.assertFalse(self.LP.is_charging, "LP nicht gestartet")
         self.assertEqual(self.LP.minP, self.LP.setP, "Anforderung solange nicht gestartet")
         self.LP.actP = 350  # charging
         self.EVU.P = -1600
         self.core.run(1)
         self.assertTrue(self.LP.is_charging, "LP gestartet")
         self.assertTrue(self.LPregler.blocked, "Regler ist blockiert")
         self.assertEqual(self.LP.minP, self.LP.setP, "Keine Erhöhung bei Blockierung")
         self.assertEqual(self.PV.P + self.EVU.P - self.LP.actP, self.core.data.hausverbrauch, "LP Verbrauch nicht im Hausverbrauch") # XXX

      with self.subTest('Mehr PV-Leistung'):
         self.LP.actP = self.LP.setP - 200  # charge more
         self.core.run(1)
         self.assertEqual(self.LP.minP + self.EVU.pvuberschuss, self.LP.setP, "Erhöhung nach Aufhebung der Blockierung")

      with self.subTest('EVU stabilisiert'):
         last_setP = self.LP.setP
         self.LP.actP = self.LP.setP - 100
         self.EVU.P = -100
         self.core.run(1)
         self.assertEqual(last_setP - self.LP.powerproperties().inc, self.LP.setP, "Reduzierung der Anforderung")

      with self.subTest('Fahrzeug max-Leistung'):
         self.EVU.P = -6000
         self.core.run(2)
         self.LP.actP = 3700
         self.assertEqual(self.LP.maxP, self.LP.setP, "Anforderung auf max")
         self.assertTrue(self.LPregler.blocked, "Regler ist blockiert")

   def test_supply_stop(self):
      """Überschuss, Abschaltung eines LPs"""
      self.PV.P = 2000
      self.EVU.P = -1700
      self.LP.actP = 1000

      self.core.run(15)
      self.assertEqual(self.EVU.pvuberschuss, self.LP.setP, "Anforderung")

      with self.subTest('EVU stabilisiert'):
         last_setP = self.LP.setP
         self.LP.actP = self.LP.setP - 100
         self.EVU.P += last_setP - self.LP.actP
         self.core.run(1)
         self.assertEqual(last_setP + self.EVU.pvuberschuss, self.LP.setP, "Anforderung")
         last_setP = self.LP.setP
         self.EVU.P = -self.core.config.offsetpv - 100
         self.core.run(1)
         self.assertEqual(last_setP, self.LP.setP, "Keine neue Anforderung")

      with self.subTest('EVU sinkt'):
         self.EVU.P += 200
         self.core.run(1)
         self.assertEqual(last_setP - self.LP.powerproperties().inc, self.LP.setP, "Reduzierung um 1A")

      with self.subTest('LP auf min'):
         self.EVU.P = 2000
         self.core.run(1)
         self.assertEqual(self.LP.minP, self.LP.setP, "Anforderung auf Min")

      with self.subTest('LP off'):
         self.LP.set(self.LP.minP+20)
         self.core.run(1)
         self.assertEqual(self.LP.minP, self.LP.setP, "Anforderung auf Min")
         self.assertEqual(0, self.LPregler.offcount, "keine Abchaltung")
         self.LP.actP = self.LP.minP-20
         self.core.run(16)
         self.assertEqual(self.LP.minP, self.LP.setP, "Anforderung auf Min")
         self.assertNotEqual(0, self.LPregler.offcount, "Abchaltungszähler")
         self.core.run(6)
         self.assertEqual(0, self.LP.setP, "Anforderung Abschaltung")

class TEST_LP1_PEAK(unittest.TestCase):
   """System mit 1 PV und 1 Ladepunkt im Peak-mode"""
   def setUp(self):
      self.core = OpenWBCore(mypath + "/test.conf")
      self.core.config["lpmodul1_mode"] = "peak"
      self.core.config["lpmodul1_alwayson"] = False
      self.PV = StubPV(1)
      self.LP = StubLP(1)
      self.EVU = StubEVU(1)
      self.core.add_module(self.PV, 'wrmodul1')
      self.core.add_module(self.LP, 'lpmodul1')
      self.core.add_module(self.EVU, 'bezugmodul1')

      self.PV.P = 0
      self.LP.actP = 0
      self.EVU.P = 0

      # Zur leichteren Verfügbarkeit
      self.LPregler = self.core.regelkreise['peak'].regler[1]

   def test_supply_toolow(self):
      """Zu wenig Überschuss"""
      self.PV.P = 9000
      self.EVU.P = -6400
      self.core.run(5)
      self.assertEqual(6400, self.core.data.uberschuss, "Überschuss")
      self.assertEqual(2600, self.core.data.hausverbrauch, "Ruheverbrauch")
      self.assertEqual(0, self.LP.setP, "Keine Leistungsanforderung")
      self.assertEqual(0, self.LPregler.oncount, "Kein Ladestart")

   def test_supply_start(self):
      """Überschuss, Ladestart erfolgreich"""
      self.PV.P = 9000
      self.EVU.P = -6550
      self.core.run(12)
      self.assertEqual(self.LP.minP, self.LP.setP, "Anforderung")

   def test_supply_stop(self):
      """Überschuss, Ein- u. Abschaltung eines LPs"""
      self.PV.P = 9000
      self.EVU.P = -self.core.config.offsetpvpeak - 100
      self.LP.actP = 2000

      with self.subTest('Ladestart'):
         self.core.run(20)
         self.assertEqual(2300, self.LP.setP, "Anforderung +1A")

      with self.subTest('EVU stabilisiert'):
         last_setP = self.LP.setP
         self.LP.actP = self.LP.setP - 100
         self.EVU.P = -self.core.config.offsetpvpeak + 100
         self.core.run(1)
         self.assertEqual(last_setP, self.LP.setP, "Keine neue Anforderung")

      with self.subTest('EVU sinkt'):
         self.EVU.P += 200
         self.core.run(1)
         self.assertEqual(last_setP-300, self.LP.setP, "Reduzierung um delta")

      with self.subTest('LP auf min'):
         self.EVU.P = -self.core.config.offsetpvpeak + 1500
         self.core.run(1)
         self.assertEqual(self.LP.minP, self.LP.setP, "Anforderung auf Min")

      with self.subTest('LP off'):
         self.LP.setP = self.LP.minP+20
         self.EVU.P = -self.core.config.offsetpvpeak + 1800
         self.core.run(1)
         self.assertEqual(self.LP.minP, self.LP.setP, "Anforderung auf Min")
         self.assertEqual(0, self.LPregler.offcount, "keine Abchaltung")
         self.LP.actP = self.LP.minP-20
         self.core.run(16)
         self.assertEqual(self.LP.minP, self.LP.setP, "Anforderung auf Min")
         self.assertNotEqual(0, self.LPregler.offcount, "Abchaltungszähler")
         self.core.run(6)
         self.assertEqual(0, self.LP.setP, "Anforderung Abschaltung")

class TEST_LP2(unittest.TestCase):
   """System mit 1 PV und 2 Ladepunkte im PV-mode"""
   def setUp(self):
      self.core = OpenWBCore(mypath + "/test.conf")
      self.core.config["lpmodul1_mode"] = "pv"
      self.core.config["lpmodul2_mode"] = "pv"
      self.core.config["lpmodul1_alwayson"] = False
      self.PV = StubPV(1)
      self.LP1 = StubLP(1)
      self.LP2 = StubLP(2)
      self.EVU = StubEVU(1)
      self.core.add_module(self.PV, 'wrmodul1')
      self.core.add_module(self.LP1, 'lpmodul1')
      self.core.add_module(self.LP2, 'lpmodul2')
      self.core.add_module(self.EVU, 'bezugmodul1')

      self.PV.P = 0
      self.LP1.actP = 0
      self.LP2.actP = 0
      self.EVU.P = 0

      # Zur leichteren Verfügbarkeit
      self.LPregler1 = self.core.regelkreise['pv'].regler[1]
      self.LPregler2 = self.core.regelkreise['pv'].regler[2]

   def test_supply_start1(self):
      """Überschuss, Ladestart erfolgreich"""
      self.PV.P = 2300
      self.EVU.P = -2000
      self.core.run(5)
      self.assertEqual(2000, self.core.data.uberschuss, "Überschuss")
      self.assertNotEqual(0, self.LPregler1.oncount, "Ladestart LP1")
      self.assertEqual(0, self.LPregler2.oncount, "kein Ladestart LP2")

      self.core.run(6)
      self.assertEqual(self.LP1.minP, self.LP1.setP, "Anforderung LP1")
      self.assertEqual(0, self.LP2.setP, "keine Anforderung LP2")

   def test_supply_start2(self):
      """Überschuss, Ladestart 2 LPs erfolgreich"""
      self.PV.P = 4000
      self.EVU.P = -3800
      self.core.run(5)
      self.assertEqual(3800, self.core.data.uberschuss, "Überschuss")
      self.assertNotEqual(0, self.LPregler1.oncount, "Ladestart LP1")
      self.assertNotEqual(0, self.LPregler2.oncount, "Ladestart LP2")

      self.core.run(6)
      self.assertEqual(self.LP1.minP, self.LP1.setP, "Anforderung LP1")
      self.assertEqual(self.LP2.minP, self.LP2.setP, "Anforderung LP2")

   def test_raise(self):
      """Wachsender Überschuss, LPs balanciert"""
      self.PV.P = 2300
      self.EVU.P = -2000
      with self.subTest('LP1 on'):
         self.core.run(12)
         self.assertEqual(self.LP1.minP, self.LP1.setP, "Anforderung LP1")
         self.assertEqual(0, self.LP2.setP, "keine Anforderung LP2")
         self.LP1.actP = 1300
         self.EVU.P += 1300
         self.core.run(5)
         self.assertEqual(0, self.LPregler2.oncount, "kein Ladestart LP2")
         self.assertEqual(0, self.LP2.setP, "keine Anforderung LP2")
         self.LP1.actP = 1800

      with self.subTest('Raise power'):
         self.EVU.P -= 1300
         last_setP = self.LP1.setP
         self.core.run(5)
         self.assertEqual(last_setP + self.EVU.pvuberschuss, self.LP1.setP, "Erhöhe Anforderung LP1")
         self.assertNotEqual(0, self.LPregler2.oncount, "Ladestart LP2")

         deltaP = self.LP1.setP - self.LP1.actP - 100 # LP1 folgt Anforderung
         self.EVU.P += deltaP
         self.LP1.actP += deltaP
         self.core.run(6)
         self.assertEqual(self.LP2.minP, self.LP2.setP, "Einschalten LP2 über LP1-Budget")

class TEST_LP1_SOFORT(unittest.TestCase):
   """System mit 1 PV und 1 Ladepunkt im Sofort-mode"""
   def setUp(self):
      self.core = OpenWBCore(mypath + "/test.conf")
      self.core.config["lpmodul1_mode"] = "sofort"
      self.LP = StubLP(1)
      self.core.add_module(self.LP, 'lpmodul1')

      self.LP.actP = 0

      # Zur leichteren Verfügbarkeit
      self.LPregler = self.core.regelkreise['sofort'].regler[1]

   def test_startup(self):
      """Initialisierung"""
      self.core.config["lpmodul1_sofortll"] = 10
      self.core.run(1)
      self.assertEqual(2300, self.LP.setP, "Anforderung eingestellter Strom")

      self.core.config["lpmodul1_sofortll"] = 20
      self.core.run(1)
      self.assertEqual(4600, self.LP.setP, "Anforderung veränderter Strom")

if __name__ == '__main__':
   unittest.main()
