from openWB.Modul import Ladepunkt, power2amp
from openWB.Scheduling import Scheduler


class DUMMYLP(Ladepunkt):
   """Dummy Ladepunkt"""
   def setup(self, config):
      super().setup(config)
      self.A  = 0
      self.kwh = 0
      Scheduler().registerTimer(1, self.loop)

   def loop(self):
      data = {
         'W': self.actP,
         'A': self.A,
         'kwh': self.kwh}
      data.update((att, getattr(self, att)) for att in ['A1', 'A2', 'A3', 'V1', 'V2', 'V3'] if hasattr(self, att))
      self.send(data)

   def set(self, power: int) -> None:
      self.setP = power
      self.A = power2amp(power, self.phasen)


def getClass():
   return DUMMYLP
