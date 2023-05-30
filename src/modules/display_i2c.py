#!/usr/bin/python3
#  MBTechWorks.com 2016
#  Pulse Width Modulation (PWM) demo to cycle brightness of an LED

from openWB.Modul import Displaymodul
import Adafruit_PCA9685 as Ada
import threading
import time
import logging

from openWB.Scheduling import Scheduler
from openWB.openWBlib import openWBValues
from typing import Callable, TypeVar

ch_grid = 15
ch_pv = 12
ch_batt = 14
ch_soc = 13
ch_green = 7
ch_red = 6

ON = 4095
OFF = 0

PMAX = 8000  # Maximale Wirkleistung für rote LED

table = {'pv':   {    0: 0,      500: 920,   1000: 1800,2000: 2600, 4000: 3450, 7000: 4095},
         'soc':  {    0: 0,       20: 880,     40: 1730,  60: 2600,   80: 3450,   95: 4095},
         'grid': {-3600: 4095, -2000: 3400, -1000: 2600,   0: 1730, 1000:  850, 2000: 0},
         'batt': {-1000: 0,     -500: 800,      0: 1700, 500: 2570, 1000: 3450, 1600: 4095}
         }

mapping = {
   'pv/W': (ch_pv, 'pv'),
   'housebattery/W': (ch_batt, 'batt'),
   'housebattery/%Soc': (ch_soc, 'soc'),
   'evu/W': (ch_grid, 'grid')
}

T = TypeVar('T')

def retry_i2c(callable: Callable[[], T]) -> T:
   while True:
      try:
         return callable()
      except OSError:
         time.sleep(1)
         continue

class I2CDISPLAY(Displaymodul):
   """Display-Modul via I2C"""
   priority = 1000   # Display has lowest data dependency priority

   def setup(self, config):
      self.pwm = retry_i2c(lambda: Ada.PCA9685(address=config.get(self.configprefix + '_address')))
      retry_i2c(lambda: self.pwm.set_pwm_freq(100))
      self.last = {'pv': 0, 'soc': 0, 'grid': -1000, 'batt': -1000, 'green': 0, 'red': 0}
      Scheduler().registerData(mapping.keys(), self)
      Scheduler().registerTimer(10, self.leds)

   def blink(self, port: int) -> None:
      t = threading.current_thread()
      t.do_run = True
      state = ON
      while t.do_run:
         try:
            self.pwm.set_pwm(port, 0, state)
         except OSError:
            pass
         time.sleep(1)
         state = ON - state

   @staticmethod
   def scale(t: dict, val: int) -> int:
      last_x = None
      for x, y in t.items():
         if x > val:
            if last_x is None:
               return y
            else:
               return last_y + int((val - last_x) * (y - last_y) / (x - last_x))
         last_y = y
         last_x = x
      return last_y

   def newdata(self, updated: dict):
      for key, values in mapping.items():
         if key in updated:
            channel, name = values
            value = updated[key]
            threshold = 1 if (name == 'soc') else 100
            if abs(value - self.last[name]) > threshold:
               dc = self.scale(table[name], value)
               try:
                  self.pwm.set_pwm(channel, 0, dc)
                  logging.info("Successfully set %s to %i (%i)" % (name, value, dc))
                  self.last[name] = value
               except OSError:
                  pass

   def leds(self):
      data = openWBValues()
      red = data.get('evu/W') < -PMAX
      if data.get('evu/W') > 50 and data.get('pv/W') > 1000:
         red = "blink"
      if data.get('lp/1/Error') or data.get('housebattery/1/Error'):
         red = "blink"

      green = data.get('lp/ChargeStat') != 0
      if green and data.get('global/WAllChargePoints') == 0:
         green = "blink"

      try:
         if self.last['red'] != red:
            if self.last['red'] == "blink":
               self.last['red_blink'].do_run = False
            if red == "blink":
               self.last['red_blink'] = threading.Thread(target=self.blink, args=(ch_red,))
               self.last['red_blink'].start()
            else:
               self.pwm.set_pwm(ch_red, 0, ON if red else OFF)
            self.last['red'] = red

         if self.last['green'] != green:
            if self.last['green'] == "blink":
               self.last['green_blink'].do_run = False
            if green == "blink":
               self.last['green_blink'] = threading.Thread(target=self.blink, args=(ch_green,))
               self.last['green_blink'].start()
            else:
               self.pwm.set_pwm(ch_green, 0, ON if green else OFF)
            self.last['green'] = green
      except OSError:
         pass


def getClass():
   return I2CDISPLAY
