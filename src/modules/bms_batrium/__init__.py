import socket

from openWB.Modul import DataProvider, DataPackage, Speichermodul
from .batriumdecoder import decode_batrium

class BATRIUM(DataProvider):
   """Batrium monitoring"""

   def setup(self, master: Speichermodul):
      self.master = master
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

def getClass():
   return BATRIUM
