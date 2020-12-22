from numbers import Number
from typing import Any, Union, Optional
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
import logging


class EventType(Enum):
   configupdate = 1  # Konfig-Änderung. info: config-Item    payload: neuer Wert
   resetEnergy = 2   # Ladepunkt Reset. info: Ladepunkt-ID   payload: None
   resetDaily = 3    # Reset daily-Werte.

@dataclass
class Event:
   type: EventType
   info: Any = None
   payload: Any = None


class CoreSingleton:   # This can not be stored in openWbCore because of circular reference.
   pass

def getCore():
   return CoreSingleton.core

def setCore(o):
   print("Setting Core to " + o.__repr__())
   CoreSingleton.core = o

PowerProperties = namedtuple('PowerProperties', 'minP maxP inc')

# Properties that every Modul has:
# name - Its name, built as CLASSNAME or CLASSNAME_<id> (when multiple instances)
# configprefix - Prefix for configuration
#              i.e. "bezugmodul1" für Bezugmodul Instanz 1
# id   - The ID (starting from 1) when multiple instances are possible
# core - the core class
# core.config - configuration
# core.data   - Data


class Modul(object):
   """
   Abstrakte Klasse für ein Modul.
   Konkrete Klassen dürften sich in erster Linie nicht hiervon, sondern von DataProvider ableiten.
   """

   def __init__(self, instance_id: int):
      name = self.__class__.__name__
      if hasattr(self.__class__, 'multiinstance') and self.__class__.multiinstance:
         self.id = instance_id
         name += '_' + str(instance_id)
      self.name = name
      self.configprefix = None  # Provided during setup
      self.core = getCore()
      self.offsets = {}   # Place for storing offsets for daily data

   def setup(self, config):
      """Setup the module (another possibility than overriding the constructor)"""
      pass

   def event(self, event: Event):
      """Process an event"""
      pass

   def reset_offset(self, prefix: str, name: str) -> None:
      """Resets the offset data"""
      if name in self.offsets:
         self.offsets[f'{prefix}_{name}'] = self.offsets[name]

   def offsetted(self, prefix, name, value) -> Optional[Number]:
      """Return offsetted value <value> with the name <name>"""
      self.offsets[name] = value
      offsetname = f'{prefix}_{name}'
      return value - self.offsets[offsetname] if offsetname in self.offsets else None


class DataPackage(dict):
   """A package of Data points"""
   def __init__(self, source: Modul, payload: dict = {}):
      self.source = source
      self.update(payload)


class DataProvider(Modul):
   """
   Abstrakte Klasse eines Daten sendenden Moduls.
   """

   def trigger(self):
      """
      Trigger Datenerfassung. Als Bestätigung muss(!) ein Aufruf von self.core.sendData erfolgen.
      Üblicherweise durch Aufruf von "send" einer abgeleiteten Klasse.
      Ein Aufruf darf auch spontan ohne trigger erfolgen, z.B. als Folge eines IP-Broadcast
      """
      ...


class EVUModul(DataProvider):
   """
   Abstrakt Klasse einer EVU-Messung.
   Ein EVU-Modul sendet folgende Datenpunkte:
   MUSS:
   - wattbezug - [W] Leistung am EVU-Übergabepunkt (>0: Bezug)
   KANN:
   - evuv1 ... evuv3 - [V] Spannung
   - evua1 ... evua3 - [A] Strom
   - evupf1 ... evupf3 - [%] Leistungsfaktor
   - bezugw1 ... bezugw3 - [W] Leistung an Phase n
   - evuhz           - [Hz] Netzfrequenz
   - einspeisungkwh  - [kWh] Gesamte eingespeiste Energie
   - bezugkwh        - [kWh] Gesamte bezogene Energie
   """

   def send(self, data) -> None:
      if 'bezugkwh' in data:
         self.offsets['in'] = data['bezugkwh']
         data['daily_bezugkwh'] = self.offsetted('daily', 'in', data['bezugkwh'])
      if 'einspeisungkwh' in data:
         data['daily_einspeisungkwh'] = self.offsetted('daily', 'out', data['einspeisungkwh'])

      self.core.sendData(DataPackage(self, data))

   def event(self, event: Event):
      if event.type == EventType.resetDaily:
         self.reset_offset('daily', 'in')
         self.reset_offset('daily', 'out')


class Speichermodul(DataProvider):
   """
   Abstrakte Klasse eines Speichers.
   Ein Speichermodul sendet folgende Datenpunkte:
   MUSS:
   - speicherleistung - [W] Ladeleistung (>0: Laden)
   SOLLTE:
   - speichersoc      - [%] State of charge
   KANN:
   - speicherikwh     - [kWh] gesamte Ladeleistung
   - speicherekwh     - [kWh] gesamte Entladeleistung
   """

   def setup(self) -> None:
      pass

   def send(self, data: dict) -> None:
      if "speicherikwh" in data and self.offsets.get('off_in'):
         data["daily_sikwh"] = self.offsetted('daily', 'in', data['speicherikwh'])
      if "speicherekwh" in data and self.offsets.get('off_out'):
         data["daily_sekwh"] = self.offsetted('daily', 'out', data['speicherekwh'])
      self.core.sendData(DataPackage(self, data))

   def event(self, event: Event):
      if event.type == EventType.resetDaily:
         self.reset_offset('daily', 'in')
         self.reset_offset('daily', 'out')

