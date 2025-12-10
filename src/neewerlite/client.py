import asyncio
from bleak import BleakClient
from . import protocol
from .exceptions import ConnectionError

class NeewerLight:
    def __init__(self, address: str):
        self.address = address
        self.client = None

    async def connect(self, timeout: float = 10.0):
        """
        Connects to the light and performs the required handshake.
        Raises ConnectionError if failed.
        """
        print(f"Connecting to {self.address}...")
        try:
            self.client = BleakClient(self.address)
            await self.client.connect(timeout=timeout)
            
            # Handshake: Subscribe to notifications
            await self.client.start_notify(protocol.UUID_NOTIFY, self._notification_handler)
            
            # Send Query Packet
            query = protocol.build_packet(protocol.HANDSHAKE_QUERY)
            await self.client.write_gatt_char(protocol.UUID_WRITE, query, response=True)
            
            # Allow time for handshake to process
            await asyncio.sleep(0.5)
            
        except Exception as e:
            if self.client:
                await self.client.disconnect()
            raise ConnectionError(f"Failed to connect to {self.address}: {e}")

    async def disconnect(self):
        """Disconnects from the light."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    def _notification_handler(self, sender, data):
        """Handles incoming notifications (handshake responses)."""
        pass

    async def _send(self, packet: bytearray):
        if not self.client or not self.client.is_connected:
            # Try auto-reconnect once
            try:
                await self.connect()
            except Exception:
                raise ConnectionError("Light is not connected.")
        
        await self.client.write_gatt_char(protocol.UUID_WRITE, packet, response=True)

    async def set_power(self, is_on: bool):
        """Turns the light ON or OFF."""
        await self._send(protocol.cmd_power(is_on))

    async def set_rgb(self, hue: int, sat: int, bri: int):
        """Sets color using HSI (Hue 0-360, Sat 0-100, Bri 0-100)."""
        await self._send(protocol.cmd_rgb(hue, sat, bri))

    async def set_cct(self, temp: int, bri: int):
        """Sets white temperature (3200-5600K) and brightness."""
        await self._send(protocol.cmd_cct(temp, bri))

    async def set_effect(self, effect_id: int, bri: int = 50):
        """
        Sets a special effect (Scene).
        effect_id: 1-9 (See NeewerEffect enum)
        bri: 0-100
        """
        await self._send(protocol.cmd_effect(effect_id, bri))
