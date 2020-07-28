#!/usr/bin/python3
#  MBTechWorks.com 2016
#  Pulse Width Modulation (PWM) demo to cycle brightness of an LED

import Adafruit_PCA9685 as Ada
import time

pwm = Ada.PCA9685(address=0x40)
pwm.set_pwm_freq(100)

ch_grid = 0
ch_pv   = 1
ch_green = 15
ch_red   = 14

# pwm.set_pwm(ch_green, 0, )
# pwm.set_pwm(ch_red, 0, 4095)

ramdisk = "/var/www/html/openWB/ramdisk/"

def readfile(fileName):
    with open(ramdisk + fileName) as f:
        content = f.read()
    try:
        result = int(content)
        return result
    except ValueError:
        return 0

def scale(channel, val) -> int:
    table = { 'pv':   {     0: 0, 2000: 850, 4000: 1760, 6000: 2680, 8000: 3420, 9500: 4095 },
              'grid': { -2000: 0,    0: 850, 2000: 1760, 4000: 2580, 6000: 3420, 7500: 4095}
            }
    t = table[channel]
    last_x = None
    for x,y in t.items():
       if x > val:
          if last_x is None:
             return y
          else:
             return last_y + int((val - last_x) * (y - last_y) / (x - last_x))
       last_y = y
       last_x = x
    return last_y

last = {'pv': 0, 'grid': 0, 'green': 0, 'red': 0}
def run(emparts, config):
      global last
      pvwatt = -readfile("pvwatt")
      bezug  = -emparts["pconsume"]
      if bezug > -5:
          bezug = emparts["psupply"]

      red = (bezug > 6400)
      green = readfile("ladestatus") != 0      
      pvdc = 0
      bezugdc = 0
      
      log = ""
      try:
        if abs(last['pv'] - pvwatt) > 100:
          pvdc    = scale('pv', pvwatt)
          pwm.set_pwm(ch_pv, 0, pvdc)
          last['pv'] = pvwatt
          log += "PV: %dw = %.2f" % (pvwatt, pvdc/4095)
        else:
          log += "PV: %dw = ----" % pvwatt
        if abs(last['grid'] - bezug) > 100:
          bezugdc = scale('grid', bezug)
          pwm.set_pwm(ch_grid, 0, bezugdc)
          last['grid'] = bezug
          log += " Grid: %dw = %.2f" % (bezug, bezugdc/4095)
        else:
          log += " Grid: %dw = ----" % bezug
  
        if red:
          log += " R"
        if green:
          log += " G"

        if last['red'] != red:
          last['red'] = red
          print("Red changed to %s" % red)
          pwm.set_pwm(ch_red, 0, 4095 if red else 0)

        if last['green'] != green:
          last['green'] = green
          print("Green changed to %s" % green)
          pwm.set_pwm(ch_green, 0, 4095 if green else 0)
      except OSError:
        pass
      if config['verbose'] == '1':
        print (log)

def stopping(emparts, config):
    pass
def config(config):
    pass
