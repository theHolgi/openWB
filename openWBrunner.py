#!/usr/bin/python3
import os
import sys
import importlib

mypath = os.path.dirname(os.path.realpath(__file__)) + '/'

sys.path.append(mypath + 'site_python')

from src.openWB.openWBlib import *
from src.openWB import *
from src.openWB import OpenWBCore
global core

if 'http_proxy' in os.environ:
   os.environ.pop('http_proxy')
if 'https_proxy' in os.environ:
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
