import os
from openWB.Event import OpenWBEvent, EventType
from .openWBlib import *
from .mqttpub import Mqttpublisher
from .ramdiskpublisher import RamdiskPublisher
from plugins import *
from datetime import datetime
from threading import Lock, Thread

import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(message)s', filename="/var/log/openWB.log")
if os.environ.get("DEBUG") == "1":
   logging.basicConfig(level=logging.DEBUG)

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
         self.kreiselock = Lock()

   def setup(self) -> "OpenWBCore":
      self.config = OpenWBconfig()
      self.data = openWBValues()
      self.modules['EVU'] = EVUModule()
      self.modules['PV'] = PVModule()
      self.modules['LP'] = LPModule()
      self.modules['SPEICHER'] = SpeicherModule()
      self.modules['DISPLAY'] = DisplayModule()
      self.modules['HELPER'] = [DependentData()]
      if self.config.get('testmode') is None:
         self.publishers = [Mqttpublisher(self), RamdiskPublisher(self)]
      with self.kreiselock:
         for lp in self.modules['LP'].modules:
            lpmode = self.config.get(lp.configprefix + '_mode')
            if lpmode not in self.regelkreise:
               from openWB.regler import Regelgruppe
               self.regelkreise[lpmode] = Regelgruppe(lpmode)
            self.regelkreise[lpmode].add(lp)
      Scheduler().registerEvent(EventType.configupdate, self.event)
      Scheduler().registerTimer(5, self.loop)  # TODO: Thread, nicht öfter als alle x s
      return self

   def logdebug(self):
      debug = "PV: %iW EVU: %iW " % (-self.data.get("pvwatt"), -self.data.get("wattbezug"))
      debug += "Batt: %iW (%i%%) " % (self.data.get("speicherleistung"), self.data.get("speichersoc"))
      debug += "Laden: %iW " % self.data.get("llaktuell")
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
      debug += "Haus: %iW " % self.data.get("hausverbrauch")
      self.logger.info(datetime.now().strftime("%H:%M:%S") + ':' + debug)

   def setconfig(self, key:str, value) -> None:
      """Set the configuration, but also announce this in the system."""
      self.config[key] = value
      self.logger.info("Config updated %s = %s" % (key, value))
      # Start a new thread, so it is non-blocking.
      Thread(target=Scheduler().signalEvent, args=(OpenWBEvent(EventType.configupdate, key, value),)).start()

   def event(self, event: OpenWBEvent) -> None:
      self.logger.info("Event: %s = %s" % (event.info, event.payload))
      try:
       if event.type == EventType.configupdate:
         m = re.match('lpmodul(\\d)_mode', event.info)
         if m:
            id = int(m.group(1))
            new_mode = event.payload
            with self.kreiselock:
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
                     self.logger.info(f"LP {id}: {mode} -> {new_mode} ")
                     break
            self.logger.info("Nach Reconfigure: " + str(self.regelkreise))

      except Exception as e:
         self.logger.critical("BAM!!!", exc_info = e)

   def loop(self) -> None:
      with self.kreiselock:
         for kreis in self.regelkreise.values():
            kreis.loop()

