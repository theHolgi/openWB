import enum
from typing import Set, Optional
from . import power2amp, PowerProperties

class Priority(enum.IntEnum):
   low = 1
   medium = 2
   high = 3
   forced = 4

# dataclass would be great here, but requires Python 3.7
class RequestPoint:
   def __init__(self, key: str, value: int, priority: Optional[Priority] = None):
      self.key = key
      self.value = value
      self.priority = priority

   def __str__(self):
      return str(self.value)

class Request(dict):
   """
   Ein Request bildet die Möglichkeiten eines Ladepunktes ab, seine Leistung zu verändern.
   - min+P Mindest Leistungsinkrement
   - max+P Maximum Listungsinkrement
   - min-P Mindest Leistungsdekrement
   - max-P Maximum Leistungsdekrement
   jeder dieser Schlüssel hat einen Wert und eine Priorität.
   """
   def __init__(self, id: int, prio: int = 1, flags: Set[str] = None):
      self.id = id
      self.defaultprio = prio
      self.flags = set() if flags is None else flags  # can't do this in function default, as this will return the same single object for every usage.

   def __iadd__(self, point: RequestPoint) -> "Request":
      if point.priority is None:
         point.priority = self.defaultprio
      point.owner = self.id
      self[point.key] = point
      return self


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
   mode = "pv"

   def __init__(self, wallbox: "Ladepunkt"):
      self.wallbox = wallbox
      self.oncount = 0
      self.offcount = 0
      self.blockcount = 0
      self.state = 'idle'
      self.config = self.wallbox.core.config

   def request(self) -> Request:
      props = self.wallbox.powerproperties()
      request = Request(self.wallbox.id, prio=self.wallbox.prio)
      if self.wallbox.charging:
         request.flags.add('on')
         if self.wallbox.actP - props.inc >= props.minP:  # Verringerung noch möglich
            request += RequestPoint('min-P', props.inc)
            request += RequestPoint('max-P', self.wallbox.actP - props.minP)
         else:  # Nein, nur ganz ausschalten
            request.flags.add('min')
            request += RequestPoint('min-P', props.minP)
            request += RequestPoint('max-P', props.minP)
         if self.wallbox.actP + props.inc <= props.maxP:  # Erhöhung noch möglich
            request += RequestPoint('min+P', props.inc)
            request += RequestPoint('max+P', props.maxP - self.wallbox.actP)
         else:
            request.flags.add('max')  # Nicht wirklich benötigt
      else:
         request.flags.add('off')
         request += RequestPoint('min+P', props.minP)
         request += RequestPoint('max+P', props.maxP)
      return request


   ##################### old code ########################
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

class Regelgruppe():
   """
   Eine Regelungsgruppe, charakterisiert durch eine Regelungsstrategie:
   - "pv" - Überschuss regler
   - "peak" - Peak shaving
   - "sofort" - Sofortladen
   """
   def __init__(self, mode:str):
      self.mode = mode
      self.regler = []
      self.wallboxes = set()
      self.hysterese = 600
      if self.mode == 'pv':
         self.leistungserhoehung = lambda i: i>800
         self.leistungssenkung   = lambda i: i<200
      elif self.mode == 'peal':
         self.leistungserhoehung = lambda i: i>6500
         self.leistungssenkung   = lambda i: i<6000

   def leistungserhoehung(self, uberschuss: int) -> bool:
      """Ermittle ob """
   def add(self, ladepunkt: "Ladepunkt") -> None:
      self.regler.append(Regler(ladepunkt))
      self.wallboxes.add(ladepunkt)

   def controlcycle(self, data) -> None:
      requests = [lp.request() for lp in self.regler]
      if self.leistungserhoehung(data.uberschuss):
         ...
      elif self.leistungssenkung(data.uberschuss):
         ...
      else:
         ...



