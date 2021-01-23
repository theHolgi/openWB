#!/usr/bin/python
import sys
import struct
from pymodbus.client.sync import ModbusTcpClient

class ModbusWR:
    """
    Read values from SMA inverter via Modbus
    In order to work, Modbus must be enabled.
    """
    def __init__(self, ip):
        self.host = ip

    def read(self):
        try:
            client = ModbusTcpClient(self.host, port=502, timeout=10)

            #pv watt
            resp = client.read_holding_registers(30775, 2, unit=3)  # Wirkleistung alle Außenleiter, S32 W
            # To enforce signed decoding, there seems to be no better way.
            all = bytes.fromhex(format(resp.registers[0], '04x') + format(resp.registers[1], '04x'))
            power = struct.unpack('>i', all)[0]
            if power < 0:
                power = 0
            power = -power

            #pv Wh
            resp = client.read_holding_registers(30529, 2, unit=3)  # Total AC power, U32 Wh
            all = format(resp.registers[0], '04x') + format(resp.registers[1], '04x')
            generation = int(all, 16)/1000
            return power, generation
        except:
            raise ConnectionError


if __name__ == '__main__':
   power, generation = ModbusWR(sys.argv[1]).read()
   print("Current power: %sW; Total generation: %.2fkWh" % (power, generation / 1000.0))
   
