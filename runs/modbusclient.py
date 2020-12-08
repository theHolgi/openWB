#!/usr/bin/python3

import sys
from pymodbus.client.sync import ModbusTcpClient
import struct

host = sys.argv[1]
register = int(sys.argv[2])

def readregister(client, reg: int) -> int:
      resp = client.read_holding_registers(reg, 2, unit=3)

      all = bytes.fromhex(format(resp.registers[0], '04x') + format(resp.registers[1], '04x'))
      return struct.unpack('>i', all)[0]

client = ModbusTcpClient(host, port=502)

print("%i = %i" %(register, readregister(client, register)))
