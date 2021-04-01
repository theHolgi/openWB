#!/usr/bin/env python3
# coding=utf-8

# name | Offset |  unit | scale | offset
import struct

decoder = {
   ':2W,': [  # 5732 System Discovery Information
      ('Status',24, 'status', None, None),
      ('ok',    26, 'bool',   None, None),
      ('Umin',  31, 'uint16', 0.001, None),
      ('Umax',  33, 'uint16', 0.001, None),
      ('Uavg',  35, 'uint16', 0.001, None),
      ('Tmin',  37, 'uint8',    1, -40),
      ('soc',   41, 'uint8',  0.5, -5),
      ('Ubat',  42, 'uint16', 0.01, None),
      ('Ibat',  44, 'float', 0.001, None)
   ],
   ':>Z,': [  # 3E5A Telemetry - Combined Status Rapid Info
      ('Umin',  8, 'uint16', 0.001, None),
      ('Umax', 10, 'uint16', 0.001, None),
      ('Uavg', 28, 'uint16', 0.001, None),
      ('Tmin', 14, 'uint8', 1, -40),
      ('Tmax', 15, 'uint8', 1, -40),
      ('Tavg', 30, 'uint8', 1, -40),
      ('Ubat', 40, 'uint16', 0.01, None),
      ('Ibat', 42, 'float', 0.001, None)
   ],
   ':3?,': [  # 3F33 Telemetry - Combined Status Fast Info
      ('Umin', 13, 'uint16', 0.001, None),
      ('Umax', 15, 'uint16', 0.001, None),
      ('Tmin', 17, 'uint8', 1, -40),
      ('Tmax', 18, 'uint8', 1, -40),
      ('soc',  32, 'uint8', 0.5, -5),
      ('Tshunt',33, 'uint8', 1, -40),
      ('Usupp', 25, 'uint16', 0.01, None)
   ]
}


def decode_batrium(datagram: bytes, limit: str = None) -> dict:
   msg = {}
   id = datagram[0:4].decode()
   if id in decoder and (limit is None or limit == id):
      message = decoder[id]
      for key, pos, unit, scale, offset in message:
         if unit == 'bool':
            val = datagram[pos] != b'\x00'
         elif unit == 'uint8':
            val = int(datagram[pos])
         elif unit == 'uint16':
            val = int.from_bytes(datagram[pos:pos+2], byteorder='little')
         elif unit == 'float':
            val = struct.unpack('<f', datagram[pos:pos+4])[0]
         elif unit == 'status':
            val = { 0: 'timeout',
                    1: 'idle',
                    2: 'charging',
                    3: 'discharging',
                    4: 'full',
                    5: 'empty',
                    8: 'dunno',
                    10: 'strange'
                    }[datagram[pos]]
         if scale is not None:
            val = val * scale
         if offset is not None:
            val = val + offset
         msg[key] = val
   return msg
