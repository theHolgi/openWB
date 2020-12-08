from typing import Iterator


class RamdiskPublisher(object):
   datamapping = {
      # ramdisk file: data name
      'evuv%p': 'evuv%p',
      'bezuga%p': 'evua%p',
      'bezugw%p': 'evup%p',
      'schieflast': 'schieflast'
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
            if key2 is None:
               for k1 in RamdiskPublisher._loop(key.replace('%n', str(n))):
                  yield k1
            else:
               for k1, k2 in RamdiskPublisher._loop(key.replace('%n', str(n)), key2.replace('%n', str(n))):
                  yield k1, k2
      elif key.find('%p') >= 0:  # Phase
         for phase in range(1, 4):
            if key2 is None:
               yield key.replace('%p', str(phase))
            else:
               yield key.replace('%p', str(phase)), key2.replace('%p', str(phase))

   def publish(self):
      for k, v in self.datamapping.items():
        for key, datakey in self._loop(k, v):
           self.ramdisk[key] = self.data[datakey]