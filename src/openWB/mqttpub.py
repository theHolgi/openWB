import os
import re
import subprocess
from enum import Enum

import paho.mqtt.client as mqtt

from openWB import DataPackage
from typing import Iterator, Tuple
from datetime import datetime
from time import time
import logging

from openWB.Event import OpenWBEvent, EventType
from openWB.Scheduling import Scheduler

basePath = os.path.dirname(os.path.realpath(__file__)) + '/'
projectPath = os.path.realpath(os.path.dirname(__file__) + '/../../ramdisk/')


def ramdisk(fileName: str, content, mode: str = 'w'):
   with open(projectPath + '/' + fileName, mode) as f:
      f.write(str(content) + "\n")


def read_ramdisk(fileName: str) -> str:
   with open(projectPath + '/' + fileName) as f:
      return f.read()


def _loop(key1: str, key2: str) -> Iterator[Tuple[str, str]]:
   if key1.find('%n') >= 0:  # Instance
      for n in range(1, 9):  # Mqttpublisher.num_lps + 1
         yield key1.replace('%n', str(n)), key2.replace('%n', str(n))
   elif key1.find('%p') >= 0:  # Phase
      for phase in range(1, 4):
         yield key1.replace('%p', str(phase)), key2.replace('%p', str(phase))
   else:
      yield key1, key2


class Chargemap(Enum):
   sofort = 0
   peak = 1
   pv = 2
   stop = 3
   awattar = 4


