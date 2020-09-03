#!/usr/bin/python3
import os
import sys
import importlib

mypath = os.path.dirname(os.path.realpath(__file__)) + '/'

sys.path.append(mypath + 'site_python')

from openWB.openWBlib import *
from openWB import *
from openWB.OpenWBCore import OpenWBCore
global core

os.environ.pop('http_proxy')
os.environ.pop('https_proxy')

core = OpenWBCore(mypath + "/pyconfig.conf")

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
