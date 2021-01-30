from time import sleep
from typing import Callable, Tuple, List

from openWB import DataPackage, Singleton
from fnmatch import fnmatch
from itertools import groupby

class Scheduler(Singleton):
   def __init__(self):
      if "dataListener" not in vars(self):
         self.dataListener = {}   # Listeners are a mapping of pattern: [listeners]
         self.timeTable = {}      # Timetable is a mapping of  listener: time
         self.dataQueue = []

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
      # {'path/1': val, 'path/2': val2 }
      # -> [ (class1, 'path11', val1), ( class2, 'path2', val2)
      recipients = [(l,k,v) for k, v in data.items() for pattern in self.dataListener.keys() for l in self.dataListener[pattern] if fnmatch(k, pattern)]
      for recipient, tuples in groupby(sorted(recipients, key=lambda tuple: id(tuple[0])), key=lambda tuple: tuple[0]):
         data = dict(tuple[1:] for tuple in tuples)
         recipient.dataUpdate(data)


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
         if simulated:  # In simulation, do not rescheduling beyond the end of list. This makes the loop stop after the slowest task has been run once.
            last = timetable[-1][0]
            if last < reschedule: continue
         timetable.append((reschedule, next_task))
         timetable.sort(key=delaysort)
