import os
import sys
import importlib

mypath = os.path.dirname(os.path.realpath(__file__)) + '/'

sys.path.append(mypath + 'site_python')

from openWB.openWBlib import *
from openWB import *
from openWB.OpenWBCore import OpenWBCore
global core

config = openWBconfig(mypath + 'pyconfig.conf')
core = OpenWBCore(mypath)

for source in ['wr', 'bezug', 'lp']:
   instance = 1
   while True:
      modulename = config[source + 'modul' + str(instance)]
      if modulename is None:
         break
      module = importlib.import_module('modules.%s_%s' % (source, modulename))
      cls = module.getClass()
      core.add_module(cls(instance))
      instance += 1

core.run()
