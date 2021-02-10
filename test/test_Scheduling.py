import logging
import unittest

from openWB import DataPackage
from openWB.Event import *
from openWB.Scheduling import Scheduler

logging.getLogger().setLevel(logging.DEBUG)


class Listener:
   def __init__(self):
      self.data = []
      self.executed = 0

   def newData(self, data: DataPackage):
      self.data.append(data)

   def loop(self):
      self.executed += 1


class TestScheduling(unittest.TestCase):
   def setUp(self):
      self.listener1 = Listener()
      self.listener2 = Listener()
      if '_inst' in vars(Scheduler):   # Delete the Scheduler singleton
         del Scheduler._inst

   def test_dataUpdate_1listener(self):
      Scheduler().registerData(['/some/path/*', '/another/path/*'], self.listener1.newData)
      Scheduler().dataUpdate(DataPackage(Listener, {
         '/some/other/path': 1,
         '/some/path/a': 2}))
      Scheduler().dataUpdate(DataPackage(Listener, {
         '/some/path/subpath/b': 3,
         '/another/path/c': 4
      }))
      Scheduler.simulated = True
      Scheduler().dataRunner.join()
      self.assertEqual(1, len(self.listener1.data), "Listener 1 has received one package")
      self.assertDictEqual({
         '/some/path/a': 2,
         '/some/path/subpath/b': 3,
         '/another/path/c': 4
      }, self.listener1.data[0], "Listener shall have received the registered data branches")

   def test_dataUpdate_2listeners(self):
      Scheduler().registerData(['/some/path/*'], self.listener1.newData)
      Scheduler().registerData(['/another/path/*'], self.listener1.newData)
      Scheduler().registerData(['/some/path/a'], self.listener2.newData)
      Scheduler().registerData(['/another/path/*'], self.listener2.newData)
      Scheduler().dataUpdate(DataPackage(Listener, {
         '/some/other/path': 1,
         '/some/path/a': 2}))
      Scheduler().dataUpdate(DataPackage(Listener, {
         '/some/path/subpath/b': 3,
         '/another/path/c': 4
      }))
      Scheduler.simulated = True
      Scheduler().dataRunner.join()
      self.assertEqual(1, len(self.listener1.data), "Listener 1 has received one package")
      self.assertEqual(1, len(self.listener2.data), "Listener 2 has received one package")
      self.assertDictEqual({
         '/some/path/a': 2,
         '/some/path/subpath/b': 3,
         '/another/path/c': 4
      }, self.listener1.data[0], "Listener 1 shall have received his registered data branches")
      self.assertDictEqual({
         '/some/path/a': 2,
         '/another/path/c': 4
      }, self.listener2.data[0], "Listener 2 shall have received her registered data branches")

   def test_scheduling(self):
      Scheduler().registerTimer(5, self.listener1.loop)
      Scheduler().registerTimer(10, self.listener2.loop)
      Scheduler().run(simulated=True)
      self.assertEqual(2, self.listener1.executed)
      self.assertEqual(1, self.listener2.executed)

   def test_eventListener(self):
      self.daily = False
      self.monthly = False
      def dailyReset(event):
         self.daily = True
      def monthlyReset(event):
         self.monthly = True
      Scheduler().registerEvent(EventType.resetDaily, dailyReset)
      Scheduler().registerEvent(EventType.resetMonthly, monthlyReset)
      Scheduler().signalEvent(OpenWBEvent(EventType.resetDaily, info="Info"))
      self.assertTrue(self.daily)
      self.assertFalse(self.monthly)

if __name__ == '__main__':
   unittest.main()
