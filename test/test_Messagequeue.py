from queue import Queue
from time import sleep

import threading


class Consumer(threading.Thread):
   def __init__(self):
      super().__init__()
      self.queue = queue
      self.lock = threading.Event()
      self.data = None

   def newdata(self, data: int) -> None:
      self.data = data
      self.lock.set()

   def run(self):
      #      logger = logging.getLogger(self.__class__.__name__)
      while True:
         self.lock.wait()
         print(self.data)
         sleep(1)


class Producer(threading.Thread):
   def __init__(self, consumer: Consumer):
      super().__init__()
      self.consumer = consumer

   def run(self):
      i = 0
      while True:
         self.consumer.newdata(i)
         i += 1
         sleep(0.1)


queue = Queue()

q = Consumer()
p = Producer(q)
p.start()
q.start()

p.join()
q.join()

