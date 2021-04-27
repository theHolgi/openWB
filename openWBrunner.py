#!/usr/bin/python3
import logging
import os
import sys

mypath = os.path.dirname(os.path.realpath(__file__)) + '/'
sys.path.append(mypath + 'src')

from openWB import OpenWBCore, api
from openWB.Scheduling import Scheduler

if 'http_proxy' in os.environ:
   os.environ.pop('http_proxy')
if 'https_proxy' in os.environ:
   os.environ.pop('https_proxy')

logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(message)s', filename="/var/log/openWB.log")
if os.environ.get("DEBUG") == "1":
   logging.basicConfig(level=logging.DEBUG)

infologgers = ['Adafruit_I2C.Device.Bus.1.Address.0X40', 'pymodbus']
for logger in infologgers:
   logging.getLogger(logger).setLevel(logging.INFO)

core = OpenWBCore.OpenWBCore().setup()

# Start the API
#api = api.OpenWBAPI(core)
#api.start()

Scheduler().run()
