import os
import re
import sys

import paho.mqtt.client as mqtt

from . import DataPackage
from typing import Iterator, Tuple, overload
from datetime import datetime
from time import time
import logging

basePath = os.path.dirname(os.path.realpath(__file__)) + '/'
projectPath = os.path.realpath(os.path.dirname(__file__) + '/../../ramdisk/')


def ramdisk(fileName: str, content, mode: str = 'w'):
   with open(projectPath + '/' + fileName, mode) as f:
      f.write(str(content) + "\n")

def read_ramdisk(fileName: str) -> str:
   with open(projectPath + '/' + fileName) as f:
      return f.read()

class Mqttpublisher(object):
   configmapping = {
      "lp/1/strChargePointName": "lp%nname"
   }
   datamapping = {
      # EVU
      "evu/W": "wattbezug",
      "evu/WhExported": "einspeisungkwh",
      "evu/WhImported": "bezugkwh",
      "evu/APhase%p": "bezuga%p",
      "evu/VPhase%p": "evuv%p",
      "evu/WPhase%p": "bezuga%p",
      "evu/PfPhase%p": "evupf%p",
      "evu/ASchieflast": "schieflast",
      "evu/Hz": "evuhz",
      "global/WHouseConsumption": "hausverbrauch",

      # PV
      "pv/W": "pvwatt",
      "pv/WhCounter": "pvkwh",

      # LP
      "global/WAllChargePoints": "llaktuell",
      "lp/%n/W": "llaktuell%n",
      "lp/%n/VPhase%p": "llv%p%n",
      "lp/%n/APhase%p": "lla%p%n",
      "lp/%n/PfPhase%p": "llpf%p%n",
      "lp/%n/kWhCounter": "llkwh%n",
      "lp/%n/AConfigured": "llsoll%n",         # Soll Strom
      "lp/%n/ChargeStatus": "ladestatus%n",    # Soll geladen werden
      "lp/%n/boolPlugStat": "plugstat%n",      # plugged
      "lp/%n/boolChargeStat": "chargestat%n",  # charging

      "lp/%n/countPhasesInUse": "lpphasen%n",
      "lp/%n/kWhActualCharged": "aktgeladen%n",
      "lp/%n/kWhChargedSincePlugged": "pluggedladungbishergeladen%n",
      "lp/%n/TimeRemaining": "restzeitlp%n",
      "lp/%n/ChargePointEnabled": "lpenabled%n",       # Nicht enabled ist z.B. nach Ablauf der Lademenge
      "lp/%n/boolChargePointConfigured": "lpconf%n",   # Configured -> Geräte konfiguriert
      "lp/%n/AutolockStatus": "autolockstatuslp%n",
      "lp/%n/AutolockConfigured": "autolockconfiguredlp%n",
      "config/get/sofort/lp/%n/current": "lpsofortll%n",

      # Daily Daten
      "evu/DailyYieldImportKwh": "daily_bezugkwh",
      "evu/DailyYieldExportKwh": "daily_einspeisungkwh",
      "pv/DailyYieldKwh": "daily_pvkwhk",
      "housebattery/DailyYieldImportKwh": "daily_sikwh",
      "housebattery/DailyYieldExportKwh": "daily_sekwh",

      "global/DailyYieldHausverbrauchKwh": "xxx",  # Hausverbrauch daily
      "global/DailyYieldAllChargePointsKwh": "xxx",  # Lademenge daily
      
      # Config
      "pv/bool70PVDynStatus": "nurPV70Status"
   }
   all_live_fields = ("uberschuss", "ladeleistung", "-pvwatt", #3
                      "llaktuell1", "llaktuell2", "llaktuell", #6
                      "speicherleistung", "speichersoc", "soc", "soc1", "hausverbrauch", #11
                      "verbraucher1_watt", "verbraucher2_watt", #13
                      "llaktuell3", "llaktuell4", "llaktuell5", #16
                      "llaktuell6", "llaktuell7", "llaktuell8", # 19
                      "shd1_w", "shd2_w", "shd3_w", "shd4_w", #23
                      "shd5_w", "shd6_w", "shd7_w", "shd8_w" #27
                      )
   retain = True
   core = None
   num_lps = 0   # Anzahl Ladepunkte
   configqos = 2

   def __init__(self, core, hostname: str = "localhost"):
      def on_connect(client, userdata, flags, rc):
         """Subscribe to set topics"""
         self.logger.info('Subscribing.')
         client.subscribe("openWB/set/#", 2)
         client.subscribe("openWB/config/set/#", 2)

      def on_message(client, userdata, msg):
         """Handle incoming messages"""
         self.messagehandler(msg)

      self.core = core
      self.name = "MQTT"
      self.logger = logging.getLogger('MQTT')
      self.lastdata = {}
      self._init_data()
      self.client = mqtt.Client("openWB-python-bulkpublisher-" + str(os.getpid()))
      self.client.on_message = on_message
      self.client.on_connect = on_connect
      self.client.connect(hostname)
      self.client.loop_start()
      self.publish_config()

   @overload
   @staticmethod
   def _loop(key: str) -> Iterator[str]:
      ...

   @overload
   @staticmethod
   def _loop(key: Tuple[str, str]) -> Iterator[Tuple[str, str]]:
      ...

   @staticmethod
   def _loop(key: str, key2: str = None) -> Iterator[str]:
      if key.find('%n') >= 0:  # Instance
         for n in range(1, 9):   # Mqttpublisher.num_lps + 1
            if key2 is None:
               for k1 in Mqttpublisher._loop(key.replace('%n', str(n))):
                 yield k1
            else:
               for k1, k2 in Mqttpublisher._loop(key.replace('%n', str(n)), key2.replace('%n', str(n))):
                 yield k1, k2
      elif key.find('%p') >= 0:  # Phase
         for phase in range(1, 4):
            if key2 is None:
               yield key.replace('%p', str(phase))
            else:
               yield key.replace('%p', str(phase)), key2.replace('%p', str(phase))
      else:
         if key2 is None:
            yield key
         else:
            yield key, key2

   def _init_data(self):
      for key in self.datamapping.keys():
         self.lastdata.update((mqttkey, None) for mqttkey in self._loop(key))
      self.all_live = read_ramdisk('all-live.graph').split('\n')

   def publish(self):
      self.num_lps = sum(1 if self.core.data.get('lpconf', id=n) else 0 for n in range(1, 9))
      for k, v in self.datamapping.items():
        for mqttkey, datakey in self._loop(k, v):
          val = self.core.data.get(datakey)
          if isinstance(val, bool):   # Convert booleans into 1/0
            val = 1 if val else 0
          if val != self.lastdata[mqttkey]:
            self.lastdata[mqttkey] = val
            self.client.publish("openWB/" + mqttkey, payload=val, qos=0, retain=True)

      # Live values
      last_live = [datetime.now().strftime("%H:%M:%S")]
      #last_live.extend(str(-data.get(key)) if key[0]=='-' else str(data.get(key)) for key in self.all_live_fields)
      for key in self.all_live_fields:
         last_live.append(str(-self.core.data.get(key[1:])) if key[0] == '-' else str(self.core.data.get(key)))
         
      last_live = ",".join(last_live)
      self.all_live.append(last_live)
      print("Live: %s" % last_live)
      if len(self.all_live) > 800:
         self.all_live = self.all_live[-800:]
      self.client.publish("openWB/graph/lastlivevalues", payload=last_live)
      self.client.publish("openWB/system/Timestamp", int(time()) , qos=0)
      for index, n in enumerate(range(0, 800, 50)):
         if len(self.all_live) > n:
            pl = "\n".join(self.all_live[n:n+50])
            self.client.publish("openWB/graph/%ialllivevalues" % index,
                                payload="\n".join(self.all_live[n:n+50]), retain=self.retain)
         else:
            pl = "-\n"
         self.client.publish("openWB/graph/%ialllivevalues" % index, payload=pl, retain=self.retain)

      # Graphen aus der Ramdisk
      ramdisk('all-live.graph', "\n".join(self.all_live))
      ramdisk('pv-live.graph', self.core.data.get("pvwatt"), 'a')
      ramdisk('evu-live.graph', self.core.data.get("uberschuss"), 'a')
      ramdisk('ev-live.graph', self.core.data.get("llaktuell"), 'a')

   def publish_config(self):
      """Sende Config als MQTT"""
      for k, v in self.configmapping.items():
         for mqttkey, datakey in self._loop(k, v):
            val = self.core.config.get(datakey)
            if isinstance(val, bool):   # Convert booleans into 1/0
               val = 1 if val else 0
            if val is not None:
               self.client.publish("openWB/" + mqttkey, payload=val, qos=self.configqos, retain=True)

   def messagehandler(self, msg):
      """Handle incoming requests"""
      republish = False
      self.logger.info("receive: %s = %s" % (repr(msg.topic), repr(msg.payload)))
      found = msg.topic.startswith('openWB/set/ChargeMode/lp/')
      try:
         val = int(msg.payload)
         self.logger.info("Value: %i" % val)
      except ValueError:
         val = None
      try:
         if msg.topic == "openWB/config/set/pv/regulationPoint":   # Offset (PV)
            if -300000 <= val <= 300000:
               republish = True
               self.core.setconfig('offsetpv', val)
         elif msg.topic == "openWB/config/set/pv/nurpv70dynw":
            republish = True
            self.core.setconfig('offsetpvpeak', val)
         elif re.match("openWB/set/lp/(\\d)/ChargePointEnabled", msg.topic):     # Chargepoint en/disable
            device = int(re.search('/lp/(\\d)/', msg.topic).group(1))
            republish = True
            self.core.sendData(DataPackage(self, {'lpenabled%i' % device: val}))
         elif msg.topic.startswith("openWB/config/set/sofort/"):  # Sofortladen...
            device = int(re.search('/lp/(\\d)/', msg.topic).group(1))
            if 1 <= device <= 8:
               republish = True
               if msg.topic.endswith('current'):
                  self.core.setconfig('lpmodul%i_sofortll' % device, val)
               elif msg.topic.endswith('energyToCharge'):
                  self.core.setconfig('lademkwh%i' % device, val)
               elif msg.topic.endswith('resetEnergyToCharge'):
                  self.core.sendData(DataPackage(self, {'aktgeladen%i' % device: 0}))
         elif msg.topic == "openWB/config/set/pv/stopDelay":
            if 0 <= val <= 10000:
               republish = True
               self.core.setconfig('abschaltverzoegerung', val)
         elif msg.topic == "openWB/set/pv/NurPV70Status":   # 70% mode
            self.core.data["nurPV70Status"] = val == 1
            self.logger.info("Konfiguriere %i Ladepunkte" % self.num_lps)
            for n in range(1, self.num_lps+1):
               self.logger.info("LP %i" % n)
               if self.core.config.get('lpmodul%i_mode' % n) == "pv" and val == 1:
                  self.logger.info("LP %i = peak" % n)
                  self.core.setconfig('lpmodul%i_mode' % n, "peak")
               elif self.core.config.get('lpmodul%i_mode' % n) == "peak" and val == 0:
                  self.logger.info("LP %i = pv" % n)
                  self.core.setconfig('lpmodul%i_mode' % n, "pv")
         elif msg.topic.startswith('openWB/set/ChargeMode/lp/'):   # Individueller Lademodus
            device = int(re.search('/lp/(\\d)', msg.topic).group(1))
            self.logger.info(f'ChargeMode lp{device} = {msg.payload.decode()}')
            if 1 <= device <= 8:
               self.core.setconfig('lpmodul%i_mode' % device, msg.payload.decode())            
         elif msg.topic == "openWB/set/ChargeMode":         # Globaler Lademodus
            #        sofort  min-pv  pv standby stop
            mode = ['sofort', 'pv', 'pv', 'standby', 'stop'][val]
            if val == 1 or val == 2:
               if self.core.data["nurPV70Status"]:
                 mode = "peak"
            for n in range(1, self.num_lps+1):
               self.core.setconfig('lpmodul%i_mode' % n, mode)
            if val == 1:   # min-PV
               for n in range(1, self.num_lps + 1):
                  self.core.setconfig('lpmodul%i_alwayson' % n, True)
            elif val == 2:  # PV
               for n in range(1, self.num_lps + 1):
                  self.core.setconfig('lpmodul%i_alwayson' % n, False)
         else:
            logger.info("Nix gefunden.")
      except Exception as e:
         logger.error("BAMM: %s: %s" % (sys.exc_info()[0], e))
      if republish:
         self.client.publish(msg.topic.replace('/set/', '/get/'), msg.payload, qos=self.configqos, retain=True)

"""
openWB/set/ChargeMode/lp/1
"""
