#!/usr/bin/python3
#  MBTechWorks.com 2016
#  Pulse Width Modulation (PWM) demo to cycle brightness of an LED

from openWB.Modul import Displaymodul
import board
import busio
import adafruit_pca9685 as adafruit
import threading
import time

from openWB.Scheduling import Scheduler
from openWB.openWBlib import openWBValues

ch_grid = 15
ch_pv = 13
ch_batt = 14
ch_green = 7
ch_red = 6

ON = 0xffff
OFF = 0

PMAX = 8000  # Maximale Wirkleistung für rote LED

table = {'pv':   {    0: 0,       500: 14700, 1000: 29500, 2000: 43000, 4000: 57500, 6000: 0xffff},
         'grid': {-3600: 0xffff,-2000: 54500,-1000: 42000,    0: 28000, 1000: 14000, 2000: 0},
         'batt': {-1000: 0,      -500: 12500,    0: 27000,  500: 41000, 1000: 55000, 1800: 0xffff}
        }

mapping = {
   'pv/W': (ch_pv, 'pv'),
   'housebattery/W': (ch_batt, 'batt'),
   'evu/W': (ch_grid, 'grid')
}

class I2CDISPLAY(Displaymodul):
   """Display-Modul via I2C"""
   priority = 1000   # Display has lowest data dependency priority

   def setup(self, config):
      i2c = busio.I2C(board.SCL, board.SDA)
      self.pwm = adafruit.PCA9685(i2c, address=config.get(self.configprefix + '_address'), )
      self.pwm.frequency = 100
      self.last = {'pv': 0, 'grid': -1000, 'batt': -1000, 'green': 0, 'red': 0}
      Scheduler().registerData(mapping.keys(), self)
      Scheduler().registerTimer(10, self.leds)

   def blink(self, port: int) -> None:
      t = threading.currentThread()
      t.do_run = True
      state = ON
      while t.do_run:
         try:
            self.pwm.channels[port].duty_cycle = state
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
      try:
         for key, values in mapping.items():
            if key in updated:
               channel, name = values
               value = updated[key]
               if abs(value - self.last[name]) > 100:
                  dc = self.scale(table[name], value)
                  self.last[name] = value
                  self.pwm.channels[channel].duty_cycle = dc
      except OSError:
         pass

   def leds(self):
      data = openWBValues()
      red = data.get('evu/W') < -PMAX
      if data.get('evu/W') > 50 and data.get('pv/W') > 1000:
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
               self.pwm.channels[ch_red].duty_cycle = ON if red else OFF
            self.last['red'] = red

         if self.last['green'] != green:
            if self.last['green'] == "blink":
               self.last['green_blink'].do_run = False
            if green == "blink":
               self.last['green_blink'] = threading.Thread(target=self.blink, args=(ch_green,))
               self.last['green_blink'].start()
            else:
               self.pwm.channels[ch_green].duty_cycle = ON if green else OFF
            self.last['green'] = green
      except OSError:
         pass


def getClass():
   return I2CDISPLAY
