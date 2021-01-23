import socket

from openWB import DataProvider, DataPackage
from .batriumdecoder import decode_batrium

class BATRIUM(DataProvider):
   """Batrium monitoring"""

   def setup(self, config):
      super().setup(config)

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
               'speicherleistung': parts['Ubat'] * parts['Ibat'],
               'speichersoc': parts['soc'],
               'speicher_umin': parts['Umin'],
               'speicher_umax': parts['Umax'],
               'speicher_tmin': parts['Tmin']
            }
            self.core.sendData(DataPackage(self, data))


def getClass():
   return BATRIUM
