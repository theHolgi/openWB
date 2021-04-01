#!/usr/bin/python
from typing import List

from openWB.Modul import Speichermodul
from openWB.Scheduling import Scheduler
import struct
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.exceptions import ConnectionException
import sys


class SUNNYISLAND(Speichermodul):
   """SMA Smart home Meter (or Energy Meter)"""
   type = "speicher"

   def setup(self, config) -> None:
      self.ip = config.get(self.configprefix + '_ip')
      self.client = ModbusTcpClient(self.ip, port=502)
      if config.get(self.configprefix + '_bms') == "batrium":
         from .bms_batrium import BATRIUM
         self.bms = BATRIUM(1)
         self.bms.setup(self)
         self.bms.start()
      else:
         self.bms = None
      super().setup(config)
      Scheduler().registerTimer(10, self.loop)

   @staticmethod
   def decode_s32(value: List[int]) -> int:
      if value[0] == 32768 and value[1] == 0:
          return 0
      # To enforce signed decoding, there seems to be no better way.
      return struct.unpack('>i', bytes.fromhex(format(value[0], '04x') + format(value[1], '04x')))[0]

   @staticmethod
   def decode_u32(value: List[int]) -> int:
      if value[0] == 32768 and value[1] == 0:
          return 0
      return int(format(value[0], '04x') + format(value[1], '04x'), 16)

   def _readregister(self, reg: int, count=2) -> List[int]:
      return self.client.read_holding_registers(reg, count, unit=3).registers

   def loop(self):
      try:
         # state = self._readregister(30201)
         # 35 - Fehler
         # 303 - Aus
         # 307 - Ok
         # 455 - Warnung
         resp = self._readregister(30595, 4)
         data = {
           'kwhIn': self.decode_u32(resp[0:2]) / 1000,    # Aufgenommen [Wh]
           'kwhOut': self.decode_u32(resp[2:4]) / 1000     # Abgegeben   [Wh]
         }
         if self.bms is None or self.bms.timeout >= 10:
            data['soc'] = self.decode_u32(self._readregister(30845))        # SOC [%],
            data['W'] = -self.decode_s32(self._readregister(30775))  # Leistung [W] (>0: Laden)
         else:
            self.bms.timeout += 1
         self.send(data)
      except AttributeError:
         # modbus client seems to return (!) an ModbusIOExcption which is then tried to examine (resp.registers[])
         self.send({})
      except ConnectionException:
         self.send({'W': 0})
      except Exception as e:
         self.logger.exception("O-o, something really wrong!")
         sys.exit(1)   # TODO: Remove when it's running stable


def getClass():
   return SUNNYISLAND


