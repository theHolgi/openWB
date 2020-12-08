from openWB import *
from .speedwiredecoder import decode_speedwire
import socket
import struct

class SMASHM(DataProvider):
   """SMA Smart home Meter (or Energy Meter)"""

   def setup(self, config) -> None:
      self.serial = config.get(self.configprefix + '_serial')
      self.bezugkwh = 0
      self.einspeisungkwh = 0
      self.offsetikwh = 0
      self.offsetekwh = 0

   def trigger(self):
      ipbind = '0.0.0.0'
      MCAST_GRP = '239.12.255.254'
      MCAST_PORT = 9522

      #                filename:  channel
      mapping = {'evuhz': 'frequency'}
      phasemapping = {'evua%i': {'from': 'i%i', 'sign': True},
                      'evuv%i': {'from': 'u%i'},
                      'evupf%i': {'from': 'cosphi%i'}
                      }
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
      sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      sock.bind(('', MCAST_PORT))
      try:
         mreq = struct.pack("4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton(ipbind))
         sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
      except BaseException:
         self.core.logging.warn('could not connect to mulicast group or bind to given interface')
         return
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
            data = DataPackage(self)
            watt = int(emparts['pconsume'])       # W
            if watt < 5:
               watt = -int(emparts['psupply'])
               positive[0] = -1
            data['wattbezug'] = watt
            self.bezugkwh = emparts['pconsumecounter']       # kWh
            self.einspeisungkwh = emparts['psupplycounter']  # kWh
            data['einspeisungkwh'] = self.einspeisungkwh
            data['bezugkwh'] = self.bezugkwh
            data['daily_einspeisungkwh'] = (self.einspeisungkwh - self.offsetekwh)
            data['daily_bezugkwh'] = (self.bezugkwh - self.offsetikwh)
            # print("Bezug: %i Einspeisung: %i" % (emparts['pconsume'], emparts['psupply']))
            for phase in [1, 2, 3]:
               power = int(emparts['p%iconsume' % phase])
               if power < 5:
                  power = -int(emparts['p%isupply' % phase])
                  positive[phase] = -1
               data['bezugw%i' % phase] = power
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
            self.core.sendData(data)
            break

   def event(self, event: Event):
      if event.type == EventType.resetDaily:
         self.offsetikwh = self.bezugkwh
         self.offsetekwh = self.einspeisungkwh

def getClass():
   return SMASHM