class Ladepunkt(DataProvider):
   """
     Superklasse eines Ladepunktes.
     Ein Ladepunkt sendet folgende Datenpunkte:
     MUSS:
     - llaktuell - Aktuelle Ladeleistung [W]
     KANN:
     - plugstat - Stecker eingesteckt [bool]
     - chargestat - Auto lädt wirklich [bool]
     - ladestatus - Auto soll laden [bool]
     - llkwh - Gesamte Lademenge [kWh]
     - llv1, llv2, llv3    - Spannung [V]
     - lla1, lla2, lla3    - Strom    [A]
     - llpf1, llpf2, llpf3 - Leistungsfaktor [%]
   """
   multiinstance = True
   type = "lp"

   # Diese Properties hat ein Ladepunkt und werden von ihm selbst verändert:
   phasen = 1 # Anzahl Phasen
   setP = 0  # Aktuell zugewiesene Leistung
   actP = 0  # Aktuell verwendete Leistung
   prio = 1  # Aktuelle Priorität

   def setup(self) -> None:
      self.plugged = False
      self.charging = False
      self.logger = logging.getLogger(self.__class__.__name__)

   def powerproperties(self) -> PowerProperties:
      """Liefert Möglichkeiten/Wünsche der Leistungsanpassung"""
      ...

   def set(self, power: int) -> None:
      """Setze zugewiesene Leistung"""
      self.setP = power
      ...

   def zaehle_phasen(self) -> None:
      if self.is_charging:
         phasen = 0
         for p in range(1, 4):
            if self.core.data.get('lla%i' % p, self.id) > 4:
               phasen += 1
         if phasen != 0:
            self.phasen = phasen

   @property
   def is_charging(self) -> bool:
      """Fehrzeug lädt tatsächlich"""
      return self.actP > 300

   @property
   def is_blocked(self) -> bool:
      """Fahrzeug folgt dem Sollstrom nicht"""
      return self.core.data.get('lla1', self.id) <= self.core.data.get('llsoll', self.id) - 1

   @property
   def minP(self) -> int:
      """Minimalleistung"""
      return self.core.config.minimalstromstaerke * self.phasen * 230

   @property
   def maxP(self) -> int:
      """Maximalleistung"""
      return self.core.config.maximalstromstaerke * self.phasen * 230

   def send(self, data: dict) -> None:
      if "plugstat" not in data:
         data["plugstat"] = not self.is_blocked
      if "chargestat" not in data:
         data["chargestat"] = self.is_charging
      if "lpphasen" not in data:
         data['lpphasen'] = self.phasen
      if "llkwh" not in data:
         data['llkwh'] = 0

      # Handle Ladung seit Plug / Ladung seit Chargstart
      plugged = data['plugstat']
      charging = data['chargestat']
      chargedkwh = data['llkwh']
      data['pluggedladungbishergeladen'] = self.offsetted('plugin', 'kwh', chargedkwh) if plugged else 0
      data['aktgeladen'] = self.offsetted('charge', 'kwh', chargedkwh)
      if plugged and not self.plugged:
         self.reset_offset('plugged', 'kwh')
         self.logger.info('Plugged in at %i kwh' % chargedkwh)
      if charging and not self.charging:
         self.reset_offset('charge', 'kwh')
         self.logger.info('Start charging at %i kwh' % chargedkwh)
         self.setP = self.actP  # Initialisiere setP falls externer Start
      self.plugged = plugged
      self.charging = charging
      self.core.sendData(DataPackage(self, data))

   def event(self, event: Event):
      if event.type == EventType.resetEnergy and event.info == self.id:
         # Reset invoked from UI
         self.reset_offset('charge', 'kwh')


class PVModul(DataProvider):
   """
   Abstrakte Klasse eines Wechselrichters.
   Ein Wechselrichter sendet folgende Datenpunkte:
   MUSS:
   - pvwatt - [W] Momentanleistung
   KANN:
   - pvkwh  - [kWh] gesamte Erzeugungsleistung
   """
   multiinstance = True
   type = "wr"

   def send(self, data: dict) -> None:
      if "pvkwh" in data:
         data['daily_pvkwh'] = self.offsetted('daily', 'kwh', data['pvkwh'])

      self.core.sendData(DataPackage(self, data))

   def event(self, event: Event):
      if event.type == EventType.resetDaily:
         self.reset_offset('daily', 'kwh')

class Displaymodul(Modul):
   """Superklasse eines Displaymoduls"""
   multiinstance = True
   type = "display"

# Ein Displaymodul ruft nicht "sendData" auf.
# Displaymodule werden nach dem Einlesen der Eingänge und der Berechnung abgeleiteter Daten aufgerufen.

def amp2amp(amp: Union[float, int]) -> int:
   """Limitiere Ampere auf min/max und runde ab auf Ganze"""
   config = getCore().config
   if amp < 1:
      return 0
   elif amp < config.minimalstromstaerke:
      amp = config.minimalstromstaerke
   elif amp > config.maximalstromstaerke:
      amp = config.maximalstromstaerke
   return int(amp)

def power2amp(power:int, phasen: int) -> int:
   """Konvertiere Leistung zu (ganzen) Ampere"""
   if power < 100:
      return 0
   else:
      return amp2amp(power/phasen/230)

def amp2power(amp: int, phasen: int) -> int:
   """Konvertiere Strom zu Leistung"""
   return amp * 230 * phasen
