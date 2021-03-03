#!/usr/bin/python3
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

core = OpenWBCore.OpenWBCore().setup()

# Start the API
#api = api.OpenWBAPI(core)
#api.start()

Scheduler().run()
