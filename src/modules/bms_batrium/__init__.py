import socket

from openWB.Modul import DataProvider, DataPackage, Speichermodul
from openWB.openWBlib import openWBValues
from pathlib import Path
from .batriumdecoder import decode_batrium
from datetime import datetime
from utils import CsvLog

datalogging = True


class BATRIUM(DataProvider):
   """Batrium monitoring"""

   def setup(self, master: Speichermodul):
      self.master = master
      self.timeout = 0
      if datalogging:
         self.data = CsvLog(Path('/tmp/batrium.csv'), (1, 2))

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
               if not self.data.has(p, chargestate):
                  for id, values in parts['cells'].items():
                     self.data.write([datetime.now().strftime("%d.%m.%y %X"), p, chargestate, id,
                                      round(values['Umin'], 3), round(values['Umax'], 3),
                                      values['Tmax'],
                                      values['Status']])


def getClass():
   return BATRIUM
