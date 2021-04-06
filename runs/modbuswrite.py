#!/usr/bin/python3

import sys
from pymodbus.client.sync import ModbusTcpClient
import struct

host = sys.argv[1]
register = int(sys.argv[2])
value = int(sys.argv[3])

def enc_u32(value) -> list:
  v = []
  for n in range(2):
     v.insert(0, value % 65536)
     value = value // 65536
  return v

client = ModbusTcpClient(host, port=502)
client.connect()

print("%i = %s" % (register, str(enc_u32(value))))
print(client.write_registers(register, enc_u32(value), unit=3))

