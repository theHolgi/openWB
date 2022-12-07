from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Iterable, Any, List, Tuple


class CsvLog:
   def __init__(self, filename: Path, keyfields: List[int]):
      self.keys = set()
      self.keyfields = keyfields
      if filename.exists():
         with filename.open() as f:
            self.keys.update(self._gen_key(list(line.split(','))) for line in f.readlines())
      self.handle = filename.open('a')

   def __del__(self):
      self.handle.close()

   def has(self, *key) -> bool:
      return tuple(map(str, key)) in self.keys

   def write(self, values: Iterable[Any]) -> bool:
      key = self._gen_key(values)
      if key not in self.keys:
         self.handle.write(','.join(map(str, values)))
         self.keys.add(key)
         return True
      else:
         return False

   def _gen_key(self, values: List[Any]) -> Tuple[str]:
      return tuple(str(values[index]) for index in self.keyfields)


def tomorrow_at_6() -> datetime:
   now = datetime.now()
   if now.hour < 6:
      tomorrow = datetime.combine(now.date(), time(hour=6))
   else:
      now += timedelta(days=1)
      tomorrow = datetime.combine(now.date(), time(hour=6))
   return tomorrow
