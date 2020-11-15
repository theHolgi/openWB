#!/usr/bin/python

from openWB import DataProvider, DataPackage
import struct
from pymodbus.client.sync import ModbusTcpClient


class SUNNYISLAND(DataProvider):
   """SMA Smart home Meter (or Energy Meter)"""

   def setup(self, config) -> None:
      self.ip = config.get(self.configprefix + '_ip')
      self.client = ModbusTcpClient(self.ip, port=502)

   def _readregister(self, reg: int) -> int:
      resp = self.client.read_holding_registers(reg, 2, unit=3)

      value1 = resp.registers[0]
      value2 = resp.registers[1]
      all = format(value1, '04x') + format(value2, '04x')
      return int(struct.unpack('>i', all.decode('hex'))[0])

   def trigger(self):
      soc = self._readregister(30845)
      charge = -self._readregister(30775)
      importkwh = self._readregister(30595)
      exportkwh = self._readregister(30597)
      self.core.sendData(DataPackage(self, {'speichersoc': soc,
                                            'speicherleistung': charge,
                                            'speicherikwh': importkwh,
                                            'speicherekwh': exportkwh}))
