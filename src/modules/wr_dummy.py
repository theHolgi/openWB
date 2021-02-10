from openWB.Modul import PVModul
from openWB.Scheduling import Scheduler


class DUMMYWR(PVModul):
   """Dummy Wechselrichter"""
   def setup(self, config):
      self.P  = 0
      self.Wh = 0
      Scheduler().registerTimer(1, self.loop)

   def loop(self):
      self.send({
         'W': self.P,
         'kwh': self.Wh}
      )


def getClass():
   return DUMMYWR
