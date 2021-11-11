import socket

from openWB.Modul import DataProvider, DataPackage, Speichermodul
from openWB.openWBlib import openWBValues
from .batriumdecoder import decode_batrium
from datetime import datetime

datalogging = True


class BATRIUM(DataProvider):
   """Batrium monitoring"""

   def setup(self, master: Speichermodul):
      self.master = master
      self.timeout = 0
      if datalogging:
         self.data = open('/tmp/batrium.csv', 'a')
         self.logged_chargestates = {}

   def run(self):
      BCASTPORT = 18542

      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
      sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      sock.bind(('', BCASTPORT))

      # processing received messages
      while True:
         packet = sock.recv(1024)
         parts = decode_batrium(packet, ':2W,')
         if parts:
            data = {
               'W': parts['Ubat'] * parts['Ibat'],
               'soc': parts['soc'],
               'Umin': parts['Umin'],
               'Umax': parts['Umax'],
               'Tmin': parts['Tmin']
            }
            self.master.send(data)
            self.timeout = 0
         if datalogging:
            parts = decode_batrium(packet, ':ZA,')
            if parts:
               data = openWBValues()
               p = int(round(data.get('housebattery/W'), -2))
               chargestate = int(data.get('housebattery/%Soc'))
               key = chargestate, p
               if key not in self.logged_chargestates:  # not yet logged this combination P/%soc
                  self.logged_chargestates[key] = True
                  for id, values in parts['cells'].items():
                     self.data.write(','.join(map(str, [datetime.now().strftime("%y-%m-%d %X"), p, chargestate,
                                                        id, values['Umin'], values['Umax'], values['Tmax'], values['Status']])) + '\n')


def getClass():
   return BATRIUM
