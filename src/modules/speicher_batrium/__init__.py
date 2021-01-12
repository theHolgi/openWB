import socket

from openWB import Speichermodul
from .batriumdecoder import decode_batrium

class BATRIUM(Speichermodul):
   """Batrium monitoring"""

   def setup(self, config):
      super().setup(config)

   def loop(self):
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
               'batt_umin': parts['Umin'],
               'batt_umax': parts['Umax'],
               'batt_tmin': parts['Tmin'],
               'batt_soc':  parts['soc']
            }
            self.send(data)


def getClass():
   return BATRIUM
