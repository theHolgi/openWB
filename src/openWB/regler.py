import enum
from datetime import datetime
from math import ceil

from openWB import DataPackage
from openWB.Modul import amp2power
from openWB.Scheduling import Scheduler
from openWB.openWBlib import OpenWBconfig, openWBValues
from openWB.Event import OpenWBEvent, EventType
from typing import Set, Optional
from itertools import groupby
from dataclasses import dataclass
import logging

from plugins.awattar import Awattar
from utils import tomorrow_at_6


class Priority(enum.IntEnum):
   low = 1
   medium = 2
   high = 3
   forced = 4

class ChargeLimit(enum.IntEnum):
   unlimited = 0
   bykWh = 1
   bysoc = 2


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
      return f"<Request {{{self.id}: " + " ".join(f"{key}={value}" for key, value in self.items()) + f" {self.flags}}}>"


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
   - "awattar" - Günstig laden
   """
   priority = 500   # Regelung hat eine mittlere Priorität

   def __init__(self, mode: str):
      self.mode = mode
      self.regler = dict()
      self.config = OpenWBconfig()
      self.data = openWBValues()
      self.hysterese = int(self.config.get('hysterese'))
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
         self.limit = int(self.config.get('offsetpv'))
      elif self.mode == 'peak':
         """
            Peak-Modus: Limit darf nicht überschritten werden.
            - P > Limit: erhöhe bis < Limit
            - P < Limit: reduziere solange < Limit
         """
         self.limit = int(self.config.get('offsetpvpeak'))
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

      elif self.mode == 'awattar':
         """
         Awattar-Lade-Modus:
         - Besorge Awattar-Preise
         - Bestimme Anzahl Stunden n, die für die gewünschte kWh-Menge benötigt werden
         - Bestimme die n Stunden, in denen der Preis am Günstigsten ist
         - setze Ladestrom auf lpmodul%i_sofortll, sofern aktuell eine dieser Stunden ist
         """
         self.limit = 1
         self.awattarmodul = Awattar()
         def get_delta(r: Request, deltaP: int) -> int:
            return 0
         self.get_increment = get_delta
         self.get_decrement = get_delta

   def add(self, ladepunkt: "Ladepunkt") -> None:
      """Füge Ladepunkt hinzu"""
      self.regler[ladepunkt.id] = Regler(ladepunkt)
      if self.mode == 'awattar':
         self.logger.info("Enable global Awattar")
         self.data.update(DataPackage(self.regler[ladepunkt.id], {'global/awattar/boolAwattarEnabled': 1}))

   def pop(self, id: int) -> "Ladepunkt":
      """Lösche Ladepunkt mit der ID <id>"""
      # TODO: Beibehaltung aktiver Lademodus
      wb = None
      if id in self.regler:
         wb = self.regler.pop(id).wallbox
      if len(self.regler) == 0:  # Leer
         if self.mode == 'awattar':
            self.data.update(DataPackage(self, {'global/awattar/boolAwattarEnabled': 0}))
      return wb

   def __repr__(self):
      return "<Regelgruppe " + str(list(self.regler.keys())) + ">"

   @property
   def isempty(self) -> bool:
      """
      Gebe an, ob diese Gruppe leer ist
      :return:
      """
      return len(self.regler) == 0

   def schieflast_nicht_erreicht(self, wallbox_id: int) -> bool:
      return self.regler[wallbox_id].wallbox.phasen == 3 or \
         self.data.get('lp/%i/AConfigured' % wallbox_id) < 20 or \
         self.data.get('evu/ASchieflast') < int(self.config.get('schieflastmaxa'))

   def loop(self) -> None:
      properties = [lp.get_props() for lp in self.regler.values()]
      arbitriert = dict([(id, 0) for id in self.regler.keys()])
      self.logger.debug(f"Reglergruppe {self.mode} LP Props: {properties!r}")
      uberschuss = self.data.get('global/uberschuss')
      for id, regler in self.regler.items():
         prefix = 'lp/%i/' % id
         limitierung = self.config.get('msmoduslp%i' % id)
         if self.mode != 'stop':
            if limitierung == ChargeLimit.bykWh and self.config.get('lademkwh%i' % id):  # Limitierung: kWh
               charged = self.data.get(prefix + 'kWhChargedSincePlugged', 0)
               if self.data.get(prefix + 'W') == 0:
                  restzeit = "---"
               else:
                  restzeit = int((self.config.get('lademkwh%i' % id) - charged)*1000*60 / self.data.get('lp/%i/W' % id))
               self.data.update(DataPackage(regler.wallbox, {prefix+'TimeRemaining': f"{restzeit} min"}))
               if self.config.get('lademkwh%i' % id) <= charged:
                  self.logger.info(f"Lademenge erreicht: LP{id} {self.config.get('lademkwh%i' % id)}kwh")
                  from openWB.OpenWBCore import OpenWBCore
                  OpenWBCore().setconfig(regler.wallbox.configprefix + '_mode', "stop")
                  Scheduler().signalEvent(OpenWBEvent(EventType.resetEnergy, id))
            elif limitierung == ChargeLimit.bysoc:  # Limitierung: SOC
               pass  # TODO
      if self.mode == 'sofort':
         for id, regler in self.regler.items():
            power = amp2power(self.config.get("lpmodul%i_sofortll" % id, 6), regler.wallbox.phasen)
            if regler.wallbox.setP != power:
               regler.wallbox.set(power)
      elif self.mode == 'awattar':
         package = DataPackage(self, {'global/awattar/ActualPriceForCharging': self.awattarmodul.getprice(datetime.now())})
         until = tomorrow_at_6()
         if self.awattarmodul.getprice(until) is None:  # Preise nicht verfügbar
            self.awattarmodul.refresh()
            chart = self.awattarmodul.get_pricechart()
            if chart is not None:
               package['global/awattar/pricelist'] = chart
         for id, regler in self.regler.items():
            required = self.config.get('lademkwh%i' % id, 0) - self.data.get('lp/%i/kWhActualCharged' % id, 0)
            power = amp2power(self.config.get("lpmodul%i_sofortll" % id, 6), regler.wallbox.phasen)
            # hard-code "Until" for 6:00 next day (if now is after 6:00)
            hours_to_charge = ceil(required * 1000.0 / power)
            activitychart = self.awattarmodul.cheapestchart(until, hours_to_charge)
            package["global/awattar/%i/charge" % id] = activitychart

            if required <= 0 or not self.awattarmodul.charge_now(hours_to_charge, until):
               power = 0
            if regler.wallbox.setP != power:
               regler.wallbox.set(power)
         self.data.update(package)

      elif self.mode == 'stop':
         for regler in self.regler.values():
            if regler.wallbox.setP != 0 or regler.wallbox.is_charging:
               self.logger.info(f"(LP {regler.wallbox.id}: {regler.wallbox.setP}W -> Reset")
               regler.wallbox.set(0)
      elif uberschuss > self.limit:  # Leistungserhöhung
         deltaP = uberschuss - self.limit
         # Erhöhe eingeschaltete LPs
         for r in sorted(filter(lambda r: 'min+P' in r and 'on' in r.flags, properties), key=lambda r: r['min+P'].priority):
            p = self.get_increment(r, deltaP)
            if p is not None and self.schieflast_nicht_erreicht(r.id):
               # Erhöhe bei Asymmetrie nur 3-phasen-Boxen
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
               if self.get_increment(r, budget) is not None and self.schieflast_nicht_erreicht(r.id):
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
