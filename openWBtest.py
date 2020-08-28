import unittest
from openWB.openWBlib import *
from openWB import *
from openWB.OpenWBCore import OpenWBCore
from openWB.regler import Regler
global core

mypath = os.path.dirname(os.path.realpath(__file__)) + '/'

class StubCore():
   config = openWBconfig('test.conf')

class StubPV(DataProvider, PVModul):
   P = 0
   def trigger(self):
      self.core.sendData(DataPackage(self, {'pvwatt': -self.P}))

class StubLP(DataProvider, Ladepunkt):
   P = 0
   I = 0
   phasen = 1

   def trigger(self):
      self.core.sendData(DataPackage(self, {'llaktuell': self.P}))

   def set(self, amp:int):
      self.I = amp

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
      self.LP.P = 0
      self.EVU.P = 0

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
      self.assertEqual(0, self.core.ladepunkte[0].lastrequest.power, "Keine Leistungsanforderung")
      self.assertEqual(0, self.core.ladepunkte[0].oncount, "Kein Ladestart")
      self.assertEqual(0, self.LP.I, "Keine Ladung gestartet")

   def test_supply_tooshort(self):
      """Überschuss, Ladestart abgebrochen"""
      self.PV.P = 2000
      self.EVU.P = -1500
      self.core.run(5)
      self.assertEqual(1500, self.core.data.uberschuss, "Überschuss")
      self.assertEqual(500, self.core.data.hausverbrauch, "Ruheverbrauch")
      self.assertEqual(1380, self.core.ladepunkte[0].lastrequest.power, "Leistungsanforderung")
      self.assertIn('ondelay', self.core.ladepunkte[0].lastrequest.flags, "Startflag")
      self.EVU.P = -1000
      self.core.run(1)
      self.assertEqual(0, self.core.ladepunkte[0].lastrequest.power, "Keine Leistungsanforderung")
      self.assertEqual(0, self.core.ladepunkte[0].oncount, "Kein Ladestart")
      self.assertEqual(0, self.LP.I, "Keine Ladung gestartet")

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

   def cycle(self, n: int, data: DataProvider):
      for i in range(n):
         req = self.regler.request(data)
         self.regler.set(req.power)
      return req

   def test_consume(self):
      """Bezug"""
      data = openWBValues()
      data.update(DataPackage(self.EVU, {'uberschuss': -500}))
      req = self.regler.request(data)
      self.assertEqual(0, req.power, "Keine Anforderung")
      self.assertEqual(0, self.regler.oncount, "Kein Ladestart")

   def test_notplugged(self):
      """Überschuss, kein Fahrzeug"""
      data = openWBValues()
      data.update(DataPackage(self.EVU, {'uberschuss': 5000}))
      data.update(DataPackage(self.LP,  {'plugstat': 0}))
      req = self.regler.request(data)
      self.assertEqual(0, req.power, "Keine Anforderung")
      self.assertEqual(0, self.regler.oncount, "Kein Ladestart")

   def test_supply_toofew(self):
      """zu wenig Überschuss"""
      data = openWBValues()
      data.update(DataPackage(self.EVU, {'uberschuss': 500}))
      data.update(DataPackage(self.LP,  {'plugstat': 1}))
      req = self.regler.request(data)
      self.assertEqual(0, req.power, "Keine Anforderung")
      self.assertEqual(0, self.regler.oncount, "Kein Ladestart")

   def test_supply_tooshort(self):
      """Überschuss, Abbruch im Einschaltdelay"""
      data = openWBValues()
      data.update(DataPackage(self.EVU, {'uberschuss': 1500}))
      req = self.cycle(5, data)
      self.assertEqual(1380, req.power, "Anforderung")
      self.assertEqual(6, req.amp, "Minimalstrom")
      self.assertIn('ondelay', req.flags, "Ladeverzögerung")
      self.assertEqual(5, self.regler.oncount, "Ladestart")

      data.update(DataPackage(self.EVU, {'uberschuss': 1000}))
      req = self.cycle(1, data)
      self.assertEqual(0, req.power, "Keine Anforderung")
      self.assertEqual(0, self.regler.oncount, "Kein Ladestart")
      self.assertEqual(0, self.LP.I, 'Kein Ladestrom')

   def test_supply_start(self):
      """Überschuss, Starte Ladung"""
      data = openWBValues()
      data.update(DataPackage(self.EVU, {'uberschuss': 1500}))
      req = self.cycle(15, data)
      self.assertEqual(1380, req.power, "Anforderung")
      self.assertEqual(6, req.amp, "Minimalstrom")
      self.assertNotIn('ondelay', req.flags, "Keine Ladeverzögerung")
      self.assertEqual(15, self.regler.oncount, "Ladestart")
      self.assertEqual(6, self.LP.I, 'Ladestrom')

      with self.subTest("Fahzeug startet"):
         data.update(DataPackage(self.LP,  {'llaktuell': 500}))  # etwas
         req = self.cycle(1, data)
         self.assertEqual(1380, req.power, "Anforderung")
         self.assertNotIn('ondelay', req.flags, 'Keine Ladeverzögerung')
         data.update(DataPackage(self.LP,  {'llaktuell': 1000}))  # mehr
         req = self.cycle(1, data)
         self.assertEqual(1500, req.power, "Anforderung gesamte PV-Leistung")
         self.assertEqual(power2amp(1500, 1), req.amp, "passender Strom")

      with self.subTest('Mehr PV-Leistung'):
         data.update(DataPackage(self.EVU, {'uberschuss': 2000}))
         req = self.cycle(1, data)
         self.assertEqual(2000, req.power, "Anforderung")
         self.assertEqual(8, req.amp, "Mehr Strom")

      with self.subTest('Fahrzeug max-Leistung'):
         data.update(DataPackage(self.LP,  {'llaktuell': 3700}))  # Max. Ladeleistung
         data.update(DataPackage(self.EVU, {'uberschuss': 6000}))
         req = self.cycle(8, data)
         self.assertEqual(5750, req.power, "Anforderung max-Leistung")
         self.assertEqual(25, req.amp,     "Max Strom")
         self.assertNotIn('blocked', req.flags, 'Keine Blockierung')
         req = self.cycle(4, data)
         self.assertEqual(3910, req.power, "Reduzierte Anforderung")
         self.assertEqual(power2amp(3910, 1), req.amp, "Reduzierter Strom")
         self.assertIn('blocked', req.flags, 'Blockierung')


if __name__ == '__main__':
   unittest.main()
