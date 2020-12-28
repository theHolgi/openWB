from typing import Iterator


class RamdiskPublisher(object):
   datamapping = {
      # ramdisk file: data name
      # EVU
      'evuv%p': 'evuv%p',
      'evupf%p': 'evupf%p',
      'bezuga%p': 'evua%p',
      'bezugw%p': 'bezugw%p',
      'schieflast': 'schieflast',
      'evuhz': 'evuhz',
      'wattbezug': 'wattbezug',
      'einspeisungkwh': 'einspeisungkwh',
      'bezugkwh': 'bezugkwh',

      # Ladepunkt
      'llkombiniert': 'llaktuell',
      # 'llsoll'
      # 'llsolls1'
      # 'llas1%p'
      # 'soc'
      'llv%p': 'llv%p1',
      'lla%p': 'lla%p1',
      'llpf%p': 'llpf%p1',

      'llaktuell': 'llaktuell1',
      'llkwh': 'aktgeladen1',

      # Speicher
      'speicherikwh': 'speicherikwh',
      'speicherekwh': 'speicherekwh',

      # PV
      'pvallwatt': 'pvwatt',
      'pvwatt1': 'pvwatt1',
      # 'pvcounter'
      # 'pvallwh'
      'daily_pvkwhk': 'daily_pvkwh',
      'monthly_pvkwhk': 'monthly_pvkwh'
      # 'yearly_pvkwhk'
      # 'daily_pvkwhk1'
      # 'monthly_pvkwhk1'
      # 'yearly_pvkwhk1'

   }
   """Mirrors selected data to the ramdisk. Required for legacy PHP status"""
   def __init__(self, core):
      self.ramdisk = core.ramdisk
      self.data = core.data

   def setup(self):
      pass

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

   def publish(self):
      for k, v in self.datamapping.items():
        for key, datakey in self._loop(k, v):
           self.ramdisk[key] = self.data.get(datakey)
