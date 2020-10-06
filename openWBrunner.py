#!/usr/bin/python3
import os
import sys
import importlib

mypath = os.path.dirname(os.path.realpath(__file__)) + '/'
sys.path.append(mypath + 'src')

from openWB import OpenWBCore, api

if 'http_proxy' in os.environ:
   os.environ.pop('http_proxy')
if 'https_proxy' in os.environ:
   os.environ.pop('https_proxy')

core = OpenWBCore.OpenWBCore(mypath + "/pyconfig.conf")

# Start the API
api = api.OpenWBAPI(core)
api.start()

for source in ['wr', 'bezug', 'lp']:
   instance = 1
   while True:
      prefix = source + 'modul' + str(instance)
      modulename = core.config[prefix]
      if modulename is None:
         break
      module = importlib.import_module('modules.%s_%s' % (source, modulename))
      cls = module.getClass()
      core.add_module(cls(instance), prefix)
      instance += 1

core.run()
