from openWB import *


class SMASHM(DataProvider):
   """SMA Smart home Meter (or Energy Meter)"""

   def trigger(self):
      self.core.sendData(DataPackage(self, {
         'wattbezug': -3000,
         'kwh': 10,
         'evua1': 1,
         'evua2': 2,
         'evua3': 3,
         'evuv1': 230,
         'evuv2': 232,
         'evuv3': 233,
         'frequenz': 50
      }))

   def event(self):
      pass

def getClass():
   return SMASHM
