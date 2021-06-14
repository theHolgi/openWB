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
         resp = self.device.read(SMAREGISTERS.WhIn, 4)
         data = {
           'kwhIn': self.device.decode_u32(resp[0:2]) / 1000,    # Aufgenommen [Wh]
           'kwhOut': self.device.decode_u32(resp[2:4]) / 1000     # Abgegeben   [Wh]
         }
         if self.bms is not None:
            self.bms.timeout += 1
         if self.bms is None or self.bms.timeout >= 10:
            data['soc'] = self.device.decode_u32(self.device.read(SMAREGISTERS.SOC))
            data['W'] = -self.device.decode_s32(self.device.read(SMAREGISTERS.P))

         self.send(data)
      except (AttributeError, ConnectionException):
         # modbus client seems to return (!) an ModbusIOExcption which is then tried to examine (resp.registers[])
         pass

def getClass():
   return SUNNYISLAND


