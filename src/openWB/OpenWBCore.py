from openWB import DataPackage
from openWB.Event import OpenWBEvent, EventType
from .openWBlib import *
from .mqttpub import Mqttpublisher
from .ramdiskpublisher import RamdiskPublisher
from plugins import *
from datetime import datetime

import logging
import time
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(message)s', filename="/var/log/openWB.log")

infologgers = ['Adafruit_I2C.Device.Bus.1.Address.0X40', 'pymodbus']
for logger in infologgers:
   logging.getLogger(logger).setLevel(logging.INFO)

class OpenWBCore(Singleton):
   """openWB core and scheduler"""
   def __init__(self):
      if not hasattr(self, "modules"):
         self.modules = {}
         self.logger = logging.getLogger(self.__class__.__name__)
         self.pvmodule = 0
         self.regelkreise = dict()
         self.today = datetime.today()
         self.publishers = []

   def setup(self) -> "OpenWBCore":
      self.config = OpenWBconfig()
      self.data = openWBValues()
      self.modules['EVU'] = EVUModule()
      self.modules['PV'] = PVModule()
      self.modules['LP'] = LPModule()
      self.modules['SPEICHER'] = SpeicherModule()
      self.modules['HELPER'] = [DependentData()]
      if self.config.get('testmode') is None:
         self.publishers = [Mqttpublisher(self), RamdiskPublisher(self)]
      for lp in self.modules['LP'].modules:
         lpmode = self.config.get(lp.configprefix + '_mode')
         if lpmode not in self.regelkreise:
            from openWB.regler import Regelgruppe
            self.regelkreise[lpmode] = Regelgruppe(lpmode)
         self.regelkreise[lpmode].add(lp)
      Scheduler().registerEvent(EventType.configupdate, self.event)
      return self

   def run(self, loops: int = 0) -> None:
      """Run the given number of loops (0=infinite)"""
      if loops == 0:
         condition = lambda: True
         for publisher in self.publishers:
            publisher.setup()
      else:
         done = (i < loops for i in range(loops+1))
         condition = lambda: next(done)
      while condition():
         for module in self.modules:
            module.finished.clear()
            module.trigger.set()   # Set the event trigger
         # Now, wait until all backtriggers are set
         for module in self.modules:
            if not module.finished.wait(timeout=10.0):
               self.logger.warn("Timeout waiting for " + module.name)

         ####### Now, all modules have run.
         self.data.derive_values()
         self.logger.debug("Values: " + str(self.data))
         for module in self.outputmodules:
            module.trigger.set()
         for gruppe in self.regelkreise.values():
            gruppe.controlcycle(self.data)
         self.logdebug()
         if self.config.get('testmode') is None:
            for publisher in self.publishers:
               publisher.publish()
            time.sleep(10)
            today = datetime.today()
            if self.today.day != today.day:
               self.triggerEvent(OpenWBEvent(EventType.resetDaily))
               if today.day == 1:
                  self.triggerEvent(OpenWBEvent(EventType.resetMonthly))
            elif self.today.hour != 12 and today.hour == 12:
               self.triggerEvent(OpenWBEvent(EventType.resetNoon))
            self.today = today

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

   def setconfig(self, key:str, value) -> None:
      """Set the configuration, but also announce this in the system."""
      self.config[key] = value
      self.logger.info("Config updated %s = %s" % (key, value))
      Scheduler().signalEvent(OpenWBEvent(EventType.configupdate, key, value))

   def event(self, event: OpenWBEvent) -> None:
      self.logger.info("Event: %s = %s" % (event.info, event.payload))
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
                     from openWB.regler import Regelgruppe
                     self.regelkreise[new_mode] = Regelgruppe(new_mode)
                  self.regelkreise[new_mode].add(lp)
                  # Entferne leere Regelgruppe
                  if self.regelkreise[mode].isempty:
                     self.regelkreise[mode].destroy()
                  self.logger.info(f"LP {id}: {mode} -> {new_mode} ")
                  break
            self.logger.info("Nach Reconfigure: " + str(self.regelkreise.keys()))
