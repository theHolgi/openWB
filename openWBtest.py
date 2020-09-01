import unittest
from openWB.openWBlib import *
from openWB import *
from openWB.OpenWBCore import OpenWBCore
from openWB.regler import *
global core

mypath = os.path.dirname(os.path.realpath(__file__)) + '/'

class StubCore():
   config = openWBconfig('test.conf')

class StubPV(DataProvider, PVModul):
   P = 0
   def trigger(self):
      self.core.sendData(DataPackage(self, {'pvwatt': -self.P}))

class StubLP(DataProvider, Ladepunkt):
   actP = 0
   I = 0
   phasen = 1

   def trigger(self):
      self.core.sendData(DataPackage(self, {'llaktuell': self.actP}))

   def powerproperties(self):
      return PowerProperties(minP=self.phasen*230*6,
                             maxP=self.phasen*230*25,
                             inc=self.phasen*230)

   def set(self, power: int):
      self.setP = power

class StubEVU(DataProvider):
   P = 0
   def trigger(self):
      self.core.sendData(DataPackage(self, {'wattbezug': self.P}))


class TEST_PV1LP1(unittest.TestCase):
   """System mit 1 PV und 1 Ladepunkt"""
   def setUp(self):
      self.core = OpenWBCore(mypath)
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

   def test_supply_toofew(self):
      """Wenig Überschuss, kein Ladestart"""
      self.PV.P = 800
      self.EVU.P = -500
      self.core.run(5)
      self.assertEqual(500, self.core.data.uberschuss, "Überschuss")
      self.assertEqual(300, self.core.data.hausverbrauch, "Ruheverbrauch")
      self.assertEqual(0, self.LP.setP, "Keine Leistungsanforderung")
      self.assertEqual(0, self.LPregler.oncount, "Kein Ladestart")
      self.assertEqual(0, self.LP.I, "Keine Ladung gestartet")

   def test_supply_tooshort(self):
      """Überschuss, Ladestart abgebrochen"""
      self.PV.P = 2000
      self.EVU.P = -1700
      self.core.run(5)
      self.assertEqual(1700, self.core.data.uberschuss, "Überschuss")
      self.assertEqual(300, self.core.data.hausverbrauch, "Ruheverbrauch")
      self.assertNotEqual(0, self.LPregler.oncount, "Ladestart")
      self.EVU.P = -1000
      self.core.run(1)
      self.assertEqual(0, self.LPregler.oncount, "Kein Ladestart")
      self.assertEqual(0, self.LP.setP, "Keine Leistungsanforderung")
      self.assertEqual(0, self.LP.I, "Keine Ladung gestartet")

   def test_supply_start(self):
      """Überschuss, Ladestart erfolgreich"""
      self.PV.P = 2000
      self.EVU.P = -1700
      self.core.run(12)
      self.assertEqual(10, self.LPregler.oncount, "Ladestart")
      self.assertEqual(1500, self.LP.setP, "Anforderung")   # TODO: Eigentlich nur minP

      with self.subTest("Fahzeug startet"):
         self.LP.actP = 500  # etwas
         self.core.run(1)
         # self.assertEqual(1500, self.LP.setP, "Anforderung solange nicht gestartet")  # TODO: Eigentlich nur minP
         self.LP.charging = True
         self.core.run(1)
         self.assertEqual(self.LP.actP + 1500, self.LP.setP, "Erhöhte Anforderung")
         ...

      with self.subTest('Mehr PV-Leistung'):
         self.EVU.P = -2000
         self.core.run(1)
         self.assertEqual(self.LP.actP+1800, self.LP.setP, "Anforderung")

      with self.subTest('Fahrzeug max-Leistung'):
         self.LP.actP = 3700  # max
         self.EVU.P = -6000
         self.core.run(8)
         self.assertEqual(self.LP.maxP, self.LP.setP, "Anforderung auf max")
         self.core.run(4)
         self.assertEqual(3910, self.LP.setP, "Reduzierte Anforderung")

class Test_Regler(unittest.TestCase):
   """Teste Regler Klasse"""
   EVU = StubEVU(1)
   LP = StubLP(1)
   LP.core = StubCore()
   LP.id = 1

   def setUp(self):
      self.regler = Regler(self.LP)
      self.LP.I = 0
      self.LP.P = 0
      self.LP.charging = False

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

   def test_atminP(self):
      self.LP.charging = True
      self.LP.actP = self.LP.minP + 50  # A bit more, but not enough
      req = self.regler.get_props()
      self.assertEqual(self.LP.id, req.id, "Request kommt von LP")
      self.assertIn('on', req.flags, "Kein off-Flag")
      self.assertIn('min', req.flags, "Läuft auf min-P")
      self.assertEqual(230, req['min+P'].value, "Minimal+P ist Inkrement")
      self.assertEqual(self.LP.maxP - self.LP.actP, req['max+P'].value, "Maximal+P ist Delta zu Max")
      self.assertEqual(self.LP.minP, req['min-P'].value, "Minimal-P ist Abschaltung")
      self.assertEqual(self.LP.minP, req['max-P'].value, "Maximal-P ist Abschaltung")

   def test_atmiddle(self):
      self.LP.charging = True
      self.LP.actP = self.LP.minP + 1000  # Somewhere
      req = self.regler.get_props()
      self.assertEqual(self.LP.id, req.id, "Request kommt von LP")
      self.assertIn('on', req.flags, "Kein off-Flag")
      self.assertNotIn('min', req.flags, "Läuft nicht auf min-P")
      self.assertNotIn('max', req.flags, "Läuft nicht auf max-P")
      self.assertEqual(230, req['min+P'].value, "Minimal+P ist Inkrement")
      self.assertEqual(230, req['min-P'].value, "Minimal-P ist Inkrement")
      self.assertEqual(self.LP.actP - self.LP.minP, req['max-P'].value, "Maximal-P ist Delta zu Min")
      self.assertEqual(self.LP.maxP - self.LP.actP, req['max+P'].value, "Maximal+P ist Delta zu Max")

   def test_atmaxP(self):
      self.LP.charging = True
      self.LP.actP = self.LP.maxP - 50  # A bit less, but not enough
      req = self.regler.get_props()
      self.assertEqual(self.LP.id, req.id, "Request kommt von LP")
      self.assertIn('on', req.flags, "Kein off-Flag")
      self.assertIn('max', req.flags, "Läuft auf max-P")
      self.assertEqual(230, req['min-P'].value, "Minimal-P ist Inkrement")
      self.assertEqual(self.LP.actP - self.LP.minP, req['max-P'].value, "Maximal-P ist Delta zu Min")
      self.assertNotIn('min+P', req, "Keine Leistungserhöhung")
      self.assertNotIn('max+P', req, "Keine Leistungserhöhung")

if __name__ == '__main__':
   unittest.main()
