import asyncio
import logging
from typing import Optional
from bleak import BleakClient
from . import protocol
from .protocol import NeewerEffect, FXParams
from .exceptions import ConnectionError

logger = logging.getLogger(__name__)


class NeewerLight:
    """Controls any Neewer light over Bluetooth LE.

    Auto-detects the protocol based on device name:
    - **Studio lights** (RGB62, SL-80, GL1, etc.): standard 0x78 protocol
    - **Home strips** (NH-PD, NS02): Neewer Home 0x7A protocol

    Usage:
        light = NeewerLight("AA:BB:CC:DD:EE:FF", name="NEEWER-RGB62")
        await light.connect()
        await light.set_rgb(0, 100, 50)
        await light.set_effect(NeewerEffect.COP_CAR, brightness=80)
        await light.set_power(False)
    """

    def __init__(self, address: str, name: str = ""):
        self.address = address
        self.name = name
        self.client: Optional[BleakClient] = None
        self.is_on: Optional[bool] = None
        self._is_home = protocol.is_neewer_home(name)

    @property
    def is_home_device(self) -> bool:
        """True if this is a Neewer Home (NH/NS02) device."""
        return self._is_home

    async def connect(self, timeout: float = 10.0):
        """Connects to the light and queries initial state."""
        logger.info(f"Connecting to {self.address} ({self.name})...")
        if self.client and self.client.is_connected:
            return

        try:
            self.client = BleakClient(self.address)
            await self.client.connect(timeout=timeout)

            # Subscribe to notifications
            try:
                await self.client.start_notify(protocol.UUID_NOTIFY, self._notification_handler)
            except Exception as e:
                if "already started" not in str(e):
                    raise

            # Auto-detect device type from name if not already set
            if not self.name and self.client.services:
                # Try to read device name from GATT if available
                pass

            # Query initial state
            await asyncio.sleep(0.3)
            if self._is_home:
                await self._send_raw(protocol.home_query_all())
            else:
                await self._send_raw(protocol.cmd_query_status())
                await asyncio.sleep(0.3)
                await self._send_raw(protocol.cmd_query_channel())

            await asyncio.sleep(0.2)

        except Exception as e:
            if self.client:
                try:
                    await self.client.disconnect()
                except Exception:
                    pass
            raise ConnectionError(f"Failed to connect to {self.address}: {e}")

    async def disconnect(self):
        """Disconnects from the light."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    def _notification_handler(self, sender, data: bytearray):
        """Handles incoming BLE notifications — parses power state."""
        hex_str = " ".join([f"{b:02X}" for b in data])
        logger.debug(f"RX < {hex_str}")

        if len(data) < 3:
            return

        # Neewer Home response (0x7A)
        if data[0] == protocol.HOME_HEADER:
            data_id = data[1]
            if data_id in (0x0A, 0x08) and len(data) > 3:
                self.is_on = data[3] == 0x01
                logger.info(f"NH power: {'ON' if self.is_on else 'OFF'}")
            return

        # Standard response (0x78)
        if data[0] != protocol.CMD_HEADER or len(data) < 4:
            return

        cmd = data[1]
        if cmd == 0x02 and len(data) > 3:
            self.is_on = data[3] == 0x01
            logger.info(f"Power: {'ON' if self.is_on else 'OFF'}")
        elif cmd == 0x85 and len(data) > 3:
            self.is_on = data[3] == 0x01
            logger.info(f"Status: power={'ON' if self.is_on else 'OFF'}")
        elif cmd == 0x01 and len(data) > 4 and data[3] in (0x01, 0x02):
            self.is_on = data[3] == 0x01

    async def _send_raw(self, packet: bytearray):
        if not self.client or not self.client.is_connected:
            raise ConnectionError("Light is not connected.")
        hex_str = " ".join([f"{b:02X}" for b in packet])
        logger.debug(f"TX > {hex_str}")
        await self.client.write_gatt_char(protocol.UUID_WRITE, packet, response=True)

    async def _send(self, packet: bytearray):
        """Send a command, auto-reconnecting if needed."""
        if not self.client or not self.client.is_connected:
            try:
                await self.connect()
            except Exception:
                raise ConnectionError("Light is not connected.")
        await self._send_raw(packet)

    # ------------------------------------------------------------------
    # Power (auto-detects protocol)
    # ------------------------------------------------------------------

    async def set_power(self, is_on: bool):
        """Turns the light ON or OFF."""
        if self._is_home:
            await self._send(protocol.home_power_on() if is_on else protocol.home_power_off())
        else:
            await self._send(protocol.cmd_power(is_on))
        self.is_on = is_on

    async def turn_on(self):
        await self.set_power(True)

    async def turn_off(self):
        await self.set_power(False)

    # ------------------------------------------------------------------
    # Color modes (auto-detects protocol)
    # ------------------------------------------------------------------

    async def set_rgb(self, hue: int, sat: int, bri: int):
        """Sets color using HSI (Hue 0-360, Sat 0-100, Bri 0-100).

        On Home devices, bri is scaled to 0-1000 automatically.
        """
        if self._is_home:
            await self._send(protocol.home_set_color(bri * 10, hue, sat))
        else:
            await self._send(protocol.cmd_rgb(hue, sat, bri))

    async def set_cct(self, temp: int, bri: int, gm: int = 50):
        """Sets white temperature and brightness.

        Args:
            temp: Color temperature in Kelvin (2500-8500)
            bri: Brightness 0-100
            gm: Green-Magenta tint 0-100 (50=neutral, studio lights only)
        """
        if self._is_home:
            temp_val = temp // 100 if temp > 100 else temp
            await self._send(protocol.home_set_lighting(bri * 10, temp_val))
        else:
            if gm != 50:
                await self._send(protocol.cmd_cct_gm(temp, bri, gm))
            else:
                await self._send(protocol.cmd_cct(temp, bri))

    # ------------------------------------------------------------------
    # Effects — Studio lights (0x78 / 0x8B)
    # ------------------------------------------------------------------

    async def set_effect(self, effect: NeewerEffect, **kwargs):
        """Sets a special effect with full parameters (studio lights only).

        Uses the extended 0x8B format with per-effect parameters.

        Args:
            effect: NeewerEffect enum (1-17)
            **kwargs: Parameters for FXParams (brightness, speed, cct, gm, etc.)

        Example:
            await light.set_effect(NeewerEffect.COP_CAR, brightness=80, color_mode=2, speed=7)
            await light.set_effect(NeewerEffect.CANDLELIGHT, brightness_min=10, brightness_max=80)
        """
        if self._is_home:
            logger.warning("set_effect() is for studio lights. Use set_music_mode() for NH strips.")
            return
        params = FXParams(**kwargs) if kwargs else FXParams()
        await self._send(protocol.build_fx(effect, params))

    async def set_effect_simple(self, effect_id: int, bri: int = 50):
        """Legacy simple FX (0x88 format). Use set_effect() for full control."""
        await self._send(protocol.cmd_effect_simple(effect_id, bri))

    # ------------------------------------------------------------------
    # Music mode — Home strips (0x7A)
    # ------------------------------------------------------------------

    async def set_music_mode(self, brightness: int = 50, mode_id: int = 0,
                             speed: int = 50, sensitivity: int = 80):
        """Activate music reactive mode (Home/NH strips only).

        Args:
            brightness: 0-100
            mode_id: 0-5 (Energie, Respiration, Battre, Meteore, Ciel étoilé, Néon)
            speed: 0-100
            sensitivity: mic sensitivity 0-100
        """
        if not self._is_home:
            logger.warning("set_music_mode() is for NH strips only.")
            return
        await self._send(protocol.home_music_mode(brightness, mode_id, speed, sensitivity))

    # ------------------------------------------------------------------
    # Individual FX shortcuts (studio lights)
    # ------------------------------------------------------------------

    async def fx_lightning(self, bri: int = 50, cct: int = 5500, speed: int = 5):
        await self._send(protocol.fx_lightning(bri, cct, speed))

    async def fx_paparazzi(self, bri: int = 50, cct: int = 5500, gm: int = 50, speed: int = 5):
        await self._send(protocol.fx_paparazzi(bri, cct, gm, speed))

    async def fx_faulty_bulb(self, bri: int = 50, cct: int = 5500, gm: int = 50, speed: int = 5):
        await self._send(protocol.fx_faulty_bulb(bri, cct, gm, speed))

    async def fx_explosion(self, bri: int = 50, cct: int = 5500, gm: int = 50, speed: int = 5, ember: int = 5):
        await self._send(protocol.fx_explosion(bri, cct, gm, speed, ember))

    async def fx_welding(self, bri_min: int = 0, bri_max: int = 50, cct: int = 5500, gm: int = 50, speed: int = 5):
        await self._send(protocol.fx_welding(bri_min, bri_max, cct, gm, speed))

    async def fx_cop_car(self, bri: int = 50, color: int = 0, speed: int = 5):
        """color: 0=rouge, 1=bleu, 2=rouge+bleu, 3=blanc+bleu, 4=rouge+bleu+blanc"""
        await self._send(protocol.fx_cop_car(bri, color, speed))

    async def fx_candlelight(self, bri_min: int = 0, bri_max: int = 100, cct: int = 3200,
                             gm: int = 50, speed: int = 5, ember: int = 5):
        await self._send(protocol.fx_candlelight(bri_min, bri_max, cct, gm, speed, ember))

    async def fx_tv_screen(self, bri_min: int = 0, bri_max: int = 50, cct: int = 5500,
                           gm: int = 50, speed: int = 5):
        await self._send(protocol.fx_tv_screen(bri_min, bri_max, cct, gm, speed))

    async def fx_fireworks(self, bri: int = 50, mode: int = 0, speed: int = 5, ember: int = 5):
        await self._send(protocol.fx_fireworks(bri, mode, speed, ember))

    async def fx_party(self, bri: int = 50, mode: int = 0, speed: int = 5):
        await self._send(protocol.fx_party(bri, mode, speed))