class Mqttpublisher(object):
   priority = 999
   configmapping = {
      "lp/%n/strChargePointName": "lp%nname",
      "lp/%n/chargeLimitation": "msmoduslp%n",
      "lp/%n/energyConsumptionPer100km": "durchslp%n",
      "config/get/pv/minBatteryChargePowerAtEvPriority": "speichermaxwatt",
      "config/get/pv/minBatteryDischargeSocAtBattPriority": "speichersocnurpv",
      "config/get/pv/batteryDischargePowerAtBattPriority": "speicherwattnurpv",
      "graph/boolDisplayHouseConsumption": "display_house",
      "graph/boolDisplayLoad%n": "display_load%n",
      "graph/boolDisplayLp%nSoc": "display_lp%nsoc",
      "graph/boolDisplayLpAll": "display_lpAll",
      "graph/boolDisplaySpeicherSoc": "display_speichersoc",
      "graph/boolDisplaySpeicher": "display_speicher",
      "graph/boolDisplayEvu": "display_evu",
      "graph/boolDisplayLegend": "display_legend",
      "graph/boolDisplayLiveGraph": "display_lIVE",
      "graph/boolDisplayPv": "display_PV"
   }
   datamapping = {  # UNUSED

      # LP
      "lp/%n/AConfigured": "llsoll%n",  # Soll Strom

      "lp/%n/kWhActualCharged": "aktgeladen%n",
      "lp/%n/kWhChargedSincePlugged": "pluggedladungbishergeladen%n",
      "lp/%n/TimeRemaining": "restzeitlp%n",
      "lp/%n/AutolockStatus": "autolockstatuslp%n",
      "lp/%n/AutolockConfigured": "autolockconfiguredlp%n",
      "config/get/sofort/lp/%n/current": "lpsofortll%n",

      "global/DailyYieldHausverbrauchKwh": "xxx",  # Hausverbrauch daily
      "global/DailyYieldAllChargePointsKwh": "daily_llkwh",  # Lademenge daily
   }
   # Fields for live chart
   all_live_fields = ("-evu/W", "global/WAllChargePoints", "pv/W",  # 3
                      "lp/1/W", "lp/2/W", "llaktuell",  # 6
                      "housebattery/W", "housebattery/%Soc", "lp/1/soc", "lp/2/soc", "global/WHouseConsumption",  # 11
                      "verbraucher1_watt", "verbraucher2_watt",  # 13
                      "llaktuell3", "llaktuell4", "llaktuell5",  # 16
                      "llaktuell6", "llaktuell7", "llaktuell8",  # 19
                      "shd1_w", "shd2_w", "shd3_w", "shd4_w",  # 23
                      "shd5_w", "shd6_w", "shd7_w", "shd8_w"  # 27
                      )

   # Fields for long-time graph

   all_fields = ("-evu/W", "global/WAllChargePoints", "pv/W",  # 3
                 "lp/1/W", "lp/2/W", "lp/3/W", "lp/5/W", "lp/5/W", "evu/WPhase1", "evu/WPhase2", "evu/WPhase3",  # 11
                 "housebattery/W", "housebattery/%Soc", "lp/1/soc", "lp/2/soc", "global/WHouseConsumption",  # 16
                 "verbraucher1_watt", "verbraucher2_watt"
                 )
   retain = True
   num_lps = 0  # Anzahl Ladepunkte
   configqos = 2

   def __init__(self, core, hostname: str = "localhost", client_id: str = "openWB-bulkpublisher"):
      self.core = core
      self.name = "MQTT"
      self.logger = logging.getLogger('MQTT')
      self.client = mqtt.Client(client_id + "-" + str(os.getpid()))
      self.client.on_message = lambda client, userdata, msg: self.messagehandler(msg)
      self.client.connect(hostname)
      self.client.loop_start()
      self.graphtimer = 0
      self.all_live = []
      self.all_data = []

      def log_proxy(client, userdata, level, buf):
         if level == mqtt.MQTT_LOG_INFO:
            method = self.logger.info
         elif level == mqtt.MQTT_LOG_WARNING:
            method = self.logger.warning
         else:
            method = self.logger.error
         method(buf)

      # self.client.on_log = log_proxy

   def __del__(self):
      self.client.disconnect()

   def setup(self):
      """Subscribe to set topics"""
      self.bulk_config()
      self.logger.debug('Subscribing.')
      self.client.subscribe("openWB/set/#", 2)
      self.client.subscribe("openWB/config/set/#", 2)
      scheduler = Scheduler()
      scheduler.registerData(["*"], self)
      scheduler.registerTimer(10, self.publishLiveData)  # TODO: React on Chargepoint  end-of-loop event
      scheduler.registerEvent(EventType.configupdate, self.newconfig)
      scheduler.registerEvent(EventType.resetDaily, self.cut_live)

   def newdata(self, data: dict):
      """Handler for subscribed registerData"""
      for key, value in data.items():
         # self.logger.debug(f"Publish: openWB/{key} = {value}")
         self.publish_data(key, value)

   def newconfig(self, event: OpenWBEvent):
      """Handler for subscribed configupdate Event"""
      if event.type == EventType.configupdate:
         self.logger.info(f'MQTT config update: {event.info} = {event.payload}')
         m = re.match("lpmodul(\\d)_mode", event.info)  # Chargepoint mode
         if m:
            mode = Chargemap[event.payload]
            self.publish_config("config/get/lp/%s/ChargeMode" % m.group(1), mode.value)
            return

   def cut_live(self):
      """Reset the live graphes"""
      for name in ['pv', 'evu', 'ev', 'speicher', 'soc']:
         filename = name + "-live.graph"
         content = read_ramdisk(filename).splitlines(keepends=True)
         ramdisk(filename, ''.join(content[-6 * (self.core.config.get('livegraph')):]))

   def publish_data(self, topic: str, payload, qos=2) -> None:
      """Publish topic/payload with data quality; topic not including "openWB" prefix"""
      self.client.publish("openWB/" + topic, payload, qos=qos, retain=True)

   def publish_config(self, topic: str, payload, qos=1) -> None:
      """Publish topic/payload with config quality; topic not including "openWB" prefix"""
      self.client.publish("openWB/" + topic, payload, qos=qos, retain=True)

   def publishLiveData(self):
      self.num_lps = sum(1 if self.core.data.get('lpconf', id=n) else 0 for n in range(1, 9))

      # Live values
      last_live = [datetime.now().strftime("%H:%M:%S")]
      # last_live.extend(str(-data.get(key)) if key[0]=='-' else str(data.get(key)) for key in self.all_live_fields)
      for key in self.all_live_fields:
         last_live.append(str(-self.core.data.get(key[1:])) if key[0] == '-' else str(self.core.data.get(key)))

      last_live = ",".join(last_live)
      self.all_live.append(last_live)
      self.logger.debug("Live: %s" % last_live)
      if len(self.all_live) > 800:
         self.all_live = self.all_live[-800:]
      self.logger.debug("all_live now %i long." % len(self.all_live))
      self.publish_data("graph/lastlivevalues", last_live)
      self.publish_data("system/Timestamp", int(time()))
      for index, n in enumerate(range(0, 800, 50)):
         if len(self.all_live) > n:
            pl = "\n".join(self.all_live[n:n + 50])
         else:
            pl = "-\n"
         self.publish_data("graph/%ialllivevalues" % (index + 1), payload=pl)
      self.logger.debug("Publish (1)")

      # All (long-time chart) values
      self.graphtimer += 1
      if self.graphtimer == 4:
         self.graphtimer = 0
         all_live = [datetime.now().strftime("%Y/%m/%d %H:%M:%S")]
         for key in self.all_fields:
            all_live.append(str(-self.core.data.get(key[1:])) if key[0] == '-' else str(self.core.data.get(key)))
         self.all_data.append(','.join(all_live))
         self.logger.debug("Longtime Live: %s" % all_live)
         if len(self.all_data) > 2000:
            self.all_data = self.all_data[-2000:]
         ramdisk('all.graph', "\n".join(self.all_data))

      self.logger.debug("Publish (2)")
      # Graphen aus der Ramdisk
      ramdisk('all-live.graph', "\n".join(self.all_live))
      ramdisk('pv-live.graph', self.core.data.get("pv/W"), 'a')
      ramdisk('evu-live.graph', self.core.data.get("evu/W"), 'a')
      ramdisk('ev-live.graph', self.core.data.get("llaktuell"), 'a')
      ramdisk('speicher-live.graph', self.core.data.get('housebattery/W'), 'a')
      ramdisk('speichersoc-live.graph', self.core.data.get('housebattery/%Soc'), 'a')
      self.logger.debug("Publish (done)")

   def awattargraph(self, ):
      """openWB/global/awattar/pricelist"""

   def bulk_config(self):
      """Sende Config als MQTT"""
      for k, v in self.configmapping.items():
         for mqttkey, datakey in _loop(k, v):
            val = self.core.config.get(datakey)
            if isinstance(val, bool):  # Convert booleans into 1/0
               val = 1 if val else 0
            if val is not None:
               self.publish_config(mqttkey, val)

   def messagehandler(self, msg):
      """Handle incoming requests"""
      republish = False
      getter_topic = msg.topic.replace('openWB/', '').replace('/set/', '/get/')
      self.logger.info("receive: %s = %s" % (repr(msg.topic), repr(msg.payload)))
      try:
         val = int(msg.payload)
 #        self.logger.info("Value: %i" % val)
      except ValueError:
         val = None
      try:
         if msg.topic == "openWB/config/set/pv/regulationPoint":  # Offset (PV)
            if val is not None and -300000 <= val <= 300000:
               republish = True
               self.core.setconfig('offsetpv', val)
         elif msg.topic == "openWB/config/set/pv/priorityModeEVBattery":  # Priorität Batt/EV
            if val is not None and 0 <= val <= 2:
               republish = True
               self.core.setconfig('speicherpveinbeziehen', val)
         elif msg.topic == "openWB/config/set/pv/nurpv70dynw":
            republish = True
            self.core.setconfig('offsetpvpeak', val)
         elif msg.topic.startswith("openWB/config/set/sofort/"):  # Sofortladen...
            device = int(re.search('/lp/(\\d)/', msg.topic).group(1))
            if 1 <= device <= 8:
               republish = True
               if msg.topic.endswith('current'):
                  if val is not None and 6 <= val <= 32:
                     self.core.setconfig('lpmodul%i_sofortll' % device, val)
               elif msg.topic.endswith('chargeLimitation'):  # Limitierung Modus
                  if val is not None and 0 <= val <= 2:
                     self.core.setconfig('msmoduslp%i' % device, val)
                     self.publish_config("lp/%i/boolDirectModeChargekWh" % device, 1 if val == 1 else 0)
                     self.publish_config("lp/%i/boolDirectChargeModeSoc" % device, 1 if val == 2 else 0)
               elif msg.topic.endswith('energyToCharge'):  # Modus 1: Lademenge [kWh]
                  if val is not None and 0 <= val <= 100:
                     self.core.setconfig('lademkwh%i' % device, val)
               elif msg.topic.endswith('socToChargeTo'):  # Modus 2: SOC [%]
                  if val is not None and 0 <= val <= 100:
                     self.core.setconfig('sofortsoclp%i' % device, val)
               elif msg.topic.endswith('resetEnergyToCharge'):
                  republish = False
                  if msg.payload:
                     Scheduler().signalEvent(OpenWBEvent(EventType.resetEnergy, device))

         elif msg.topic == "openWB/config/set/pv/stopDelay":
            if val is not None and 0 <= val <= 10000:
               republish = True
               self.core.setconfig('abschaltverzoegerung', val)
         elif msg.topic.startswith('openWB/config/set/lp/'):  # Ladepunkt Konfiguration
            self.logger.info("LP message")
            device = int(re.search('/lp/(\\d)', msg.topic).group(1))
            if re.search("/ChargeMode", msg.topic):  # Chargemode
               mode = Chargemap(val)
               self.logger.info(f'ChargeMode lp{device} = {mode}')
               if 1 <= device <= 8:
                  self.core.setconfig('lpmodul%i_mode' % device, mode.name)
            elif re.search("/alwaysOn", msg.topic):
               self.logger.info(f'AlwaysOn lp{device} = {msg.payload}')
               if 1 <= device <= 8:
                  republish = True
                  self.core.setconfig('lpmodul%i_alwayson' % device, bool(int(msg.payload)))
         elif msg.topic == "openWB/set/graph/RequestDayGraph":
            # Anforderung eines Daily graphs.
            # Format Wert: yyyymmdd
            # Antwort: openWB/system/DayGraphData1<n>, n=1..12 je 25 Zeilen
            # Herkunft: web/logging/data/<yyyymm>.csv erzeugt von Cronjob "cron5min.sh"
            # echo $(date +%H%M),$bezug,$einspeisung,$pv,$ll1,$ll2,$ll3,$llg,$speicheri,$speichere,$verbraucher1,$verbrauchere1,$verbraucher2,$verbrauchere2,$verbraucher3,$ll4,$ll5,$ll6,$ll7,$ll8,$speichersoc,$soc,$soc1,$temp1,$temp2,$temp3,$d1,$d2,$d3,$d4,$d5,$d6,$d7,$d8,$d9,$d10,$temp4,$temp5,$temp6 >> $dailyfile.csv
            if 1 <= val <= 20501231:
               subprocess.run([basePath + '../../runs/senddaygraphdata.sh', msg.payload])
         elif msg.topic == 'openWB/set/graph/RequestMonthGraph':
            # Anforderung eines Month graphs.
            # Format Wert: yyyymm
            # Antwort: openWB/system/MonthGraphData<n>, n=1..12 je 25 Zeilen
            # Herkunft: web/logging/data/<yyyymm>.csv erzeugt von Cronjob "cronnightly.sh"
            # echo $(date +%Y%m%d),$bezug,$einspeisung,$pv,$ll1,$ll2,$ll3,$llg,$verbraucher1iwh,$verbraucher1ewh,$verbraucher2iwh,$verbraucher2ewh,$ll4,$ll5,$ll6,$ll7,$ll8,$speicherikwh,$speicherekwh,$d1,$d2,$d3,$d4,$d5,$d6,$d7,$d8,$d9,$d10 >> $monthlyfile.csv
            if 1 <= val <= 20501231:
               subprocess.run([basePath + '../../runs/sendmonthgraphdata.sh', msg.payload])
         elif msg.topic == "openWB/set/graph/RequestLiveGraph":
            if val == 1:
               subprocess.run(basePath + "../../runs/sendlivegraphdata.sh")
            else:
               self.publish_data("system/LiveGraphData", "empty", qos=0)
         elif msg.topic == "openWB/set/graph/RequestLLiveGraph":
            if val == 1:
               subprocess.run(basePath + "../../runs/sendllivegraphdata.sh")
         elif getter_topic in self.configmapping:
            if val is not None and 0 <= val <= 10000:
               republish = True
               self.core.setconfig(self.configmapping[getter_topic], val)
         else:
            self.logger.info("Nix gefunden.")
      except IOError as e:  # Exception
         self.logger.exception("BAMM!", exc_info=e)
      if republish:
         self.logger.info("Re-publish: %s = %s" % (getter_topic, msg.payload))
         self.publish_config(getter_topic, msg.payload)


"""
openWB/set/ChargeMode/lp/1
openWB/config/set/sofort/lp/1/chargeLimitation 1 = Energy, 2 = SoC
"""
