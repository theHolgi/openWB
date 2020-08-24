from openWB import *


class TRIPOWER(DataProvider, PVModul):
   """SMA Tripower"""
   def trigger(self):
      self.core.sendData(DataPackage(self, {'pvwatt': -5000}))

   def event(self):
      pass

def getClass():
   return TRIPOWER
