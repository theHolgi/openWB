#!/usr/bin/python3
import logging
import os
import sys

mypath = os.path.dirname(os.path.realpath(__file__)) + '/'
sys.path.append(mypath + 'src')

from openWB import OpenWBCore, api
from openWB.Scheduling import Scheduler
from openWB.startup import init_system

if 'http_proxy' in os.environ:
   os.environ.pop('http_proxy')
if 'https_proxy' in os.environ:
   os.environ.pop('https_proxy')

level = logging.DEBUG if os.environ.get("DEBUG") == "1" else logging.INFO
logging.basicConfig(level=level, format='%(asctime)-15s %(message)s', filename="/var/log/openWB.log")

infologgers = ['Adafruit_I2C.Device.Bus.1.Address.0X40', 'pymodbus']
for logger in infologgers:
   logging.getLogger(logger).setLevel(logging.INFO)

init_system()
core = OpenWBCore.OpenWBCore().setup()

# Start the API
#api = api.OpenWBAPI(core)
#api.start()

Scheduler().run()
