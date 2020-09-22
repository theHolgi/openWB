from typing import Union
from collections import namedtuple

core = None  # The OpenWBcore singleton

def getCore():
   return core

def setCore(o):
   global core
   core = o

class Event:
   """Abstract class for an event"""
   pass

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

   def setup(self, config):
      """Setup the module (another possibility than overriding the constructor)"""
      pass

   def event(self, event: Event):
      """Process an event"""
      pass


class DataPackage(dict):
   """A package of Data points"""
   def __init__(self, source: Modul, payload: dict = {}):
      self.source = source
      self.update(payload)


class DataProvider(Modul):
   """Abstrakte Klasse eines Daten sendenden Moduls.
   Ein EVU- (Bezug-)Modul leitet sich direkt von DataProvider ab.
   """

   def trigger(self):
      """
      Trigger Datenerfassung. Als Bestätigung muss(!) ein Aufruf von self.core.sendData erfolgen.
      Ein Aufruf darf auch spontan ohne trigger erfolgen, z.B. als Folge eines IP-Broadcast
      """
      ...

class Ladepunkt(DataProvider):
   """
     Superklasse eines Ladepunktes.
   """
   multiinstance = True
   type = "lp"

   # Diese Properties hat ein Ladepunkt und werden von ihm selbst verändert:
   phasen = 1   # Init
   setP = 0  # Aktuell zugewiesene Leistung
   actP = 0  # Aktuell verwendete Leistung
   prio = 1  # Aktuelle Priorität

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
      """Fehrzeug lädt"""
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


# Properties eines Ladepunktes:
# - phasen - Anzahl erkannter benutzter Phasen
# Ein Ladepunkt muss folgende Datenpunkte senden:
# - llaktuell - Aktuelle Ladeleistung
# Optionale Datenpunkte:
# - plugstat - Stecker eingesteckt (1|0)
# - chargestat - Auto lädt (1|0)
# - llkwh - Gesamte Lademenge
# - llv1, llv2, llv3 - Spannung
# - lla1, lla2, lla3 - Strom


class PVModul(DataProvider):
   """Superklasse eines Wechselrichters.
   """
   multiinstance = True
   type = "wr"

# Ein Wechselrichter muss folgende Datenpunkte senden:
# - pvwatt: Momentanleistung (W)
# Optional:
# - pvkwh: Gesamte Einspeiseleistung (kWh)


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
