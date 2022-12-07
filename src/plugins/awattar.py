import logging
from math import ceil
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
      self.cache = {}

   def refresh(self) -> None:
      http = PoolManager()
      r = http.request('GET', self.url)
      prices = JSONDecoder().decode(r.data.decode())
      self.prices = sorted(list(map(Priceentry, prices.get("data", []))))
      self.cache = {}

   def getprice(self, timestamp: datetime) -> Optional[float]:
      try:
         price = (entry.price for entry in self.prices if entry.covers(timestamp))
         return price.__next__()
      except StopIteration:
         return None

   def cheapest_within(self, timestamp: datetime) -> List[Priceentry]:
      return list(filter(lambda x: x.start <= timestamp, self.prices))

   def charge_now(self, hours_to_charge: int, until: datetime, now: datetime = datetime.now()) -> bool:
      """ Tell if we need to charge now, when <required> kwh with <power> charging power is required until <until>"""
      if (hours_to_charge, until) in self.cache:
         cheapest_hours = self.cache.get((hours_to_charge, until))
      else:
         cheapest_hours = self.cheapest_within(until)[:hours_to_charge]
         self.cache[(hours_to_charge, until)] = cheapest_hours
         logging.info(f"AWATTAR: Charging in the intervals {cheapest_hours}")
      return any(elem.covers(now) for elem in cheapest_hours)
