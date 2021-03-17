from collections import OrderedDict

from typing import Callable, Iterable, TypeVar, Mapping, List

import logging
import queue
from time import sleep

from openWB import DataPackage, Singleton
from openWB.Event import *
from fnmatch import fnmatch
from itertools import groupby
from threading import Thread

T = TypeVar('T')
V = TypeVar('V')


def add2key(d: Mapping[T, List[V]], key: T, value: V) -> None:
   if key in d:
      d[key].append(value)
   else:
      d[key] = [value]


class Scheduler(Singleton):
   def __init__(self, simulated: bool = False):
      if not hasattr(self, "dataListener"):
         self.dataListener = {}   # Listeners are a mapping of pattern: [listeners]
         self.timeTable = {}      # Timetable is a mapping of  listener: time
         self.eventListener = {}  # Event listeners are a mapping of Event: [listeners]
         self.dataQueue = queue.Queue()
         self.timerQueue = queue.Queue()
         if not simulated:
            self.dataRunner = Thread(target=self._dataQueue, daemon=True)
            self.dataRunner.start()
         self.logger = logging.getLogger()
         Scheduler.simulated = simulated           # Token for testing

   def registerData(self, patterns: Iterable[str], listener: object) -> None:
      """
      Registers a callback for a data pattern.
      :param patterns: data path pattern, e.g. "pv/*"
      :param listener: object that implements:
      - newdata(data) -> signal new data
      - priority      -> execution priority
      """
      for pattern in patterns:
         add2key(self.dataListener, pattern, listener)

   def unregisterData(self, listener) -> None:
      """Unregister from Data update events"""
      for pattern, listeners in self.dataListener.items():
         if listener in listeners:
            listeners.remove(listener)
            if len(listeners) == 0:
               del self.dataListener[pattern]

   def registerTimer(self, time: int, listener: Callable[[], None]) -> None:
      """
      Registers a callback for regular scheduling.
      :param time: scheduling time in seconds
      :param listener: a callback
      :return:
      """
      self.timeTable[listener] = time
      self.timerQueue.put(listener)

   def unregisterTimer(self, listener: Callable[[], None]) -> None:
      """
      Unregister listener from Timer events
      """
      del self.timeTable[listener]

   def registerEvent(self, event: EventType, listener: Callable[[OpenWBEvent], None]) -> None:
      """
      Registers a callback for an event.
      :param event: Event to listen on
      :param listener: callback function
      """
      add2key(self.eventListener, event, listener)

   def dataUpdate(self, data: DataPackage) -> None:
      """
      Announces that data has been updated.
      :param data: data Package
      """
      self.dataQueue.put(data)

   def _dataQueue(self):
      # {'path/1': val, 'path/2': val2 }
      # -> [ (class1, 'path11', val1), ( class2, 'path2', val2)
      notifylist = OrderedDict()
      queuedata = dict(self.dataQueue.get(block=True))  # Wait until an element becomes available.
      while True:
         while not self.dataQueue.empty():  # empty the queue
            queuedata.update(self.dataQueue.get())
         if queuedata:
            self.logger.debug(f"Collected data: {queuedata}")
            recipients = [(l,k,v) for k, v in queuedata.items() for pattern in self.dataListener.keys() for l in self.dataListener[pattern] if fnmatch(k, pattern)]
            for recipient, tuples in groupby(sorted(recipients, key=lambda tuple: tuple[0].priority), key=lambda tuple: tuple[0]):
               data = dict(tuple[1:] for tuple in tuples)
               priority = recipient.priority
               if priority in notifylist:
                  notifylist[priority][1].update(data)
               else:
                  notifylist[priority] = (recipient, data)
            queuedata = {}
            # now, execute the first element
         elif notifylist:
            recipient, data = notifylist.pop(next(notifylist.keys().__iter__()))
            self.logger.debug(f"Data trigger: {recipient} with {data}")
            recipient.newdata(data)
         elif self.simulated:   # During simulation, quit when no activity any more.
            return
         else:
            queuedata.update(self.dataQueue.get(block=True))
#         sleep(1)

   def run(self, simulated: bool = False) -> None:
      """
      run scheduled tasks regularly
      """
      delaysort = lambda delay: delay[0]
      timetable = []
      while True:
         while not self.timerQueue.empty():  # Check for new elements
            listener = self.timerQueue.get()
            timetable.append((self.timeTable[listener], listener))
         timetable.sort(key=delaysort)
         delay, next_task = timetable.pop(0)
         if delay > 0 and not simulated:
            sleep(delay)
         if next_task not in self.timeTable:    # check if the task has not been removed from the timetable meanwhile
            continue
         self.logger.debug(f"Calling: {next_task}")
         next_task()
         if len(timetable) == 0:
            break
         # Advance the timetable
         if delay > 0:
            timetable = [(d-delay, task) for d, task in timetable]
         # re-schedule the task
         reschedule = self.timeTable.get(next_task)
         if reschedule is None:  # Might have been removed meanwhile
            continue
         if simulated:  # In simulation, do not reschedule beyond the end of list. This makes the loop stop after the slowest task has been run once.
            last = timetable[-1][0]
            if last < reschedule:
               continue
         timetable.append((reschedule, next_task))

   def test_callAll(self, n: int = 1) -> None:
      """
      Call all scheduled tasks (for testing)
      """
      assert self.simulated, "call is only allowed in simulation mode."
      for i in range(n):
         for task in self.timeTable.keys():
            task()
         self._dataQueue()

   def signalEvent(self, event: OpenWBEvent) -> None:
      """signals an event"""
      if event.type in self.eventListener:
         for callback in self.eventListener[event.type]:
            callback(event)
