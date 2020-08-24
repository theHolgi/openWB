from openWB import *


class GO_E(DataProvider, Ladepunkt):
   """SMA Smart home Meter (or Energy Meter)"""
   def trigger(self):
      self.core.sendData(DataPackage(self, {'lp_i': 10, 'ladeleistunglp': 1000}))

   def event(self):
      pass

   def set(self, power:int) -> None:
      print("%i lädt mit %i Watt" % (self.id, power))


def getClass():
   return GO_E
