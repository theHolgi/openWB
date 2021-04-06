import enum
from openWB import DataPackage
from openWB.Modul import amp2power
from openWB.Scheduling import Scheduler
from openWB.openWBlib import OpenWBconfig, openWBValues
from typing import Set, Optional
from itertools import groupby
from dataclasses import dataclass
import logging


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
   def __init__(self, id: int, prio: int = 1, flags: Optional[Set[str]] = None):
      self.id = id
      self.defaultprio = prio
      self.flags = set() if flags is None else flags  # can't do this in function default, as this will return the same single object for every usage.

   def __iadd__(self, point: RequestPoint) -> "Request":
      if point.priority is None:
         point.priority = self.defaultprio
      point.owner = self.id
      self[point.key] = point
      return self

   def __repr__(self):
      return f"<Request>{{{self.id}: " + " ".join(f"{key}={value}" for key, value in self.items()) + f" {self.flags}}}"


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

   def __init__(self, wallbox: "Ladepunkt"):
      self.wallbox = wallbox
      self.oncount = 0
      self.offcount = 0
      self.blockcount = 0
      self.state = 'idle'
      self.config = OpenWBconfig()
      self.request = self.req_idle
      self.logger = logging.getLogger(self.__class__.__name__ + f'-{self.wallbox.id}')

   def __repr__(self):
      return f"<Regler #{self.wallbox.id}>"

   @property
   def blocked(self) -> bool:
      return self.wallbox.is_blocked

   def get_props(self) -> Request:
      props = self.wallbox.powerproperties()
      request = Request(self.wallbox.id, prio=self.wallbox.prio)
      debugstr = f'Wallbox setP: {self.wallbox.setP} minP: {props.minP}'
      if self.wallbox.is_charging:
         request.flags.add('on')
         debugstr += " (on)"
         if props.inc > 0 and self.wallbox.setP - props.inc >= props.minP:  # Verringerung noch möglich
            request += RequestPoint('min-P', props.inc)
            request += RequestPoint('max-P', self.wallbox.setP - props.minP)
         elif not self.config[self.wallbox.configprefix + '_alwayson']:  # Nein, nur ganz ausschalten
            request.flags.add('min')
            # Wenn noch über Min, lasse Reduzierung noch zu
            if self.wallbox.setP > props.minP:
               request += RequestPoint('min-P', self.wallbox.setP - props.minP)
            else:
               request += RequestPoint('min-P', self.wallbox.setP)
            request += RequestPoint('max-P', self.wallbox.setP)
         if self.blocked:                 # Blockierter Ladepunkt bietet keine Leistungserhöhung an
            request.flags.add('blocked')  # Nicht wirklich benötigt
            debugstr += " (blocked)"
         elif self.wallbox.actP + props.inc <= props.maxP:  # Erhöhung noch möglich
            request += RequestPoint('min+P', props.inc)
            request += RequestPoint('max+P', props.maxP - self.wallbox.setP)
         else:
            request.flags.add('max')  # Nicht wirklich benötigt
            debugstr += " (max)"
      else:
         request.flags.add('off')
         debugstr += " (off)"
         if self.wallbox.setP < props.minP:   # Noch nicht eingeschaltet
            request += RequestPoint('min+P', props.minP - self.wallbox.setP)
            request += RequestPoint('max+P', props.maxP - self.wallbox.setP)
         else:   # Ladeende - versuche Leistung freizugeben
            request += RequestPoint('min-P', self.wallbox.setP)
            request += RequestPoint('max-P', self.wallbox.setP)

      self.logger.debug(debugstr)
      return request

   def req_idle(self, increment: int) -> None:
      """set function of PV/idle and PV/init mode"""
      # WB soll an sein
      if self.config[self.wallbox.configprefix + '_alwayson']:
         self.wallbox.set(self.wallbox.powerproperties().minP)
         self.request = self.req_charging
      elif self.oncount >= self.config.get('einschaltverzoegerung',10):
         self.state = 'init'
         self.oncount = 0
         self.request = self.req_charging
         power = self.wallbox.setP + increment
         self.wallbox.set(power)
      elif increment == 0:  # Keine Anforderung
         self.oncount = 0
         self.state = 'idle'
      elif increment < 0:   # Negative Anforderung ist Reduzierung von Restleistung
         self.oncount = 0
         self.wallbox.set(self.wallbox.setP + increment)
      else:
         self.oncount += 1

   def req_charging(self, increment: int) -> None:
      """Set the given power"""
      power = self.wallbox.setP + increment
      self.logger.info("WB %i requested %iW" % (self.wallbox.id, power))
      if power < 100:
         self.offcount += 1
         if self.offcount >= self.config.get('abschaltverzoegerung', 20):
            self.state = 'idle'
            self.offcount = 0
            self.request = self.req_idle
            self.wallbox.set(power)
      else:
         self.offcount = 0
         self.wallbox.set(power)
         self.wallbox.zaehle_phasen()


