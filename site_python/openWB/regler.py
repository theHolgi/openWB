from collections import namedtuple
import enum


Request = namedtuple('Request', 'id power priority')

class Priority(enum.IntEnum):
   low = 1
   medium = 2
   high = 3
   forced = 4


class Regler:
   """Eine Reglerinstanz"""

   def __init__(self, wallbox):
      self.mode = "pv"
      self.wallbox = wallbox

   def request(self, data) -> Request:
      if self.mode == "pv":
         if data.uberschuss > 1000:
            return Request(self.wallbox.id, data.uberschuss/2, Priority.low)
         else:
            return Request(self.wallbox.id, 0, Priority.low)

   def set(self, power: int) -> None:
      """Set the given power"""
      self.wallbox.set(power)
