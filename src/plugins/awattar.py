from datetime import datetime, timedelta
from json import JSONDecoder
from typing import Optional, Iterable, List

from urllib3 import PoolManager


class Priceentry:
   def __init__(self, entry):
      self.start = datetime.fromtimestamp(entry.get('start_timestamp') / 1000)
      self.end = datetime.fromtimestamp(entry.get('end_timestamp') / 1000)
      self.price = entry.get('marketprice')

   def covers(self, timestamp: datetime) -> bool:
      """Tell if the entry is valid for the given timestamp"""
      return self.start <= timestamp <= self.end

   def in_range(self, span: timedelta) -> bool:
      """Tell if the entry is valid for the given delta time"""
      return self.covers(datetime.now() + span)

   def __repr__(self) -> str:
      return f"{self.price} ({self.start}...{self.end})"

   def __ge__(self, other) -> bool:
      return self.price >= other.price

   def __lt__(self, other) -> bool:
      return self.price < other.price


class Awattar:
   url = "https://api.awattar.de/v1/marketdata"

   def __init__(self):
      self.prices = []

   def refresh(self) -> None:
      http = PoolManager()
      r = http.request('GET', self.url)
      prices = JSONDecoder().decode(r.data.decode())
      self.prices = list(map(Priceentry, prices.get("data", [])))

   def getprice(self, timestamp: datetime) -> Optional[float]:
      try:
         price = (entry.price for entry in self.prices if entry.covers(timestamp))
         return price.__next__()
      except StopIteration:
         return None

   def cheapest_within(self, timestamp: datetime) -> List[Priceentry]:
      all_within = filter(lambda x: x.start <= timestamp, self.prices)
      return sorted(all_within)



