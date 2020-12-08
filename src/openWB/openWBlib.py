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

import subprocess
import logging
from typing import Iterator, Any, Optional

basepath = '/var/www/html/openWB/'

class openWBconfig:
   """
   Represents openwb.conf
   behaves like a dictionary (non-existent settings return None)
   """
   def __init__(self, configfile: str = basepath + 'openwb.conf'):
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
   __getattr__ = __getitem__

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
   #__setattr__ = __setitem__

   def get(self, key, default=None):
      return self.settings.get(key, default)


class openWBValues(dict):
   """
   Represents openWB values dictionary
   behaves like a dictionary
   """
   def __init__(self):
      self.sumvalues = set(['pvwatt', 'llaktuell', 'ladestatus'])

   def update(self, data: "DataPackage"):
      if hasattr(data.source, 'multiinstance') and data.source.multiinstance:
         for (key, value) in data.items():
            self[key + str(data.source.id)] = value
#            self.sumvalues.add(key)
      else:
         for key, value in data.items():
            self[key] = value
      self.fast_derive_values(data)

   def __getattr__(self, key):
      return self[key] if key in self else 0

   def __setattr__(self, key, value):
      self[key] = value

   def get(self, key, id: Optional[int] = None, default=0) -> Any:
      """Returns the value or the given default, if not available"""
      if id is not None:
         key = key+str(id)
      return self[key] if key in self else default

   def get_all_phased(self, basename: str) -> Iterator:
      """Iterates basename<i> over phase i=1..3"""
      return (self[basename + str(phase)] for phase in range(1, 4))

   def fast_derive_values(self, data: "DataPackage"):
      """Immediately derive values from a new data package"""
      if 'evua1' in data:
         self.maxevu = max(data['evua' + str(phase)] for phase in range(1, 4))
         self.lowevu = min(data['evua' + str(phase)] for phase in range(1, 4))
         self.schieflast = self.maxevu - self.lowevu

   def derive_values(self):
      """Calculate derived values"""
      for key in self.sumvalues:
         sumVal = 0
         for instance in range(1, 10):
            value = self.get(key + str(instance))
            if value is None:
               break
            sumVal += int(value)
         self[key] = sumVal
      self.uberschuss = self.get('speicherleistung') - self.wattbezug
      self.hausverbrauch = self.wattbezug - self.pvwatt - self.get('llaktuell') - self.get('speicherleistung')

class ramdiskValues:
   """
   Represents the ramdisk of openWB
   behaves like a dictionary
   """
   def __init__(self, ramdiskpath = basepath + 'ramdisk/'):
      if ramdiskpath[-1] != '/':
         ramdiskpath += '/'
      self.cache = {}
      self.path = ramdiskpath
      self.sumvalues = set()

   def __getitem__(self, key):
      if key not in self.cache: self.cache[key] = self._get(key)
      return self.cache[key]
   #__getattr__ = __getitem__

   def __setitem__(self, key, value):
      self.cache[key] = value
      self._put(key, value)
   #__setattr__ = __setitem__

   def _get(self, name):
      """Get content of Ramdisk file <name>"""
      with open(self.path + name, 'r') as f:
         val = f.read()
         try:
            val = int(val)   # Try to convert to integer
         except ValueError:
            val = val.strip()
         return val

   def _put(self, name, content):
      """Put <content> into Ramdisk file <name>"""
      with open(self.path + name, 'w') as f:
         return f.write(str(content))


def log(message):
   logging.info(message)


def debug(message):
   if True or openWBconfig()['debug'] != 0:
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
