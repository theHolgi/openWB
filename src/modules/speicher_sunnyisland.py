#!/usr/bin/python

from openWB.Modul import Speichermodul
import struct
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.exceptions import ConnectionException


class SUNNYISLAND(Speichermodul):
   """SMA Smart home Meter (or Energy Meter)"""
   type = "speicher"

   def setup(self, config) -> None:
      self.ip = config.get(self.configprefix + '_ip')
      self.client = ModbusTcpClient(self.ip, port=502)
      if config.get(self.configprefix + '_bms') == "batrium":
         from .bms_batrium import BATRIUM
         self.bms = BATRIUM(1)
         self.bms.setup(config)
         self.bms.start()
      else:
         self.bms = None
      super().setup()

   def _readregister(self, reg: int) -> int:
      resp = self.client.read_holding_registers(reg, 2, unit=3)

      all = bytes.fromhex(format(resp.registers[0], '04x') + format(resp.registers[1], '04x'))
      return struct.unpack('>i', all)[0]

   def loop(self):
      try:
         # state = self._readregister(30201)
         # 35 - Fehler
         # 303 - Aus
         # 307 - Ok
         # 455 - Warnung
         data = {
           'speicherikwh': self._readregister(30595) / 1000,    # Aufgenommen [Wh]
           'speicherekwh': self._readregister(30597) / 1000     # Abgegeben   [Wh]
         }
         if self.bms is None:
            data['speichersoc'] = self._readregister(30845),  # SOC [%],
            data['speicherleistung'] = -self._readregister(30775),  # Leistung [W] (>0: Laden)
         self.send(data)
      except AttributeError:
         # modbus client seems to return (!) an ModbusIOExcption which is then tried to examine (resp.registers[])
         self.send({})
      except ConnectionException:
         self.send({'speicherleistung': 0})


def getClass():
   return SUNNYISLAND


