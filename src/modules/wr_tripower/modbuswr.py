#!/usr/bin/python
import sys
import struct
from typing import List
from pymodbus.client.sync import ModbusTcpClient

class ModbusWR:
    """
    Read values from SMA inverter via Modbus
    In order to work, Modbus must be enabled.
    """
    def __init__(self, ip):
        self.host = ip
        self.client = ModbusTcpClient(self.host, port=502, timeout=10)


    @staticmethod
    def decode_s32(value: List[int]) -> int:
       # To enforce signed decoding, there seems to be no better way.
       all = bytes.fromhex(format(value[0], '04x') + format(value[1], '04x'))
       return struct.unpack('>i', all)[0]

    @staticmethod
    def decode_u32(value: List[int]) -> int:
       all = format(resp.registers[0], '04x') + format(resp.registers[1], '04x')
       return int(all, 16)

    def read(self):
        try:
            #pv watt
            resp = self.client.read_holding_registers(30775, 2, unit=3)  # Wirkleistung alle Außenleiter, S32 W
            power = self.decode_s32(resp.registers)
            if power < 0:
                power = 0
            power = -power

            #pv Wh
            resp = self.client.read_holding_registers(30529, 6, unit=3)  # Total AC power, U32 [Wh]
            generation = self.decode_u32(resp.registers) / 1000

            # DCA, S32[mA] / DCU, S32[0.01V] / DCW, S32[W]
            resp = self.client.read_holding_registers(30769, 6, unit=3)
            dca = self.decode_s32(resp.registers[0:1]) / 1000
            dcu = self.decode_s32(resp.registers[2:3]) / 100
            dcp = self.decode_s32(resp.registers[4:5])
            self.logging.info(f"DCA: {dca} DCU: {dcu} DCP: {dcp}")

            return {'pvwatt': power, 'pvkwh': generation}
        except:
            raise ConnectionError


if __name__ == '__main__':
   power, generation = ModbusWR(sys.argv[1]).read()
   print("Current power: %sW; Total generation: %.2fkWh" % (power, generation / 1000.0))
   
