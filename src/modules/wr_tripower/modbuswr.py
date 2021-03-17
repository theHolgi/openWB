#!/usr/bin/python
import sys
import struct
from typing import List
from pymodbus.client.sync import ModbusTcpClient
import logging

class ModbusWR:
    """
    Read values from SMA inverter via Modbus
    In order to work, Modbus must be enabled.
    """
    def __init__(self, ip, instances: int):
        self.host = ip
        self.client = ModbusTcpClient(self.host, port=502, timeout=20)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _readregister(self, reg: int, count=2) -> List[int]:
        return self.client.read_holding_registers(reg, count, unit=3).registers

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

    def read(self):
#        try:
            #pv watt
            power = self.decode_s32(self._readregister(30775, 2)) # Wirkleistung alle Außenleiter, S32 W
            if power < 0:
                power = 0

            #pv Wh
            generation = self.decode_u32(self._readregister(30529, 2)) / 1000  # Total AC power, U32 [Wh]

            # DCA, S32[mA] / DCU, S32[0.01V] / DCW, S32[W]
            resp = self._readregister(30769, 6)
            dca = self.decode_s32(resp[0:2]) / 1000
            dcu = self.decode_s32(resp[2:4]) / 100
            dcp = self.decode_s32(resp[4:6])
            self.logger.info(f"DCA: {dca} DCU: {dcu} DCP: {dcp}")

            return power, generation
#        except:
#            raise ConnectionError


if __name__ == '__main__':
   power, generation = ModbusWR(sys.argv[1]).read()
   print("Current power: %sW; Total generation: %.2fkWh" % (power, generation / 1000.0))
   
