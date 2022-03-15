#!/usr/bin/python3

from .mqttpub import Mqttpublisher


def init_system(host: str = "localhost"):
   initial_mqtt = {
      "lp/%i/boolChargePointConfigured": 0,
      "config/get/SmartHome/Devices/%i/device_configured": 0,
      "hook/%i/boolHookConfigured": 0,
      "housebattery/boolHouseBatteryConfigured": 0
   }
   mqtt = Mqttpublisher(None, host, "openWB-setup")
   for topic, value in initial_mqtt.items():
      if "%i" in topic:
         for id in range(1, 9):
            mqtt.publish_config(topic % id, value)
      else:
         mqtt.publish_config(topic, value)
   del mqtt