class Regelgruppe:
   """
   Eine Regelungsgruppe, charakterisiert durch eine Regelungsstrategie:
   - "pv" - Überschuss regler
   - "peak" - Peak shaving
   - "sofort" - Sofortladen
   """
   priority = 500   # Regelung hat eine mittlere Priorität

   def __init__(self, mode:str):
      self.mode = mode
      self.regler = dict()
      self.config = OpenWBconfig()
      self.hysterese = self.config.get('hysterese')
      self.logger = logging.getLogger(self.__class__.__name__ + "_" + mode)
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
         self.limit = self.config.get('offsetpv')
         self.hysterese = self.config.get('hysterese')

      elif self.mode == 'peak':
         """
            Peak-Modus: Limit darf nicht überschritten werden.
            - P > Limit: erhöhe bis < Limit
            - P < Limit: reduziere solange < Limit
         """
         self.limit = self.config.get('offsetpvpeak')
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

      elif self.mode == 'sofort':
         """
         Sofort-Lade-Modus:
         Keine Regelung,
         - setze auf Ladestrom lpmodul%i_sofortll (A)
         - bis zu kwH: lademkwh%i
         """
         def get_delta(r: Request, deltaP: int) -> int:
            return 0
         self.limit = 1  # dummy
         self.get_increment = get_delta
         self.get_decrement = get_delta

   def destroy(self) -> None:
      Scheduler().unregisterTimer(self.loop)
      del self

   def add(self, ladepunkt: "Ladepunkt") -> None:
      """Füge Ladepunkt hinzu"""
      self.regler[ladepunkt.id] = Regler(ladepunkt)

   def pop(self, id: int) -> "Ladepunkt":
      """Lösche Ladepunkt mit der ID <id>"""
      # TODO: Beibehaltung aktiver Lademodus
      if id in self.regler:
         return self.regler.pop(id).wallbox

   @property
   def isempty(self) -> bool:
      """
      Gebe an, ob diese Gruppe leer ist
      :return:
      """
      return len(self.regler) == 0

   def loop(self) -> None:
      properties = [lp.get_props() for lp in self.regler.values()]
      arbitriert = dict([(id, 0) for id in self.regler.keys()])
      self.logger.debug(f"Reglergruppe {self.mode} LP Props: {properties!r}")
      data = openWBValues()
      uberschuss = data.get('global/uberschuss')
      for id, regler in self.regler.items():
         prefix = 'lp/%i/' % id
         limitierung = self.config.get('msmoduslp%i' % id)
         self.logger.debug(f"Limitierung LP{id}: {limitierung}")
         if limitierung == 1:  # Limitierung: kWh
            if data.get(prefix + 'W') == 0:
               restzeit = "---"
            else:
               restzeit = int((self.config.get('lademkwh%i' % id) - data.get(prefix + 'kWhActualCharged'))*1000*60 / data.get('lp/%i/W' % id))
            print(f"LP{id} Ziel: {self.config.get('lademkwh%i' % id)} Akt: {data.get(prefix + 'kWhActualCharged')} Leistung: {data.get(prefix + 'W')} Restzeit: {restzeit}")
            data.update(DataPackage(regler.wallbox, {prefix+'TimeRemaining': f"{restzeit} min"}))
            if self.config.get('lademkwh%i' % id) <= data.get(prefix + 'kWhActualCharged'):
               self.logger.info(f"Lademenge erreicht: LP{id} {self.config.get('lademkwh%i' % id)}kwh")
               from openWB.OpenWBCore import OpenWBCore
               OpenWBCore().setconfig(regler.wallbox.configprefix + '_mode', "standby")
               Scheduling().signalEvent(OpenWBEvent(EventType.resetEnergy, id))
         elif limitierung == 2:  # Limitierung: SOC
            pass  # TODO
      if self.mode == 'sofort':
         for id, regler in self.regler.items():
            power = amp2power(self.config.get("lpmodul%i_sofortll" % id, 6), regler.wallbox.phasen)
            if regler.wallbox.setP != power:
               regler.wallbox.set(power)

      elif self.mode in ['stop', 'standby']:
         for regler in self.regler.values():
            if regler.wallbox.setP != 0:
               self.logger.info(f"(LP {regler.wallbox.id}: {regler.wallbox.setP}W -> Reset")
               regler.wallbox.set(0)
      elif uberschuss > self.limit:  # Leistungserhöhung
         deltaP = uberschuss - self.limit
         # Erhöhe eingeschaltete LPs
         for r in sorted(filter(lambda r: 'min+P' in r and 'on' in r.flags, properties), key=lambda r: r['min+P'].priority):
            p = self.get_increment(r, deltaP)
            if p is not None:
               self.logger.debug(f"LP {r.id} bekommt +{p}W von {deltaP}W")
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
            budget = uberschuss - self.limit
            if self.mode == "pv":
               budget -= self.hysterese
            # Zusätzliches Budget kommt vom Regelpotential eingeschalteter LPs gleicher oder niedrigerer Prio
            budget += sum(r['max-P'].value for r in filter(lambda r: 'max-P' in r and 'min' not in r.flags and r['max-P'].priority <= highest_prio, properties))
            for r in candidates:
               if self.get_increment(r, budget) is not None:
                  self.logger.info(f"Budget: {budget}; LP {r.id} min+P {r['min+P'].value} passt noch")  
                  arbitriert[r.id] = r['min+P'].value
                  budget -= r['min+P'].value
      elif uberschuss < self.limit:  # Leistungsreduktion
         deltaP = self.limit - uberschuss
         for r in sorted(filter(lambda r: 'min-P' in r and 'min' not in r.flags, properties), key=lambda r: r['min-P'].priority):
            p = self.get_decrement(r, deltaP)
            if p is not None:
               self.logger.debug(f"LP {r.id} Reduzierung -{p}W von -{deltaP}W")
               arbitriert[r.id] = -p
               deltaP -= p
               if deltaP <= 0:
                  break
         # Schalte LPs aus
         deltaP = self.limit - uberschuss
         if self.mode == "peak":
            deltaP -= self.hysterese
         for r in sorted(filter(lambda r: 'min' in r.flags, properties), key=lambda r: r['min-P'].priority):
            if self.get_decrement(r, deltaP) is not None:
               self.logger.info(f"Abschalten LP {r.id} soll {r['min-P'].value}W freigeben.")
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