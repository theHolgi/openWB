import asyncio
from pymodbus.client.tcp import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

# Konfigurationsdaten
IP = "stiebel.garnix.de"   # Deine IP
PORT = 502
SLAVE_ID = 1
REGISTER_ADDR = 506    # Außentemperatur = Register 507 laut Doku → -1 Offset

async def main():
    async with AsyncModbusTcpClient(IP, PORT) as client:
        try:
            result = await client.read_input_registers(REGISTER_ADDR, count=1, slave=SLAVE_ID)
            if result.isError():
                print(f"Modbus-Fehler: {result}")
            else:
                raw = result.registers[0]
                value = raw / 10.0  # z. B. 85 → 8.5 °C
                print(f"Außentemperatur: {value:.1f} °C")
        except ModbusException as ex:
            print(f"Modbus-Ausnahme: {ex}")

# Hauptfunktion ausführen
asyncio.run(main())
