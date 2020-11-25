#!/usr/bin/python

from openWB import DataProvider, DataPackage, Event, EventType
import struct
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.exceptions import ConnectionException

class SUNNYISLAND(DataProvider):
   """SMA Smart home Meter (or Energy Meter)"""
   type = "speicher"

   def setup(self, config) -> None:
      self.ip = config.get(self.configprefix + '_ip')
      self.client = ModbusTcpClient(self.ip, port=502)
      self.offsetikwh = 0
      self.offsetekwh = 0

   def _readregister(self, reg: int) -> int:
      resp = self.client.read_holding_registers(reg, 2, unit=3)

      all = bytes.fromhex(format(resp.registers[0], '04x') + format(resp.registers[1], '04x'))
      return struct.unpack('>i', all)[0]

   def trigger(self):
      try:
         soc = self._readregister(30845)
         charge = -self._readregister(30775)
         self.importkwh = self._readregister(30595)
         self.exportkwh = self._readregister(30597)
         self.core.sendData(DataPackage(self, {
           'speichersoc': soc,
           'speicherleistung': charge,
           'speicherikwh': self.importkwh - self.offsetikwh,
           'speicherekwh': self.exportkwh - self.offsetekwh
         }))
      except AttributeError:
         # modbus client seems to return (!) an ModbusIOExcption which is then tried to examine (resp.registers[])
         pass
      except ConnectionException:
         self.core.sendData(DataPackage(self, {'speicherleistung': 0}))

   def event(self, event: Event):
      if event.type == EventType.resetDaily:
         self.offsetikwh = self.importkwh
         self.offsetekwh = self.exportkwh


def getClass():
   return SUNNYISLAND


