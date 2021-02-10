from openWB.Modul import Speichermodul
from openWB.Scheduling import Scheduler
from openWB.Event import *

class DUMMYWR(Speichermodul):
   """Dummy Wechselrichter"""
   def setup(self, config):
      self.P  = 0
      self.soc = 0
      self.kwhOut = 0
      self.kwhIn = 0
      self.dailyOffsetOut = 0
      self.dailyOffsetIn = 0
      Scheduler().registerTimer(1, self.loop)
      Scheduler().registerEvent(EventType.resetDaily, self.daily)

   def loop(self) -> None:
      self.send({
         'W': self.P,
         'soc': self.soc,
         'kwhOut': self.kwhOut - self.dailyOffsetOut,
         'kwhIn': self.kwhIn - self.dailyOffsetIn}
      )

   def daily(self, event: OpenWBEvent) -> None:
      self.dailyOffsetOut = self.kwhOut
      self.dailyOffsetIn = self.kwhIn


def getClass():
   return DUMMYWR
