#!/usr/bin/python
import sys
import unittest
import subprocess

basepath = '/var/www/html/openWB/'


def openWBconfig(configfile = basepath + 'openwb.conf'):
   """Return openWB.config"""
   settings = {}
   with open(configfile, 'r') as f:
      for line in f.readlines():
         key, value = line.split('=')
         try:
            value = int(value)   # Try to convert to integer
         except ValueError:
            value = value.strip()
         settings[key] = value
   return settings

class openWBValues:
   """
   Represents the ramdisk of openWB
   behaves like a dictionary
   """
   def __init__(self, ramdiskpath = basepath + 'ramdisk/'):
      if ramdiskpath[-1] != '/': ramdiskpath += '/'
      self.cache = {}
      self.path  = ramdiskpath
   def __getitem__(self, key):
      if key not in self.cache: self.cache[key] = self._get(key)
      return self.cache[key]
   def __setitem__(self, key, value):
      self.cache[key] = value
      self._put(key, value)

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
   print(message)


def debug(message):
   if openWBconfig()['debug'] == 1 or True:
      print(message)

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

class TestWBlib(unittest.TestCase):
   def test_config(self):
      config = openWBconfig('openwb.conf')
      self.assertEqual(config['evseids1'], 1)
      self.assertEqual(config['evselanips1'], "10.20.0.180", "Getting a non-integer setting")

   def test_values(self):
      import os
      values = openWBValues('/tmp')
      values['test'] = 'test'
      values['test2'] = 5
      self.assertTrue(os.path.isfile('/tmp/test'))
      self.assertTrue(os.path.isfile('/tmp/test2'))
      values2 = openWBValues('/tmp')
      self.assertEqual(values2['test'],  'test', "Retrieve a string value")
      self.assertEqual(values2['test2'], 5)

if __name__ == '__main__':
    unittest.main()
