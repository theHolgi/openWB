#!/usr/bin/python
#####
#
# File: openWBlib.py
#
# Copyright 2020 Holger Lamm
#
#  This file is part of openWB.
#
#     openWB is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     openWB is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with openWB.  If not, see <https://www.gnu.org/licenses/>.
#
#####
import shelve
import subprocess
import logging
from typing import Iterator, Any, Optional
from . import Singleton
from .Scheduling import Scheduler

basepath = '/var/www/html/openWB/'


class OpenWBconfig(Singleton):
   """
   Represents openwb.conf
   behaves like a dictionary (non-existent settings return None)
   """
   def __init__(self, configfile: str = basepath + 'openwb.conf'):
      if not hasattr(self, 'settings'):
         self.settings = {}
         self.configfile = configfile
         try:
            with open(configfile, 'r') as f:
               for line in f.readlines():
                  if line[0] == '#' or line[0] == '\n':
                     continue
                  key, value = line.split('=')
                  if value[:2] == "0x":
                     value = int(value, 16)
                  else:
                     try:
                        value = int(value)   # Try to convert to integer
                     except ValueError:
                        value = value.strip()
                  self.settings[key] = value
         except IOError:
            pass

   def __getitem__(self, key):
      return self.settings.get(key)

   def __setitem__(self, key, value):
      import re
      if isinstance(value, bool):   # convert bool -> 0/1
         value = 1 if value else 0
      self.settings[key] = value
      log("Config: %s = %s" % (key, value))
      try:
         with open(self.configfile, 'r') as f:
            content = f.read()
      except IOError:
         content = ""

      line = "%s=%s" % (key, value)
      if re.search(f'^{key}=', content, re.MULTILINE):
         content = re.sub(f'^{key}=.*', line, content, flags=re.MULTILINE)
      else:
         content += line + '\n'
      with open(self.configfile, 'w') as f:
         f.write(content)

   def get(self, key, default=None):
      return self.settings.get(key, default)

config = None
def getConfig() -> OpenWBconfig:
   if config is None:
      config = OpenWBconfig()
   return config


class openWBValues(object):
   """
   Represents openWB values dictionary
   behaves like a dictionary

   Glossar daten:
   EVU:
      evu/W
      evu/WhExported
      evu/WhImported
      evu/APhase*
      evu/VPhase*
      evu/WPhase*
      evu/PfPhase*
      evu/Hz
      evu/DailyYieldImportKwh
      evu/DailyYieldExportKwh
      evu/MonthlyYieldImportKwh
      evu/MonthlyYieldExportKwh
   PV:
      pv/W
      pv/WhCounter
      pv/DailyYieldKwh
      pv/MonthlyYieldKwh
   Batterie:
      housebattery/boolHouseBatteryConfigured
      housebattery/W
      housebattery/%Soc
      housebattery/WhImported
      housebattery/WhExported
      housebattery/DailyYieldExportKwh
      housebattery/DailyYieldImportKwh
      housebattery/MonthlyYieldExportKwh
      housebattery/MonthlyYieldImportKwh
   LP:
      lp/%i/boolChargePointConfigured
      lp/%i/ChargePointEnabled
      lp/%i/AConfigured    - sollwert
      lp/%i/VPhase*
      lp/%i/APhase*
      lp/%i/PfPhase*
      lp/%i/countPhasesInUse
      lp/%i/W
      lp/%i/kwh
      lp/%i/DailyKwh
      lp/%i/boolPlugStat
      lp/%i/boolChargeStat
      lp/%i/kWhChargedSincePlugged
      lp/%i/kWhActualCharged
      lp/%i/TimeRemaining           [str] Rest Ladezeit

      lp/WhCounter
      lp/DailyYieldKwh
   Global:
      global/WAllChargePoints
      global/uberschuss
      global/WHouseConsumption
   """
   def __new__(cls, *args, **kwargs):
      """ Create a new instance
      """
      if '_inst' not in vars(cls):
         cls._inst = object.__new__(cls)
         cls._inst.val = dict()
      return cls._inst

   def __init__(self):
      self.sumvalues = set(['llaktuell', 'llkwh', 'daily_llkwh', 'ladestatus'])

   def update(self, data: "DataPackage") -> None:
      self.val.update(data)
      Scheduler().dataUpdate(data)

   def __getitem__(self, key):
      return self.val[key] if key in self.val else 0

   def __setitem__(self, key, value):
      self.val[key] = value

   def get(self, key, default: Any = 0, id: Optional[int] = None, ) -> Any:
      """Returns the value or the given default, if not available"""
      if id is not None:
         key = key+str(id)
      return self.val[key] if key in self.val else default

   def get_all_phased(self, basename: str) -> Iterator:
      """Iterates basename<i> over phase i=1..3"""
      return (self.val.get(basename + str(phase)) for phase in range(1, 4))

   def sum(self, pattern: str) -> int:
      """Summiere Daten aus pattern auf"""
      summe = 0
      i = 1
      while True:
         name = pattern % i
         if name not in self.val:
            return summe
         summe += self.get(name)
         i += 1

class RamdiskValues(Singleton):
   """
   Represents the ramdisk of openWB
   behaves like a dictionary
   """
   def __init__(self, ramdiskpath: str = basepath + 'ramdisk/'):
      if ramdiskpath[-1] != '/':
         ramdiskpath += '/'
      self.cache = {}
      self.shelf = shelve.open(ramdiskpath + 'values.db')
      self.path = ramdiskpath
      self.sumvalues = set()

   def __getitem__(self, key):
      if key not in self.cache:
         self.cache[key] = self._get(key)
      return self.cache[key]
   #__getattr__ = __getitem__

   def __setitem__(self, key, value):
      self.cache[key] = value
      self._put(key, value)
   #__setattr__ = __setitem__

   def _get(self, name):
      """Get content of Ramdisk file <name>"""
      if name in self.shelf:
         return self.shelf[name]
      try:
         with open(self.path + name, 'r') as f:
            val = f.read()
            val = float(val)   # Try to convert to float
      except ValueError:
         val = val.strip()
      except OSError:
         return None
      return val

   def _put(self, name, content):
      """Put <content> into Ramdisk file <name>"""
      self.shelf[name] = content
      with open(self.path + name, 'w') as f:
         return f.write(str(content))


def log(message):
   logging.info(message)


def debug(message):
   if True or OpenWBconfig()['debug'] != 0:
      logging.debug(message)

def setCurrent(req):
   """
   set requested current
   valid keys:
   - all
   - lp<n>
   """
   mapping = { 'all': 'all', 'lp1': 'm', 'lp2': 's1', 'lp3': 's2'}  # remap the key for set-current.sh
   if req is None: return
   for key, current in req.iteritems():
      cmd = './runs/set-current.sh %s %s'  % (current, mapping[key])
      debug("Exec: " + cmd)
      subprocess.call(cmd, shell=True)
