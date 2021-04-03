#!/usr/bin/python

from openWB.Modul import Speichermodul
from openWB.Scheduling import Scheduler
from pymodbus.exceptions import ConnectionException
from .modbusDevice import ModbusDevice, SMAREGISTERS


class SUNNYISLAND(Speichermodul):
   """SMA Smart home Meter (or Energy Meter)"""
   type = "speicher"

   def setup(self, config) -> None:
      self.ip = config.get(self.configprefix + '_ip')
      self.device = ModbusDevice(self.ip)
      if config.get(self.configprefix + '_bms') == "batrium":
         from .bms_batrium import BATRIUM
         self.bms = BATRIUM(1)
         self.bms.setup(self)
         self.bms.start()
      else:
         self.bms = None
      super().setup(config)
      Scheduler().registerTimer(10, self.loop)


   def loop(self):
      try:
         # state = self._readregister(30201)
         # 35 - Fehler
         # 303 - Aus
         # 307 - Ok
         # 455 - Warnung
         resp = self.device.read(SMAREGISTERS.WhIn, 4)
         data = {
           'kwhIn': self.device.decode_u32(resp[0:2]) / 1000,    # Aufgenommen [Wh]
           'kwhOut': self.device.decode_u32(resp[2:4]) / 1000     # Abgegeben   [Wh]
         }
         # Schreibe:
         # 40795 - Maximale Batterieladeleistung (U32)
         self.device.write(SMAREGISTERS.BatChaMaxW, 500)
         self.device.write(SMAREGISTERS.BatDschMaxW, 5000)
         # 40799 - Maximale Batterieentladeleistung (U32)
         if self.bms is None or self.bms.timeout >= 10:
            data['soc'] = self.device.decode_u32(self.device.read(SMAREGISTERS.SOC))
            data['W'] = -self.device.decode_s32(self.device.read(SMAREGISTERS.P))

            self.bms.timeout += 1
         self.send(data)
      except (AttributeError, ConnectionException):
         # modbus client seems to return (!) an ModbusIOExcption which is then tried to examine (resp.registers[])
         raise ConnectionError


def getClass():
   return SUNNYISLAND


