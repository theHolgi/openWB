from pymodbus.client import ModbusTcpClient
from pymodbus.client import Client
from pymodbus.exceptions import ModbusException

# Konfigurationsdaten
IP = "stiebel.garnix.de"   # <- anpassen!
PORT = 502
SLAVE_ID = 1
REGISTER_ADDR = 506    # Dokumentiertes Register 507 → Offset -1

# Client erstellen
client = ModbusTcpClient(host=IP, port=PORT)

async def main():
    async with client:
        try:
            # Asynchrones Lesen der Input Register
            result = await client.read_input_registers(REGISTER_ADDR, count=1, slave=SLAVE_ID)
            if result.isError():
                print(f"Modbus-Fehler: {result}")
            else:
                raw = result.registers[0]
                value = raw / 10.0
                print(f"Außentemperatur: {value:.1f} °C")
        except ModbusException as ex:
            print(f"Modbus-Ausnahme: {ex}")

# asyncio-Loop starten
import asyncio
asyncio.run(main())
