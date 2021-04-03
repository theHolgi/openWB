import struct
from typing import List

from enum import Enum
from pymodbus.client.sync import ModbusTcpClient


class SMAREGISTERS(Enum):
   #                      Name                         Datentyp   Unit     Gerätetyp
   DCA = 30769          # DC Ampere                    [S32] FIX3 A        Inverter
   DCV = 30771          # DC Volt                      [S32] FIX2 V        Inverter
   DCW = 30773          # DC Power                     [S32] FIX0 W        Inverter
   TotWhOut = 30529     # Gesamtertrag                 [U32] FIX0 Wh       Inverter
   WhIn = 30595         # Aufgenommene Energie         [U32] FIX0 Wh       Batt
   WhOut = 30597        # Abgegebene Energie            [U32] FIX0 Wh      Batt
   BatChaMaxW = 40795   # Maximale Batterieladeleistung [U32] FIX0 W    (Steuerobjekt) Batt
   BatDschMaxW = 40799  # Maximale Batterieentladeleistung [U32] FIX0 W (Steuerobjekt) Batt
   SOC = 30845          # Aktueller Ladezustand         [U32] FIX0 %       Batt
   P = 30775            # Leistung                      [S32] FIX0 W (>0: Laden)  alle


class ModbusDevice:
   def __init__(self, ip: str, port:int=502):
      self.client = ModbusTcpClient(ip, port=502)

   def read(self, reg: Enum, count=2) -> List[int]:
      return self.client.read_input_registers(reg.value, count, unit=3).registers

   def write(self, reg: Enum, value: int) -> None:
      self.client.write_registers(reg.value, (value // 65536, value % 65536), unit=3)

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
