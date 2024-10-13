#!/usr/bin/python3

from pymodbus.client.sync import ModbusTcpClient
import struct
import argparse

def readregister(client, reg: int, unit: int, length: int) -> int:
      resp = client.read_holding_registers(reg, length, unit=unit)

      all = bytes.fromhex(format(resp.registers[0], '04x') + format(resp.registers[1], '04x'))
      return struct.unpack('>i', all)[0]

parser = argparse.ArgumentParser()
parser.add_argument('host', type=str)
parser.add_argument('register', type=int)
parser.add_argument('-l', '--length', type=int, default=2)
parser.add_argument('-u', '--unit', type=int, default=1)

args = parser.parse_args()

client = ModbusTcpClient(args.host, port=502, unit=args.unit)

print("%i = %i" %(register, readregister(client, args.register, args.unit, args.length)))
