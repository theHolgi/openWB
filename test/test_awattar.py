import unittest
from plugins.awattar import Awattar
from datetime import datetime, timedelta


class MyTestCase(unittest.TestCase):
   def test_something(self):
      awattar = Awattar()
      awattar.refresh()
      self.assertGreater(len(awattar.prices), 0)

      in_3_hours = datetime.now() + timedelta(hours=3)
      self.assertIsNotNone(awattar.getprice(in_3_hours), "Can tell a price for in 3 hours")
      cheapest = awattar.cheapest_within(in_3_hours)
      self.assertEqual(len(cheapest), 4, "Get 4 entries")
      self.assertLessEqual(cheapest[0], cheapest[1], "Entries are sorted")


if __name__ == '__main__':
   unittest.main()
