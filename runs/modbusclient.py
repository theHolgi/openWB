#!/usr/bin/python3

from pymodbus.client import ModbusTcpClient
import struct
import argparse
import time


def readregister(client, reg: int, unit: int, length: int) -> int:
   client.connect()
   # time.sleep(10)
   if 10000 <= reg < 20000:
      method = client.read_coils
   elif 30000 <= reg <= 40000:
      method = client.read_input_registers
   elif 40000 <= reg <= 50000:
      method = client.read_holding_registers
   else:
      raise ValueError("Invalid register " + str(reg))
   method = client.read_holding_registers
   resp = method(reg, count=length, slave=unit)
   print(f"Read: {resp}")

   all = bytes.fromhex(format(resp.registers[0], '04x') + format(resp.registers[1], '04x'))
   return struct.unpack('>i', all)[0]

parser = argparse.ArgumentParser()
parser.add_argument('host', type=str)
parser.add_argument('register', type=int)
parser.add_argument('-l', '--length', type=int, default=2)
parser.add_argument('-u', '--unit', type=int, default=1)

args = parser.parse_args()

client = ModbusTcpClient(args.host, port=502)

print("%i = %i" %(args.register, readregister(client, args.register, args.unit, args.length)))
