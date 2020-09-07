import enum
from typing import Set, Optional
from . import getCore
from itertools import groupby
from dataclasses import dataclass

class Priority(enum.IntEnum):
   low = 1
   medium = 2
   high = 3
   forced = 4

@dataclass
class RequestPoint:
   key: str
   value: int
   priority: Optional[Priority] = None

   def __str__(self):
      return str(self.value)


class Request(dict):
   """
   Ein Request bildet die Möglichkeiten eines Ladepunktes ab, seine Leistung zu verändern.
   - min+P Mindest Leistungsinkrement
   - max+P Maximum Leistungsinkrement
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
      self.request = self.req_idle

   @property
   def blocked(self) -> bool:
      return self.wallbox.is_blocked

   def get_props(self) -> Request:
      props = self.wallbox.powerproperties()
      request = Request(self.wallbox.id, prio=self.wallbox.prio)
      if self.wallbox.is_charging:
         request.flags.add('on')

         if self.wallbox.setP - props.inc >= props.minP:  # Verringerung noch möglich
            request += RequestPoint('min-P', props.inc)
            request += RequestPoint('max-P', self.wallbox.setP - props.minP)
         else:  # Nein, nur ganz ausschalten
            request.flags.add('min')
            # Wenn noch über Min, lasse Reduzierung noch zu
            if self.wallbox.setP > props.minP:
               request += RequestPoint('min-P', self.wallbox.setP - props.minP)
            else:
               request += RequestPoint('min-P', self.wallbox.setP)
            request += RequestPoint('max-P', self.wallbox.setP)
         if self.blocked:                 # Blockierter Ladepunkt bietet keine Leistungserhöhung an
            request.flags.add('blocked')  # Nicht wirklich benötigt
         elif self.wallbox.actP + props.inc <= props.maxP:  # Erhöhung noch möglich
            request += RequestPoint('min+P', props.inc)
            request += RequestPoint('max+P', props.maxP - self.wallbox.setP)
         else:
            request.flags.add('max')  # Nicht wirklich benötigt
      else:
         request.flags.add('off')
         if self.wallbox.setP < props.minP:   # Noch nicht eingeschaltet
            request += RequestPoint('min+P', props.minP - self.wallbox.setP)
            request += RequestPoint('max+P', props.maxP - self.wallbox.setP)
         else:   # Ladeende - versuche Leistung freizugeben
            request += RequestPoint('min-P', self.wallbox.setP)
            request += RequestPoint('max-P', self.wallbox.setP)

      return request

   def req_idle(self, increment: int) -> None:
      """set function of PV/idle and PV/init mode"""
      if increment == 0:  # Keine Anforderung
         self.oncount = 0
         self.state = 'idle'
      else:
         self.oncount += 1
         if self.oncount >= self.config.einschaltverzoegerung:
            self.state = 'init'
            self.oncount = 0
            self.request = self.req_charging
            power = self.wallbox.setP + increment
            self.wallbox.set(power)

   def req_charging(self, increment: int) -> None:
      """Set the given power"""
      power = self.wallbox.setP + increment
      self.wallbox.core.logger.info("WB %i requested %iW" % (self.wallbox.id, power))
      if power < 100:
         self.offcount += 1
         if self.offcount >= self.config.abschaltverzoegerung:
            self.state = 'idle'
            self.offcount = 0
            self.request = self.req_idle
            self.wallbox.set(power)
      else:
         self.offcount = 0
         self.wallbox.set(power)
         self.wallbox.zaehle_phasen()


class Regelgruppe():
   """
   Eine Regelungsgruppe, charakterisiert durch eine Regelungsstrategie:
   - "pv" - Überschuss regler
   - "peak" - Peak shaving
   - "sofort" - Sofortladen
   """
   def __init__(self, mode:str):
      self.mode = mode
      self.regler = dict()
      self.hysterese = getCore().config.hysterese

      if self.mode == 'pv':
         """
            PV-Modus: Limit darf nicht unterschritten werden.
            - P > Limit: iO, aber erhöhe solange > Limit
            - P < Limit: reduziere bis P>limit
         """
         def get_increment(r: Request, deltaP: int) -> Optional[int]:
            if r['min+P'].value < deltaP:  # Akzeptiert
               if r['max+P'].value < deltaP:  # Sogar Pmax
                  return r['max+P'].value
               else:  # Dann liegt deltaP dazwischen
                  return deltaP
         def get_decrement(r: Request, deltaP: int) -> Optional[int]:
            if deltaP <= 0:  # Kein Bedarf
               return None
            elif r['min-P'].value > deltaP:  # min+P reicht
               return r['min-P'].value
            elif r['max-P'].value < deltaP:  # Pmax reicht noch nicht
               return r['max-P'].value
            else:  # deltaP liegt zwischen beidem
               return deltaP

         self.get_increment = get_increment
         self.get_decrement = get_decrement
         self.limit = getCore().config.offsetpv
         self.hysterese = getCore().config.hysterese

      elif self.mode == 'peak':
         """
            Peak-Modus: Limit darf nicht überschritten werden.
            - P > Limit: erhöhe bis < Limit
            - P < Limit: reduziere solange < Limit
         """
         self.limit = getCore().config.offsetpvpeak
         def get_increment(r: Request, deltaP: int) -> Optional[int]:
            if deltaP <= 0:  # Kein Bedarf
               return None
            elif r['min+P'].value > deltaP:  # min+P reicht
               return r['min+P'].value
            elif r['max+P'].value < deltaP:  # Pmax reicht noch nicht
               return r['max+P'].value
            else:  # deltaP liegt zwischen beidem
               return deltaP
         def get_decrement(r: Request, deltaP: int) -> Optional[int]:
            if r['min-P'].value < deltaP:  # Akzeptiert
               if r['max-P'].value < deltaP:  # Sogar Pmax
                  return r['max-P'].value
               else:  # Dann liegt deltaP dazwischen
                  return deltaP
         self.get_increment = get_increment
         self.get_decrement = get_decrement


   def add(self, ladepunkt: "Ladepunkt") -> None:
      self.regler[ladepunkt.id] = Regler(ladepunkt)

   def controlcycle(self, data) -> None:
      properties = [lp.get_props() for lp in self.regler.values()]
      arbitriert = dict([(id, 0) for id in self.regler.keys()])
      if data.uberschuss > self.limit:  # Leistungserhöhung
         deltaP = data.uberschuss - self.limit
         # Erhöhe eingeschaltete LPs
         for r in sorted(filter(lambda r: 'min+P' in r and 'on' in r.flags, properties), key=lambda r: r['min+P'].priority):
            p = self.get_increment(r, deltaP)
            if p is not None:
               arbitriert[r.id] = p
               deltaP -= p
               if deltaP <= 0:
                  break
         # Schalte LPs mit höchster Prio ein
         candidates = unroll(groupby(filter(lambda r: 'min+P' in r and 'off' in r.flags, properties), key=lambda r: r['min+P'].priority))
         if candidates:
            highest_prio = max(candidates.keys())
            candidates = candidates[highest_prio]
            # Budget zum Einschalten: Erstmal der Überschuss
            budget = data.uberschuss - self.limit
            if self.mode == "pv":
               budget -= self.hysterese
            # Zusätzliches Budget kommt vom Regelpotential eingeschalteter LPs gleicher oder niedrigerer Prio
            budget += sum(r['max-P'].value for r in filter(lambda r: 'max-P' in r and 'min' not in r.flags and r['max-P'].priority <= highest_prio, properties))
            for r in candidates:
               if self.get_increment(r, budget) is not None:
                  arbitriert[r.id] = r['min+P'].value
                  budget -= r['min+P'].value
      elif data.uberschuss < self.limit:  # Leistungsreduktion
         deltaP = self.limit - data.uberschuss
         for r in sorted(filter(lambda r: 'min-P' in r and 'min' not in r.flags, properties), key=lambda r: r['min-P'].priority):
            p = self.get_decrement(r, deltaP)
            if p is not None:
               arbitriert[r.id] = -p
               deltaP -= p
               if deltaP <= 0:
                  break
         # Schalte LPs aus
         deltaP = self.limit - data.uberschuss
         if self.mode == "peak":
            deltaP -= self.hysterese
         for r in sorted(filter(lambda r: 'min' in r.flags, properties), key=lambda r: r['min-P'].priority):
            if self.get_decrement(r, deltaP) is not None:
               arbitriert[r.id] = -r['min-P'].value
               deltaP -= r['min-P'].value

      for ID, inc in arbitriert.items():
         self.regler[ID].request(inc)

def unroll(d) -> dict:
   """Unroll a grouped iterator, which is not ver useable as it is returned from itertools."""
   r = dict()
   for key, values in d:
      r[key] = list(values)
   return r