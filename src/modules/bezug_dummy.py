from openWB.Modul import EVUModul
from openWB.Scheduling import Scheduler


class DUMMYEVU(EVUModul):
   """Dummy EVU"""
   def setup(self, config):
      self.P  = 0
      self.kwhOut = 0
      self.kwhIn = 0
      # Weitere Attribute:
      # A1..A3
      # V1..V3
      Scheduler().registerTimer(1, self.loop)

   def loop(self):
      data = {
         'W': self.P,
         'kwhOut': self.kwhOut,
         'kwhIn': self.kwhIn}
      data.update((att, getattr(self, att)) for att in ['A1', 'A2', 'A3', 'V1', 'V2', 'V3'] if hasattr(self, att))
      self.send(data)


def getClass():
   return DUMMYEVU
