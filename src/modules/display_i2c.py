#!/usr/bin/python3
#  MBTechWorks.com 2016
#  Pulse Width Modulation (PWM) demo to cycle brightness of an LED

from openWB import Displaymodul
import Adafruit_PCA9685 as Ada
import threading
import time

ch_grid = 0
ch_pv = 1
ch_green = 15
ch_red = 14

ON = 4095
OFF = 0

class I2CDISPLAY(Displaymodul):
   """Display-Modul via I2C"""

   def setup(self, config):
      self.pwm = Ada.PCA9685(address=config.get(self.configprefix + '_address'))
      self.pwm.set_pwm_freq(100)
      self.last = {'pv': 0, 'grid': 0, 'green': 0, 'red': 0}

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
      table = {'pv': {0: 0, 2000: 850, 4000: 1760, 6000: 2680, 8000: 3420, 9500: 4095},
               'grid': {-2000: 0, 0: 850, 2000: 1760, 4000: 2580, 6000: 3420, 7500: 4095}
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


   def trigger(self):
      pvwatt = -self.core.data.get('pvwatt')
      uberschuss = -self.core.data.get('wattbezug')

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
