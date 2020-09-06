import os
import paho.mqtt.client as mqtt
from .openWBlib import openWBValues 
from typing import Iterator, Tuple, overload
from datetime import datetime

basePath = os.path.dirname(os.path.realpath(__file__)) + '/'
projectPath = os.path.realpath(os.path.dirname(__file__) + '/../../ramdisk/')


def ramdisk(fileName: str, content, mode: str = 'w'):
   with open(projectPath + '/' + fileName, mode) as f:
      f.write(str(content) + "\n")

def read_ramdisk(fileName: str) -> str:
   with open(projectPath + '/' + fileName) as f:
      return f.read()

class Mqttpublisher(object):
   mapping = {
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
      "lp/%n/ChargePointEnabled": "lp%nenabled",     # Eher Konfiguration
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
      "global/DailyYieldAllChargePointsKwh": "xxx"  # Lademenge daily
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
   qos = 0
   retain = True

   def __init__(self, hostname: str = "localhost"):
      self.client = mqtt.Client("openWB-python-bulkpublisher-" + str(os.getpid()))
      self.client.connect(hostname)
      self.lastdata = {}
      self._init_data()

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
         for n in range(1, 9):
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
      for key in self.mapping.keys():
         self.lastdata.update((mqttkey, 0) for mqttkey in self._loop(key))
      self.all_live = read_ramdisk('all-live.graph').split('\n')

   def publish(self, data: openWBValues):
      for k,v in self.mapping.items():
        for mqttkey, datakey in self._loop(k,v):
          val = data.get(datakey)
          if isinstance(val, bool):   # Convert booleans into 1/0
            val = 1 if val else 0
          if val != self.lastdata[mqttkey]:
            self.lastdata[mqttkey] = val
            if isinstance(bool, val)
            self.client.publish("openWB/" + mqttkey, payload=val, qos=self.qos, retain=self.retain)
      # print("Last values:\n%s" % str(self.lastdata))
      # Live values
      last_live = [datetime.now().strftime("%H:%M:%S")]
      #last_live.extend(str(-data.get(key)) if key[0]=='-' else str(data.get(key)) for key in self.all_live_fields)
      for key in self.all_live_fields:
         last_live.append(str(-data.get(key[1:])) if key[0] == '-' else str(data.get(key)))
         
      last_live = ",".join(last_live)
      self.all_live.append(last_live)
      print("Live:\n%s" % last_live)
      if len(self.all_live) > 800:
         self.all_live = self.all_live[-800:]
      self.client.publish("openWB/graph/lastlivevalues", payload=last_live, retain=self.retain)
      for index, n in enumerate(range(0, 800, 50)):
         if len(self.all_live) > n:
            pl = "\n".join(self.all_live[n:n+50])
            self.client.publish("openWB/graph/%ialllivevalues" % index,
                                payload="\n".join(self.all_live[n:n+50]), retain=self.retain)
         else:
            pl = "-\n"
         self.client.publish("openWB/graph/%ialllivevalues" % index, payload=pl, retain=self.retain)
      self.client.loop(timeout=2.0)

      # Graphen aus der Ramdisk
      ramdisk('all-live.graph', "\n".join(self.all_live))
      ramdisk('pv-live.graph', data.get("pvwatt"), 'a')
      ramdisk('evu-live.graph', data.get("uberschuss"), 'a')
      ramdisk('ev-live.graph', data.get("llaktuell"), 'a')
