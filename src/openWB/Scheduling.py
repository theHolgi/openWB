import logging
import queue
from time import sleep

from openWB import DataPackage, Singleton
from fnmatch import fnmatch
from itertools import groupby
from threading import Thread


class Scheduler(Singleton):
   def __init__(self, simulated: bool = False):
      if "dataListener" not in vars(self):
         self.dataListener = {}   # Listeners are a mapping of pattern: [listeners]
         self.timeTable = {}      # Timetable is a mapping of  listener: time
         self.dataQueue = queue.Queue()
         if not simulated:
            self.dataRunner = Thread(target=self._dataQueue, daemon=True)
            self.dataRunner.start()
         self.logger = logging.getLogger()
         Scheduler.simulated = simulated           # Token for testing

   def registerData(self, pattern: str, listener) -> None:
      """
      Registers a callback for a data pattern.
      """
      if pattern in self.dataListener:
         self.dataListener[pattern].append(listener)
      else:
         self.dataListener[pattern] = [listener]

   def registerTimer(self, time: int, listener) -> None:
      """
      Registers a callback for regular scheduling.
      :param time:
      :param listener:
      :return:
      """
      self.timeTable[listener] = time

   def dataUpdate(self, data: DataPackage) -> None:
      """
      Announces that data has been updated.
      :param data: data Package
      :return:
      """
      self.dataQueue.put(data)

   def _dataQueue(self):
      # {'path/1': val, 'path/2': val2 }
      # -> [ (class1, 'path11', val1), ( class2, 'path2', val2)
      while True:
         sleep(1)
         data = {}
         while not self.dataQueue.empty():    # empty the queue
            data.update(self.dataQueue.get())
         self.logger.debug(f"Collected data: {data}")
         if data:
            recipients = [(l,k,v) for k, v in data.items() for pattern in self.dataListener.keys() for l in self.dataListener[pattern] if fnmatch(k, pattern)]
            for recipient, tuples in groupby(sorted(recipients, key=lambda tuple: id(tuple[0])), key=lambda tuple: tuple[0]):
               data = dict(tuple[1:] for tuple in tuples)
               recipient.dataUpdate(data)
         if self.simulated:
            return


   def run(self, simulated: bool = False) -> None:
      """
      run scheduled tasks regularly
      """
      delaysort = lambda delay: delay[0]
      timetable = list(sorted(((delay, task) for task, delay in self.timeTable.items()), key=delaysort))
      while True:
         delay, next_task = timetable.pop(0)
         if delay > 0 and not simulated:
            sleep(delay)
         next_task.loop()
         if len(timetable) == 0:
            break
         # Advance the timetable
         if delay > 0:
            timetable = [(d-delay, task) for d, task in timetable]
         # re-schedule the task
         reschedule = self.timeTable[next_task]
         if simulated:  # In simulation, do not reschedule beyond the end of list. This makes the loop stop after the slowest task has been run once.
            last = timetable[-1][0]
            if last < reschedule:
               continue
         timetable.append((reschedule, next_task))
         timetable.sort(key=delaysort)

   def test_callAll(self) -> None:
      """
      Call all scheduled tasks (for testing)
      """
      assert self.simulated, "call is only allowed in simulation mode."
      for task in self.timeTable.keys():
         task.loop()
