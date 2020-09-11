from . import Modul, DataPackage, setCore, getCore
from .openWBlib import *
from .mqttpub import Mqttpublisher
from .regler import *
from dataclasses import dataclass
from enum import Enum
import logging
import time
import re

logging.basicConfig(level=logging.DEBUG)

class EventType(Enum):
   configupdate = 1

@dataclass
class Event:
   type: EventType
   info: str
   payload: str


class OpenWBCore:
   """openWB core and scheduler"""
   def __init__(self, configFile: str):
      self.modules = []
      self.data = openWBValues()
      self.config = openWBconfig(configFile)
      if self.config.get('testmode') is None:
         self.mqtt = Mqttpublisher(self)
      self.logger = logging.getLogger(self.__class__.__name__)
      self.pvmodule = 0
      self.regelkreise = dict()
      setCore(self)

   @staticmethod
   def add_module(module: Modul, configprefix: str) -> None:
      core = getCore()
      core.modules.append(module)
      if hasattr(module, 'type'):
         if module.type == "wr":
            core.pvmodule += 1
         elif module.type == "lp":
            lpmode = core.config.get(configprefix + '_mode')
            if lpmode not in core.regelkreise:
               core.regelkreise[lpmode] = Regelgruppe(lpmode)
            core.regelkreise[lpmode].add(module)
            core.sendData(DataPackage(module, {'lpconf': True, 'lpenabled': True }))   # LP Konfiguriert und enabled
      module.configprefix = configprefix
      module.setup(core.config)

   def run(self, loops: int = 0) -> None:
      """Run the given number of loops (0=infinite)"""
      if loops == 0:
         condition = lambda: True
      else:
         done = (i < loops for i in range(loops+1))
         condition = lambda: next(done)
      while condition():
         for module in self.modules:
            module.trigger()
         self.data.derive_values()
         self.logger.debug("Values: " + str(self.data))
         for gruppe in self.regelkreise.values():
            gruppe.controlcycle(self.data)
         debug = "PV: %iW EVU: %iW " % (-self.data.get("pvwatt"), -self.data.get("wattbezug"))
         debug += "Laden: %iW" % self.data.get("llaktuell")
         for kreis in self.regelkreise.values():
            for lp in kreis.regler.values():
               id = lp.wallbox.id
               on = "*" if self.data.get('ladestatus', id) else ""
               debug += f"({id}{on}: {lp.mode} {self.data.get('lla1', id)}A {self.data.get('llaktuell',id)}W"
               if lp.oncount > 0:
                  debug += f" +{lp.oncount}"
               if lp.offcount > 0:
                  debug += f" -{lp.offcount}"
               debug += ")"
         debug += " Haus: %iW" % self.data.get("hausverbrauch")
         self.logger.info(debug)
         if self.config.get('testmode') is None:
            self.mqtt.publish()
            time.sleep(20)

   def sendData(self, package: DataPackage) -> None:
      self.data.update(package)
      self.logger.debug(f'Daten von {package.source.name }: {package}')

   def setConfig(self, key:str, value) -> None:
      """Set the configuration, but also announce this in the system."""
      self.config[key] = value
      self.triggerEvent(Event(EventType.configupdate, key, value))

   def triggerEvent(self, event: Event):
      for module in self.modules:
         module.event(event)
      self.event(event)

   def event(self, event: Event):
      if event.type == EventType.configupdate:
         m = re.match('lpmodul\\d_mode', event.info)
         if m:
            id = m.group(1)
            new_mode = event.payload
            for mode, regelkreis in self.regelkreise.items():
               if mode == new_mode:   # Wenn neu = alt, dann keine Aktion
                  continue
               # Aus altem Regelkreis entfernen
               lp = self.regelkreise[mode].pop(id)
               if lp is not None:
                  self.logger.info("LP %i aus %s entfernt" % (id, mode))
                  # In neuem Regelkreis hinzufügen
                  if new_mode not in self.regelkreise:
                     self.regelkreise[new_mode] = Regelgruppe(new_mode)
                  self.regelkreise[new_mode].add(lp)
                  self.logger.info("LP %i zu %s hinzugefügt" % (id, new_mode))
                  break
