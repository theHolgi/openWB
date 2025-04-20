#!/usr/bin/python

from ..modbusDevice import ModbusDevice, HUAWEIREGISTERS
import logging
import time

class ModbusWR:
    """
    Read values from SMA inverter via Modbus
    In order to work, Modbus must be enabled.
    """
    def __init__(self, ip, instance: int = 1):
        self.host = ip
        self.device = ModbusDevice(self.host, unit=instance)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

    def read(self):
        try:
            # pv watt
            self.device.connect()
            regs = self.device.read(HUAWEIREGISTERS.P)
            self.device.disconnect()
            power = self.device.decode_s32(regs)
            if power < 0:
                power = 0

            # pv Wh
            # generation = self.device.decode_u32(self.device.read_holding(self.REG_TotWh)) / 1000  # Total AC power, U32 [Wh]
            generation = 0


            return power, generation

        except AttributeError:
            raise ConnectionError
