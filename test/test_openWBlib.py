import os
import unittest

from openWB.openWBlib import openWBconfig, ramdiskValues


class TestWBlib(unittest.TestCase):
   def test_config(self):
      testfile = '/tmp/openwb.conf'
      try:
         os.remove(testfile)
      except OSError:
         pass
      config = openWBconfig(testfile)
      self.assertIsNone(config['test'])
      config['evseids1'] = 1
      config['evselanips1'] = "10.20.0.180"

      self.assertEqual(config['evseids1'], 1)
      self.assertEqual(config['evselanips1'], "10.20.0.180", "Getting a non-integer setting")

      # Read it another time
      config2 = openWBconfig(testfile)
      self.assertEqual(config2['evseids1'], 1)
      self.assertEqual(config2['evselanips1'], "10.20.0.180", "Getting a non-integer setting")

   def test_values(self):
      values = ramdiskValues('/tmp')
      values['test'] = 'test'
      values['test2'] = 5
      self.assertTrue(os.path.isfile('/tmp/test'))
      self.assertTrue(os.path.isfile('/tmp/test2'))
      values2 = ramdiskValues('/tmp')
      self.assertEqual(values2['test'],  'test', "Retrieve a string value")
      self.assertEqual(values2['test2'], 5)

if __name__ == '__main__':
    unittest.main()
