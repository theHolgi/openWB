import unittest
from plugins.awattar import Awattar, Priceentry
from datetime import datetime, timedelta, time

from utils import tomorrow_at_6


class MyTestCase(unittest.TestCase):
   def test_fetching(self):
      awattar = Awattar()
      awattar.refresh()
      self.assertGreater(len(awattar.prices), 0)

      in_3_hours = datetime.now() + timedelta(hours=3)
      self.assertIsNotNone(awattar.getprice(in_3_hours), "Can tell a price for in 3 hours")
      cheapest = awattar.cheapest_within(in_3_hours)
      self.assertEqual(len(cheapest), 4, "Get 4 entries")
      self.assertLessEqual(cheapest[0], cheapest[1], "Entries are sorted")

   def test_ranging(self):
      awattar = Awattar()
      awattar.prices = [Priceentry({'start_timestamp': 1670446800000, 'end_timestamp': 1670450400000, 'marketprice': 200.72, 'unit': 'Eur/MWh'}),
                        Priceentry({'start_timestamp': 1670450400000, 'end_timestamp': 1670454000000, 'marketprice': 280.56, 'unit': 'Eur/MWh'}),
                        Priceentry({'start_timestamp': 1670454000000, 'end_timestamp': 1670457600000, 'marketprice': 286.56, 'unit': 'Eur/MWh'}),
                        Priceentry({'start_timestamp': 1670457600000, 'end_timestamp': 1670461200000, 'marketprice': 280.78, 'unit': 'Eur/MWh'}),
                        Priceentry({'start_timestamp': 1670461200000, 'end_timestamp': 1670464800000, 'marketprice': 269.67, 'unit': 'Eur/MWh'}),
                        Priceentry({'start_timestamp': 1670464800000, 'end_timestamp': 1670468400000, 'marketprice': 369.91, 'unit': 'Eur/MWh'}),
                        Priceentry({'start_timestamp': 1670565600000, 'end_timestamp': 1670569200000, 'marketprice': 100.49, 'unit': 'Eur/MWh'})]
      awattar.new_prices = True
      until = datetime.fromtimestamp(1670472000)
      self.assertTrue(awattar.charge_now(3, until,
                                         now=datetime.fromtimestamp(1670446800)), "Charging in cheapest interval")
      self.assertTrue(awattar.charge_now(3, until,
                                         now=datetime.fromtimestamp(1670461200)), "Charging in 2nd cheapest interval")
      self.assertTrue(awattar.charge_now(3, until,
                                         now=datetime.fromtimestamp(1670450400)), "Charging in 3rd cheapest interval")
      self.assertFalse(awattar.charge_now(3, until,
                                         now=datetime.fromtimestamp(1670565600)), "Not Charging in 4th cheapest interval")

      self.assertEqual(awattar.get_pricechart(), "22:00,20.07\n23:00,28.06\n00:00,28.66\n01:00,28.08\n"
                       + "02:00,26.97\n03:00,36.99\n07:00,10.05")

      cheapest = awattar.cheapest_within(until)[:3]
      cheapest.sort(key=lambda x: x.start)
      self.assertEqual(cheapest, [])

if __name__ == '__main__':
   unittest.main()
