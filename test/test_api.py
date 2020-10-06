import unittest
from openWB import api

class StubCore:
   config = {'sampleconfig': 'configvalue'}
   data = {'sampledata': 'datavalue'}

class MyTestCase(unittest.TestCase):
   def setUp(self):
      self.core = StubCore()

   def test_something(self):
      handler = api.OpenWBAPI(self.core)
      handler.start()
      handler.join()

if __name__ == '__main__':
   unittest.main()
