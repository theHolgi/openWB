import enum
from typing import Set
from . import power2amp

class Priority(enum.IntEnum):
   low = 1
   medium = 2
   high = 3
   forced = 4

# dataclass would be great here, but requires Python 3.7
class Request:
   def __init__(self, id: int, power: int = 0, amp: int = 0, priority: Priority = Priority.low, flags: Set[str] = None):
      self.id = id
      self.power = power
      self.amp = amp
      self.priority = priority
      self.flags = set() if flags is None else flags  # can't do this in function default, as this will return the same single object for every usage.

# Arbeitsweise:
# Definition:
#  - minP = (Phasen * Min erlaubte Ampere):
#  - maxP = (Phasen * Max erlaubte Ampere)
# A) PV-Modus:
# - Ladung nicht aktiv:
#   Wenn Überschuss > minP
#      Anforderung minP, Prio x, Einschaltverzögerung aktiv
# - Ladung aktiv:
#   Wenn Ist-P < zuletzt angefordertes P: Alte Anforderung. Zähle Verzögerungszähler
#   Wenn Verzögerungszähler > x: Status "Max-Leistung erreicht"; Anforderung Ist-P

class Regler:
   """Eine Reglerinstanz"""

   def __init__(self, wallbox):
      self.mode = "pv"
      self.wallbox = wallbox
      self.oncount = 0
      self.offcount = 0
      self.blockcount = 0
      self.state = 'idle'
      self.request = self.pv_request_idle
      self.set = self.set_idle
      self.lastrequest = None
      self.current_i = 0
      self.current_p = 0
      self.config = self.wallbox.core.config

   @property
   def minP(self):
      return self.config.minimalstromstaerke * self.wallbox.phasen * 230

   @property
   def maxP(self):
      return self.config.maximalstromstaerke * self.wallbox.phasen * 230

   def pv_request_idle(self, data: "openWBValues") -> Request:
      """request function for PV/idle and PV/init mode"""
      if data.get('plugstat', id=self.wallbox.id, default=1) == 0:
         # Auto (bekannt) nicht eingesteckt: Keine Anforderung nötig
         return Request(id=self.wallbox.id)
      if data.uberschuss <= self.minP:
         self.lastrequest = Request(id=self.wallbox.id)
      else:
         self.lastrequest = Request(id=self.wallbox.id, power=self.minP, amp=self.config.minimalstromstaerke)
      if self.state == 'init':
         if data.get('llaktuell', id=self.wallbox.id) > 200:  # Gaining traction.
            self.state = 'charging'
            self.request = self.pv_request_charging
            self.set = self.set_charging
      elif self.lastrequest.power > 0:
         self.lastrequest.flags.add('ondelay')
      return self.lastrequest

   def pv_request_charging(self, data: "openWBValues") -> Request:
      if self.current_p - data.get('llaktuell', self.wallbox.id) > 200 * self.wallbox.phasen:
         self.blockcount += 1
      else:
         self.blockcount = 0
      blocked = self.blockcount >= 10
      if data.uberschuss <= self.minP:
         # TODO: Shut-off delay
         self.lastrequest = Request(id=self.wallbox.id, power=self.minP, amp=self.config.minimalstromstaerke)
      elif blocked and data.get('llaktuell', self.wallbox.id) < data.uberschuss:
         # Beschränke Anforderung auf aktuelle Ladeleistung
         amp = 1 + data.get('llaktuell', self.wallbox.id) // (230 * self.wallbox.phasen)
         self.lastrequest = Request(id=self.wallbox.id, power=amp*230*self.wallbox.phasen, amp=amp,
                                    flags=set(['blocked']))
      elif data.uberschuss >= self.maxP:
         self.lastrequest = Request(id=self.wallbox.id, power=self.maxP, amp=self.config.maximalstromstaerke)
      else:
         amp = data.uberschuss // (230 * self.wallbox.phasen)
         self.lastrequest = Request(id=self.wallbox.id, power=data.uberschuss, amp=amp)
      return self.lastrequest
   

   def set_idle(self, power: int) -> None:
      """set function of PV/idle and PV/init mode"""
      if power == 0 or power < self.lastrequest.power:  # Keine Anforderung, oder Anforderung abgelehnt
         self.oncount = 0
         self.blockcount = 0
         self.state = 'idle'
      else:
         self.oncount += 1
         if self.oncount >= self.config.einschaltverzoegerung:
            self.state = 'init'
            self.current_i = self.lastrequest.amp
            self.wallbox.set(self.current_i)

   def set_charging(self, power: int) -> None:
      """Set the given power"""
      self.current_p = power
      self.current_i = power2amp(power, self.wallbox.phasen)
      self.wallbox.set(self.current_i)

