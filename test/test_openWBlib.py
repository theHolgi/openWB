import os
import unittest

from openWB.openWBlib import OpenWBconfig, RamdiskValues


class TestConfig(unittest.TestCase):
   testfile = '/tmp/openwb.conf'
   def setUp(self):
      try:
         os.remove(self.testfile)
      except OSError:
         pass

   def test_config(self):
      config = OpenWBconfig(self.testfile)
      self.assertIsNone(config['test'])
      config['evseids1'] = 1
      config['evselanips1'] = "10.20.0.180"

      self.assertEqual(config['evseids1'], 1)
      self.assertEqual(config['evselanips1'], "10.20.0.180", "Getting a non-integer setting")

      # Read it another time
      config2 = OpenWBconfig(self.testfile)
      self.assertEqual(config2['evseids1'], 1)
      self.assertEqual(config2['evselanips1'], "10.20.0.180", "Getting a non-integer setting")
   def test_default(self):
      config = OpenWBconfig(self.testfile)
      self.assertEqual(config.get("offsetpvpeak"), 6500, "Shall return the default")
      self.assertEqual(config.get("offsetpvpeak", 200), 200, "Given default has precedence over global default")


class TestWBlib(unittest.TestCase):
   def test_values(self):
      values = RamdiskValues('/tmp')
      values['test'] = 'test'
      values['test2'] = 5
      self.assertTrue(os.path.isfile('/tmp/test'))
      self.assertTrue(os.path.isfile('/tmp/test2'))
      values2 = RamdiskValues('/tmp')
      self.assertEqual(values2['test'],  'test', "Retrieve a string value")
      self.assertEqual(values2['test2'], 5)

if __name__ == '__main__':
    unittest.main()
