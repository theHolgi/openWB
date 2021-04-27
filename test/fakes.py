from typing import Any


class FakeRamdisk:
   def __init__(self):
      self.vals = {}

   def __getitem__(self, item) -> Any:
      return self.vals.get(item)

   def __setitem__(self, item, value) -> None:
      self.vals[item] = value

