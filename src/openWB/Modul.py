from abc import abstractmethod

from datetime import datetime

import importlib

from openWB import DataPackage
from openWB.openWBlib import RamdiskValues, OpenWBconfig
from typing import Optional, Union, Callable

import logging
from threading import Thread, Event
from numbers import Number
from collections import namedtuple
from openWB.openWBlib import openWBValues
from openWB.Event import *


PowerProperties = namedtuple('PowerProperties', 'minP maxP inc')

# Properties that every Modul has:
# name - Its name, built as CLASSNAME or CLASSNAME_<id> (when multiple instances)
# configprefix - Prefix for configuration
#              i.e. "bezugmodul1" für Bezugmodul Instanz 1
# id   - The ID (starting from 1) when multiple instances are possible
# core - the core class
# core.config - configuration
# core.data   - Data


class Modul(Thread):
   """
   Abstrakte Klasse für ein Modul.
   Konkrete Klassen dürften sich in erster Linie nicht hiervon, sondern von DataProvider ableiten.
   """

   def __init__(self, instance_id: int):
      super().__init__(daemon=True)
      name = self.__class__.__name__
      self.trigger = Event()    # A trigger to start the module
      self.finished = Event()   # A trigger to signal that the module has run
      self.trigger.clear()
      self.finished.clear()
      if hasattr(self.__class__, 'multiinstance') and self.__class__.multiinstance:
         self.id = instance_id
         name += '_' + str(instance_id)
      self.name = name
      self.logger = logging.getLogger(self.name)
      self.configprefix = None  # Provided during setup
      self.offsets = {}   # Place for storing offsets for daily data

   def setup(self, config):
      """Setup the module (another possibility than overriding the constructor)"""
      pass

   def run(self):
      """Thread Main function. Wartet auf das Trigger-Event und führt jeweils eine Loop aus."""
      while True:
         self.trigger.wait()
         self.trigger.clear()
         self.loop()

   def loop(self):
      """Modul Main function. Führt das Modul 1x aus."""
      ...

   def event(self, event: OpenWBEvent):
      """Process an event"""
      pass

   def reset_offset(self, prefix: str, name: str) -> None:
      """Resets the offset data"""
      if name in self.offsets:
         offsetname = f'{prefix}_{name}'
         self.offsets[offsetname] = self.offsets[name]
         ramdisk = RamdiskValues()
         today = datetime.today()
         ramdisk[f'{self.name}_{offsetname}'] = self.offsets[name]
         # ramdisk[f'{today.strftime("%D")}.{self.name}_{offsetname}'] = self.offsets[name]
         self.logger.info(f'Setting {prefix} offset {name} to {self.offsets[name]}')

   def offsetted(self, prefix, name, value) -> Optional[Number]:
      """Return offsetted value <value> with the name <name>"""
      self.offsets[name] = value
      offsetname = f'{prefix}_{name}'
      if offsetname in self.offsets:
         return value - self.offsets[offsetname]
      else:
         ramdisk = RamdiskValues()
         offset = ramdisk[f'{self.name}_{offsetname}']
         if offset is not None:
            self.offsets[offsetname] = offset
         else:
            self.logger.info(f'Start-up initialize {prefix} offset {name} to {value}')
            ramdisk[f'{self.name}_{offsetname}'] = value
         return 0

class DataProvider(Modul):
   """
   Abstrakte Klasse eines Daten sendenden Moduls.
   """

   def loop(self):
      """
      Trigger Datenerfassung. Als Bestätigung muss(!) ein Aufruf von OpenWBCore().sendData erfolgen.
      Üblicherweise durch Aufruf von "send" einer abgeleiteten Klasse.
      Ein sendData() Aufruf darf auch spontan ohne trigger erfolgen, z.B. als Folge eines IP-Broadcast
      """
      ...


class EVUModul(DataProvider):
   """
   Abstrakt Klasse einer EVU-Messung.
   """

   def send(self, data: dict) -> None:
      if 'kwhIn' in data:
         data['daily_kwhIn'] = self.offsetted('daily', 'in', data['kwhIn'])
         data['monthly_kwhIn'] = self.offsetted('monthly', 'in', data['kwhIn'])
      if 'kwhOut' in data:
         data['daily_kwhOut'] = self.offsetted('daily', 'out', data['kwhOut'])
         data['monthly_kwhOut'] = self.offsetted('monthly', 'out', data['kwhOut'])

      self.master.send(DataPackage(self, data))

   def event(self, event: OpenWBEvent):
      if event.type == EventType.resetDaily:
         self.reset_offset('daily', 'in')
         self.reset_offset('daily', 'out')
      if event.type == EventType.resetMonthly:
         self.reset_offset('monthly', 'in')
         self.reset_offset('monthly', 'out')


class Speichermodul(DataProvider):
   """
   Abstrakte Klasse eines Speichers.
   """
   multiinstance = True
   def setup(self, config) -> None:
      pass

   def send(self, data: dict) -> None:
      if "kwhIn" in data:
         data["dailykwhIn"]   = self.offsetted('daily',   'in', data['kwhIn'])
         data["monthlykwhIn"] = self.offsetted('monthly', 'in', data['kwhIn'])
      if "kwhOut" in data:
         data["dailykwhOut"]   = self.offsetted('daily',   'out', data['kwhOut'])
         data["monthlykwhOut"] = self.offsetted('monthly', 'out', data['kwhOut'])
      self.master.send(DataPackage(self, data))

   def event(self, event: OpenWBEvent):
      if event.type == EventType.resetDaily:
         self.reset_offset('daily', 'in')
      elif event.type == EventType.resetNoon:
         self.reset_offset('daily', 'out')
      elif event.type == EventType.resetMonthly:
         self.reset_offset('monthly', 'in')
         self.reset_offset('monthly', 'out')


