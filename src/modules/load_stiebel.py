from openWB.Modul import DataProvider
from modules.modbusDevice import ModbusDevice, WPMREGISTERS
from pymodbus.exceptions import ConnectionException
from openWB.Scheduling import Scheduler


class STIEBEL(DataProvider):
	def setup(self, config) -> None:
		self.ip = config.get(self.configprefix + '_ip')
		self.device = ModbusDevice(self.ip)
		super().setup(config)
		Scheduler().registerTimer(10, self.loop)


def loop(self):
	try:
		resp = self.device.read(WPMREGISTERS.Status, 1)
		data = {
		}
		self.send(data)
	except (AttributeError, ConnectionException):
		# modbus client seems to return (!) an ModbusIOExcption which is then tried to examine (resp.registers[])
		pass


def getClass():
	return STIEBEL

