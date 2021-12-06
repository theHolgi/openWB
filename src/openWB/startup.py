#!/usr/bin/python3

from .mqttpub import Mqttpublisher


def init_system(host: str = "localhost"):
   initial_mqtt = {
    "lp/%i/boolChargePointConfigured": 0
   }
   mqtt = Mqttpublisher(None, host)
   for topic, value in initial_mqtt.items():
      if "%i" in topic:
         for id in range(1, 9):
            mqtt.publish_config(topic % id, value)
      else:
         mqtt.publish_config(topic, value)
