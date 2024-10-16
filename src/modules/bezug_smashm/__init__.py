from openWB.Modul import EVUModul
from .speedwiredecoder import decode_speedwire
import socket
import struct
import threading
import logging

class SMASHM(EVUModul):
   """SMA Smart home Meter (or Energy Meter)"""

   def setup(self, config) -> None:
      self.serial = config.get(self.configprefix + '_serial')
      self.bind = config.get(self.configprefix + '_bind', '0.0.0.0')
      self.logger = logging.getLogger(self.__class__.__name__)
      super().setup(config)
      self.runner = threading.Thread(target=self.loop)
      self.runner.start()

   def loop(self):
      MCAST_GRP = '239.12.255.254'
      MCAST_PORT = 9522

      mapping = {'Hz': 'frequency'}
      phasemapping = {'A%i': {'from': 'i%i', 'sign': True},
                      'V%i': {'from': 'u%i'},
                      'Pf%i': {'from': 'cosphi%i'}
                      }
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
      sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      sock.bind(('', MCAST_PORT))
      try:
         mreq = struct.pack("4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton(self.bind))
         sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
      except BaseException:
         self.logger.warn('could not connect to mulicast group or bind to given interface')
         return
      self.logger.info("Bound to interface " + self.bind)
      # processing received messages
      while True:
         emparts = decode_speedwire(sock.recv(608))
         # Output...
         # don't know what P,Q and S means:
         # http://en.wikipedia.org/wiki/AC_power or http://de.wikipedia.org/wiki/Scheinleistung
         # thd = Total_Harmonic_Distortion http://de.wikipedia.org/wiki/Total_Harmonic_Distortion
         # cos phi is always positive, no matter what quadrant
         positive = [1] * 4
         if self.serial is None or self.serial == 'none' or str(emparts['serial']) == self.serial:
            # Special treatment for positive / negative power
            watt = int(emparts.get('pconsume',0))       # W
            if watt < 5:
               watt = -int(emparts.get('psupply', 0))
               positive[0] = -1
            data = {'W': watt,
                    'kwhOut': emparts.get('psupplycounter', 0),  # kWh
                    'kwhIn':  emparts.get('pconsumecounter', 0) # kWh
                    }
            for phase in [1, 2, 3]:
               power = int(emparts.get('p%iconsume' % phase, 0))
               if power < 5:
                  power = -int(emparts.get('p%isupply' % phase, 0))
                  positive[phase] = -1
               data['W%i' % phase] = power
            for key, pasemap in phasemapping.items():
               for phase in range(1, 4):
                  if pasemap['from'] % phase in emparts:
                     value = emparts[pasemap['from'] % phase]
                     if pasemap.get('sign'):
                        value *= positive[phase]
                     data[key % phase] = value
            for datakey, empartskey in mapping.items():
               if empartskey in emparts:
                  data[datakey] = emparts[empartskey]
            self.send(data)


def getClass():
   return SMASHM
