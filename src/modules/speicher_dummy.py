from openWB.Modul import Speichermodul
from openWB.Scheduling import Scheduler


class DUMMYWR(Speichermodul):
   """Dummy Wechselrichter"""
   def setup(self, config):
      self.P  = 0
      self.soc = 0
      self.kwhOut = 0
      self.kwhIn = 0
      Scheduler().registerTimer(1, self)

   def loop(self):
      self.send({
         'W': self.P,
         'soc': self.soc,
         'kwhOut': self.kwhOut,
         'kwhIn': self.kwhIn}
      )


def getClass():
   return DUMMYWR
