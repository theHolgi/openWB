#!/usr/bin/python

import sys
from ..modbusDevice import SMAREGISTERS, ModbusDevice
import logging


class ModbusWR:
    """
    Read values from SMA inverter via Modbus
    In order to work, Modbus must be enabled.
    """
    def __init__(self, ip, instances: int):
        self.host = ip
        self.device = ModbusDevice(self.host, unit=3)
        self.logger = logging.getLogger(self.__class__.__name__)

    def read(self):
        try:
            # pv watt
            power = self.device.decode_s32(self.device.read(SMAREGISTERS.P))
            if power < 0:
                power = 0

            # pv Wh
            generation = self.device.decode_u32(self.device.read(SMAREGISTERS.TotWhOut)) / 1000  # Total AC power, U32 [Wh]

            # DCA, S32[mA] / DCU, S32[0.01V] / DCW, S32[W]
            resp = self.device.read(SMAREGISTERS.DCA1, 6)
            dca = self.device.decode_s32(resp[0:2]) / 1000
            dcu = self.device.decode_s32(resp[2:4]) / 100
            dcp = self.device.decode_s32(resp[4:6])
            # self.logger.info(f"DCA: {dca} DCU: {dcu} DCP: {dcp}")

            return power, generation
        except AttributeError:
            raise ConnectionError


if __name__ == '__main__':
   power, generation = ModbusWR(sys.argv[1]).read()
   print("Current power: %sW; Total generation: %.2fkWh" % (power, generation / 1000.0))
   
