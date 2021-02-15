from openWB.Modul import Ladepunkt, power2amp, PowerProperties
from openWB.Scheduling import Scheduler


class DUMMYLP(Ladepunkt):
   """Dummy Ladepunkt"""
   override_blocked = None

   def setup(self, config):
      super().setup(config)
      self.A  = 0
      self.kwh = 0
      self.minI = config.get('minimalstromstaerke')
      self.maxI = config.get('maximalstromstaerke')
      Scheduler().registerTimer(1, self.loop)

   def loop(self):
      data = {
         'W': self.actP,
         'kwh': self.kwh}
      data.update((att, getattr(self, att)) for att in ['A1', 'A2', 'A3', 'V1', 'V2', 'V3'] if hasattr(self, att))
      # fake mindestens A1 für die Blockiererkennung
      if 'A1' not in data:
         data['A1'] = self.actP / self.phasen / data.get('V1', 230)
      self.send(data)

   def set(self, power: int) -> None:
      self.setP = power
      self.send({'A': power2amp(power, self.phasen)})

   def powerproperties(self):
      return PowerProperties(minP=self.phasen*230*self.minI,
                             maxP=self.phasen*230*self.maxI,
                             inc=self.phasen*230)

   @property
   def is_blocked(self):
      if self.override_blocked is not None:
         return self.override_blocked
      else:
         return super().is_blocked


def getClass():
   return DUMMYLP
