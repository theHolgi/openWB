from . import Modul, DataPackage, setCore, getCore, Event, EventType
from .openWBlib import *
from .mqttpub import Mqttpublisher
from .regler import *
from datetime import datetime

import logging
import time
import re

logging.basicConfig(level=logging.DEBUG)

logging.getLogger("Adafruit_I2C.Device.Bus.1.Address.0X40").setLevel(logging.INFO)


class OpenWBCore:
   """openWB core and scheduler"""
   def __init__(self, configFile: str):
      self.modules = []
      self.outputmodules = []
      self.data = openWBValues()
      self.config = openWBconfig(configFile)
      self.ramdisk = ramdiskValues()
      if self.config.get('testmode') is None:
         self.mqtt = Mqttpublisher(self)
      self.logger = logging.getLogger(self.__class__.__name__)
      self.pvmodule = 0
      self.regelkreise = dict()
      self.today = datetime.today().strftime('%D')

      setCore(self)

   def add_module(self, module: Modul, configprefix: str) -> None:
      module.configprefix = configprefix
      module.setup(self.config)
      self.logger.info("Neues Modul: " + module.__class__.__name__)
      if hasattr(module, 'type') and module.type == "display":
         self.outputmodules.append(module)
      else:
         self.modules.append(module)

      if hasattr(module, 'type'):
         if module.type == "wr":
            self.pvmodule += 1
         elif module.type == "speicher":
            self.sendData(DataPackage(module, {'speichervorhanden': True}))  # Speicher vorhanden
         elif module.type == "lp":
            lpmode = self.config.get(configprefix + '_mode')
            if lpmode not in self.regelkreise:
               self.regelkreise[lpmode] = Regelgruppe(lpmode)
            self.regelkreise[lpmode].add(module)
            self.sendData(DataPackage(module, {'lpconf': True, 'lpenabled': True }))   # LP Konfiguriert und enabled

   def run(self, loops: int = 0) -> None:
      """Run the given number of loops (0=infinite)"""
      if loops == 0:
         condition = lambda: True
         self.mqtt.subscribe()
      else:
         done = (i < loops for i in range(loops+1))
         condition = lambda: next(done)
      while condition():
         for module in self.modules:
            module.trigger()
         self.data.derive_values()
         self.logger.debug("Values: " + str(self.data))
         for module in self.outputmodules:
            module.trigger()
         for gruppe in self.regelkreise.values():
            gruppe.controlcycle(self.data)
         self.logdebug()
         if self.config.get('testmode') is None:
            self.mqtt.publish()
            time.sleep(10)
            today = datetime.today().strftime('%D')
            if self.today != today:
               self.today = today
               self.triggerEvent(Event(EventType.resetDaily))

   def logdebug(self):
      debug = "PV: %iW EVU: %iW " % (-self.data.get("pvwatt"), -self.data.get("wattbezug"))
      debug += "Batt: %iW (%i%%)" % (self.data.get("speicherleistung"), self.data.get("speichersoc"))
      debug += "Laden: %iW" % self.data.get("llaktuell")
      for kreis in self.regelkreise.values():
         for lp in kreis.regler.values():
            id = lp.wallbox.id
            on = "*" if self.data.get('ladestatus', id) else ""
            debug += f"({id}{on}: {kreis.mode} {self.data.get('lla1', id)}A {self.data.get('llaktuell', id)}W"
            if lp.oncount > 0:
               debug += f" +{lp.oncount}"
            if lp.offcount > 0:
               debug += f" -{lp.offcount}"
            debug += ")"
      debug += " Haus: %iW" % self.data.get("hausverbrauch")
      self.logger.info(datetime.now().strftime("%H:%M:%S") + ':' + debug)

   def sendData(self, package: DataPackage) -> None:
      self.data.update(package)
      self.logger.debug(f'Daten von {package.source.name }: {package}')

   def setconfig(self, key:str, value) -> None:
      """Set the configuration, but also announce this in the system."""
      self.config[key] = value
      self.logger.info("Config updated %s = %s" % (key, value))
      self.triggerEvent(Event(EventType.configupdate, key, value))

   def triggerEvent(self, event: Event):
      self.logger.info("triggerEvent")
      for module in self.modules:
         self.logger.info("... to %s" % module)
         module.event(event)
      self.event(event)

   def event(self, event: Event):
      self.logger.info("Event: %s = %s" % (event.info, event.payload))
      try:
       if event.type == EventType.configupdate:
         m = re.match('lpmodul(\\d)_mode', event.info)
         if m:
            id = int(m.group(1))
            new_mode = event.payload
            for mode, regelkreis in self.regelkreise.items():
               if mode == new_mode:   # Wenn neu = alt, dann keine Aktion
                  continue
               # Aus altem Regelkreis entfernen
               lp = self.regelkreise[mode].pop(id)
               if lp is not None:
                  # In neuem Regelkreis hinzufügen
                  if new_mode not in self.regelkreise:
                     self.regelkreise[new_mode] = Regelgruppe(new_mode)
                  self.regelkreise[new_mode].add(lp)
                  # Entferne leere Regelgruppe
                  if self.regelkreise[mode].isempty:
                     del self.regelkreise[mode]
                  self.logger.info(f"LP {id}: {mode} -> {new_mode} ")
                  break
            self.logger.info("Nach Reconfigure: " + str(self.regelkreise.keys()))
         elif re.match('speichermodul1', event.info):
            self.ramdisk['speichervorhanden'] = 1 if event.payload != "none" else 0
             
      except Exception as e:
         print("BAM!!! %s" % e)
