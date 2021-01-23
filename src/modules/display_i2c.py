#!/usr/bin/python3
#  MBTechWorks.com 2016
#  Pulse Width Modulation (PWM) demo to cycle brightness of an LED

from openWB.Modul import Displaymodul
import Adafruit_PCA9685 as Ada
import threading
import time

ch_grid = 15
ch_pv = 13
ch_batt = 14
ch_green = 7
ch_red = 6

ON = 4095
OFF = 0

class I2CDISPLAY(Displaymodul):
   """Display-Modul via I2C"""

   def setup(self, config):
      self.pwm = Ada.PCA9685(address=config.get(self.configprefix + '_address'))
      self.pwm.set_pwm_freq(100)
      self.last = {'pv': 0, 'grid': -1000, 'batt': -1000, 'green': 0, 'red': 0}

   def blink(self, port):
      t = threading.currentThread()
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
   def scale(channel, val) -> int:
      table = {'pv': {0: 0, 500: 840, 1000: 1750, 2000: 2600, 4000: 3450, 7000: 4095},
               'grid': {-2000: 0, -1000: 850, 0: 1730, 1000: 2600, 2000: 3400, 3600: 4095},
               'batt': {-1000: 0, -500: 800, 0: 1700, 500: 2570, 1000: 3450, 1600: 4095}
               }
      t = table[channel]
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

   def loop(self):
      pvwatt = -self.core.data.get('pvwatt')
      uberschuss = -self.core.data.get('wattbezug')
      charging = self.core.data.get('speicherleistung')

      red = (uberschuss > 6400)
      if uberschuss < -50 and pvwatt > 1000:
         red = "blink"
      green = self.core.data.get('ladestatus') != 0
      if green and self.core.data.get('llaktuell') == 0:
         green = "blink"

      log = ""
      try:
         if abs(self.last['pv'] - pvwatt) > 100:
            pvdc = self.scale('pv', pvwatt)
            self.pwm.set_pwm(ch_pv, 0, pvdc)
            self.last['pv'] = pvwatt
            log += "PV: %dw = %.2f" % (pvwatt, pvdc / 4095)
         else:
            log += "PV: %dw = ----" % pvwatt
         if abs(self.last['grid'] - uberschuss) > 100:
            bezugdc = self.scale('grid', uberschuss)
            self.pwm.set_pwm(ch_grid, 0, bezugdc)
            self.last['grid'] = uberschuss
            log += " Grid: %dw = %.2f" % (uberschuss, bezugdc / 4095)
         else:
            log += " Grid: %dw = ----" % uberschuss

         if abs(self.last['batt'] - charging) > 100:
            chargedc = self.scale('batt', charging)
            self.pwm.set_pwm(ch_batt, 0, chargedc)
            self.last['batt'] = charging
            log += " Batt: %dw = %.2f" % (charging, chargedc / 4095)
         else:
            log += " Batt: %dw = ----" % charging

         if red == "blink":
            log += " r"
         elif red:
            log += " R"
         if green:
            log += " G"

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
