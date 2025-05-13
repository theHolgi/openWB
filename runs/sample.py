import asyncio
from pymodbus.client.tcp import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

# Konfiguration
IP = "stiebel.garnix.de"   # <== Anpassen!
PORT = 502
SLAVE_ID = 1
REGISTER_ADDR = 506    # Außentemperatur laut Doku (507) → -1 wegen Offset

async def main():
    async with AsyncModbusTcpClient(host=IP, port=PORT) as client:
        try:
            result = await client.read_input_registers(REGISTER_ADDR, count=1, slave=SLAVE_ID)
            if result.isError():
                print(f"Modbus-Fehler: {result}")
            else:
                raw = result.registers[0]
                temperature = raw / 10.0  # Umrechnung von z. B. 85 → 8.5 °C
                print(f"Außentemperatur: {temperature:.1f} °C")
        except ModbusException as ex:
            print(f"Modbus-Ausnahme: {ex}")

# Event Loop starten
asyncio.run(main())
