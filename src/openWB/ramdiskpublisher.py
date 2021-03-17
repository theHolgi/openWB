from openWB.Scheduling import Scheduler
from typing import Iterator
from openWB.openWBlib import RamdiskValues

class RamdiskPublisher(object):
   priority = 999
   datamapping = {
      # ramdisk file: data name
      # EVU
      'evu/VPhase%p': 'evuv%p',
      'evu/PfPhase%p': 'evupf%p',
      'evu/APhase%p': 'evua%p',
      'evu/WPhase%p': 'bezugw%p',
      'evu/ASchieflast': 'schieflast',
      'evu/Hz': 'evuhz',
      'evu/W': 'wattbezug',
      'evu/WhExported': 'einspeisungkwh',
      'evu/WhInported': 'bezugkwh',

      # Ladepunkt
      'lp/W': 'llaktuell',
      # 'llsoll'
      # 'llsolls1'
      # 'llas1%p'
      # 'soc'
      'llv%p': 'llv%p1',
      'lla%p': 'lla%p1',
      'llpf%p': 'llpf%p1',

      'llaktuell': 'llaktuell1',
      'llkwh': 'aktgeladen1',
      'llkwhges': 'llkwh',

      # Speicher
      'housebattery/WhInported': 'speicherikwh',
      'housebattery/WhExported': 'speicherekwh',
      'housebattery/%Soc': 'speichersoc',

      # PV
      'pv/W': 'pvallwatt',
      'pv/1/W': 'pvwatt1',
      # 'pvcounter'
      'pv/kwh': 'pvkwh',
      'daily_pvkwhk': 'daily_pvkwh',
      'monthly_pvkwhk': 'monthly_pvkwh'
      # 'yearly_pvkwhk'
      # 'daily_pvkwhk1'
      # 'monthly_pvkwhk1'
      # 'yearly_pvkwhk1'

   }
   """Mirrors selected data to the ramdisk. Required for legacy PHP status"""
   def __init__(self, core):
      self.ramdisk = RamdiskValues()
      self.data = core.data
      self.setup()

   def setup(self):
      scheduler = Scheduler()
      scheduler.registerData(['pv/*'], self)

   @staticmethod
   def _loop(key: str, key2: str = None) -> Iterator[str]:
      if key.find('%n') >= 0:  # Instance
         for n in range(1, 9):  # num_lps + 1
            for k1, k2 in RamdiskPublisher._loop(key.replace('%n', str(n)), key2.replace('%n', str(n))):
               yield k1, k2
      elif key.find('%p') >= 0:  # Phase
         for phase in range(1, 4):
            yield key.replace('%p', str(phase)), key2.replace('%p', str(phase))
      else:
         yield key, key2

   def newdata(self, data):
      for k, v in data.items():
         if k in self.datamapping:
           self.ramdisk[self.datamapping[k]] = v
