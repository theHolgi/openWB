#!/usr/bin/python

from ..modbusDevice import ModbusDevice
import logging

class ModbusWR:
    """
    Read values from SMA inverter via Modbus
    In order to work, Modbus must be enabled.
    """
    def __init__(self, ip, instances: int):
        self.host = ip
        self.device = ModbusDevice(self.host, unit=1)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device.connect()

    def read(self):
        try:
            # pv watt
            power = self.device.decode_s32(self.device.read_holding(self.REG_P))
            if power < 0:
                power = 0

            # pv Wh
            # generation = self.device.decode_u32(self.device.read_holding(self.REG_TotWh)) / 1000  # Total AC power, U32 [Wh]
            generation = 0


            return power, generation

        except AttributeError:
            raise ConnectionError
