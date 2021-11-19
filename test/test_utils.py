import unittest
from pathlib import Path
from utils import CsvLog


class Test_CsvLog(unittest.TestCase):
   testfile = Path('/tmp/xyz.csv')

   def setUp(self):
      if self.testfile.exists():
         self.testfile.unlink()

   def test_logging(self):
      with self.subTest('Create a new log'):
         log = CsvLog(self.testfile, (1, 2))
         self.assertFalse(log.keys, "Keys are empty")
         self.assertTrue(log.write(['x', 1, 2, 3, 4, 5]), "New entry is accepted")
         self.assertFalse(log.write(['x', 1, 2, 7, 8, 9]), "Another entry with same key is not accepted")
         self.assertTrue(log.has(1, 2), "Contains the new key")
         self.assertFalse(log.has(3, 5), "Does not contains another key")
         self.assertTrue(self.testfile.exists())
      del log
      with self.subTest('Read existing log'):
         log2 = CsvLog(self.testfile, (1, 2))
         self.assertTrue(log2.has(1, 2), "Contains the key already")


if __name__ == '__main__':
   unittest.main()