class Ladepunkt(DataProvider):
   """
     Superklasse eines Ladepunktes.
     Ein Ladepunkt sendet folgende Datenpunkte:
     MUSS:
     - W - Aktuelle Ladeleistung [W]
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

   def setup(self, config) -> None:
      self.plugged = False
      self.charging = False
      self.offsets['chargedW'] = 0   # Kumulative Lademenge
      self.configprefix = f"lpmodul{self.id}"

   @abstractmethod
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
            if openWBValues().get('lp/%i/APhase%i' % (self.id, p)) > 4:
               phasen += 1
         if phasen != 0:
            self.phasen = phasen

   @property
   def is_charging(self) -> bool:
      """Fahrzeug lädt tatsächlich"""
      return self.actP > 300

   @property
   def is_blocked(self) -> bool:
      """Fahrzeug folgt dem Sollstrom nicht"""
      data = openWBValues()
      return data.get('lp/%i/APhase1' % self.id) <= data.get('lp/%i/AConfigured' % self.id) - 1

   @property
   def minP(self) -> int:
      """Minimalleistung"""
      return OpenWBconfig().get('minimalstromstaerke') * self.phasen * 230

   @property
   def maxP(self) -> int:
      """Maximalleistung"""
      return OpenWBconfig().get('maximalstromstaerke') * self.phasen * 230

   def send(self, data: dict) -> None:
      if 'W' in data:   # Only for normal data packages
         if "boolPlugStat" not in data:
            data["boolPlugStat"] = not self.is_blocked
         if "boolChargeStat" not in data:
            data["boolChargeStat"] = self.is_charging
         if "countPhasesInUse" not in data:
            data['countPhasesInUse'] = self.phasen
         if "kwh" not in data:
            data['kwh'] = 0

         # Handle Ladung seit Plug / Ladung seit Chargstart
         plugged = data['boolPlugStat']
         charging = data['boolChargeStat']
         chargedkwh = data['kwh']
         self.offsets['chargedW'] += data['W']
         data['kWhChargedSincePlugged'] = self.offsetted('plugged', 'kwh', chargedkwh) if plugged else 0
         data['kWhActualCharged'] = self.offsets['chargedW'] / 720000  # Einheit: W*Zykluszeit => /(3600/t)/1000
         #  self.offsetted('charge', 'kwh', chargedkwh)
         if plugged and not self.plugged:
            self.reset_offset('plugged', 'kwh')
            self.logger.info(f'LP{self.id} plugged in at {chargedkwh} kwh')
         if charging and not self.charging:
            self.reset_offset('charge', 'kwh')
            self.offsets['chargeW'] = 0
            self.logger.info('Start charging at %i kwh' % chargedkwh)
            #  self.setP = self.actP  # Initialisiere setP falls externer Start
         self.plugged = plugged
         self.charging = charging
         data["DailyKwh"] = self.offsetted('daily', 'kwh', data['kwh'])

      self.master.send(DataPackage(self, data))

   def event(self, event: OpenWBEvent):
      if event.type == EventType.resetEnergy and event.info == self.id:
         # Reset invoked from UI
         # self.reset_offset('charge', 'kwh')
         self.offsets['chargedW'] = 0
      if event.type == EventType.resetDaily:
         self.reset_offset('daily', 'kwh')


class PVModul(DataProvider):
   """
   Abstrakte Klasse eines Wechselrichters.
   """
   multiinstance = True
   type = "wr"

   def send(self, data: dict) -> None:
      if "kwh" in data:
         data['DailyKwh']  = self.offsetted('daily', 'kwh', data['kwh'])
         data['MonthlyKwh'] = self.offsetted('monthly', 'kwh', data['kwh'])
      self.master.send(DataPackage(self, data))

   def event(self, event: OpenWBEvent):
      if event.type == EventType.resetDaily:
         self.reset_offset('daily', 'kwh')
      if event.type == EventType.resetMonthly:
         self.reset_offset('monthly', 'kwh')


class Displaymodul(Modul):
   """Superklasse eines Displaymoduls"""
   multiinstance = True
   type = "display"

# Ein Displaymodul ruft nicht "sendData" auf.
# Displaymodule werden nach dem Einlesen der Eingänge und der Berechnung abgeleiteter Daten aufgerufen.


def amp2amp(amp: Union[float, int]) -> int:
   """Limitiere Ampere auf min/max und runde ab auf Ganze"""
   config = OpenWBconfig()
   if amp < 1:
      return 0
   elif amp < config.get('minimalstromstaerke'):
      amp = config.get('minimalstromstaerke')
   elif amp > config.get('maximalstromstaerke'):
      amp = config.get('maximalstromstaerke')
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

def for_all_modules(prefix, callback: Callable[[Modul], None]):
   """Suche alle Module mit <prefix> und rufe für die erzeugte <Modul>-Instanz den callback auf"""
   instance = 1
   while True:
      modulename = OpenWBconfig()[prefix + 'modul' + str(instance)]
      if modulename is None:
         break
      module = importlib.import_module(f'modules.{prefix}_{modulename}')
      o = module.getClass()(instance)
      callback(o)
      print("Created module: " + o.name)
      instance += 1

def for_module(prefix, callback: Callable[[Modul], None]):
   """Suche das Modul mit <prefix> und rufe für die erzeugte <Modul>-Instanz den callback auf"""
   modulename = OpenWBconfig()[prefix + 'modul']
   if modulename is not None:
      module = importlib.import_module(f'modules.{prefix}_{modulename}')
      callback(module.getClass()(1))
