import struct
from typing import List
import logging

from enum import Enum
from pymodbus.client import ModbusTcpClient


class SMAREGISTERS(Enum):
   #                      Name                         Datentyp   Unit     Gerätetyp
   DCA1 = 30769         # DC Kreis1 Ampere             [S32] FIX3 A        Inverter
   DCV1 = 30771         # DC Volt                      [S32] FIX2 V        Inverter
   DCW1 = 30773         # DC Power                     [S32] FIX0 W        Inverter
   DCA2 = 30957
   DCV2 = 30959
   DCW2 = 30961
   TotWhOut = 30529     # Gesamtertrag                 [U32] FIX0 Wh       Inverter
   WhIn = 30595         # Aufgenommene Energie         [U32] FIX0 Wh       Batt
   WhOut = 30597        # Abgegebene Energie            [U32] FIX0 Wh      Batt
   BatChaMaxW = 40795   # Maximale Batterieladeleistung [U32] FIX0 W    (Steuerobjekt) Batt
   BatDschMaxW = 40799  # Maximale Batterieentladeleistung [U32] FIX0 W (Steuerobjekt) Batt
   SOC = 30845          # Aktueller Ladezustand         [U32] FIX0 %       Batt
   P = 30775            # Leistung                      [S32] FIX0 W (>0: Laden)  alle

class WPMREGISTERS(Enum):
   Status = 2500
   
class HUAWEIREGISTERS(Enum):
   P = 32080   # Active power [I32] (W)
   F = 32085   # Grid frequency [U16] (1/100 Hz)
   DCU1 = 32016  # PV1 voltage [I16] (1/10 V)
   DCI1 = 32017  # PV1 current [I16] (1/100 A)
   DCU2 = 32018  # PV2 voltage [I16]
   DCI2 = 32019  # PV2 current [I16]
   # ...

class ModbusDevice:
   def __init__(self, ip: str, port:int = 502, unit:int = 1):
      self.client = ModbusTcpClient(ip, port=port)
      self.unit = unit

   def connect(self) -> None:
      self.client.connect()

   def disconnect(self) -> None:
      self.client.close()

   @property
   def connected(self) -> bool:
      return self.client.is_socket_open()

   def read(self, reg: Enum, count=2) -> List[int]:
      r = reg.value
      if 30000 <= r < 40000:
         method = self.client.read_holding_registers
         name = "holding"
      elif 40000 <= r < 50000:
         method = self.client.read_input_registers
         name = "input"
      return method(r, count=count, slave=self.unit).registers

   def read_holding(self, reg: Enum, count=2) -> List[int]:
      return self.client.read_holding_registers(reg.value, count=count, slave=self.unit).registers

   def write(self, reg: Enum, value: int) -> None:
      self.client.write_registers(reg, (value // 65536, value % 65536), slave=self.unit)

   def decode_s32(self, value: List[int]) -> int:
      if value[0] == 32768 and value[1] == 0:
          return 0
      return self.client.convert_from_registers(value, self.client.DATATYPE.INT32)

   def decode_u32(self, value: List[int]) -> int:
      if value[0] == 32768 and value[1] == 0:
          return 0
      return self.client.convert_from_registers(value, self.client.DATATYPE.UINT32)
