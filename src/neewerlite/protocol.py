from typing import List, Optional
from enum import IntEnum
from dataclasses import dataclass

# Constants
UUID_SERVICE = "69400001-b5a3-f393-e0a9-e50e24dcca99"
UUID_WRITE = "69400002-b5a3-f393-e0a9-e50e24dcca99"
UUID_NOTIFY = "69400003-b5a3-f393-e0a9-e50e24dcca99"

# Magic Packets
CMD_HEADER = 0x78
CMD_FX_EXTENDED = 0x8B  # Extended FX command (17 effects with full params)
CMD_FX_SIMPLE = 0x88    # Legacy simple FX (effect_id + brightness only)
HANDSHAKE_QUERY = [0x78, 0x85, 0x00, 0xFD]
CHANNEL_QUERY = [0x78, 0x84, 0x00, 0xFC]


class NeewerEffect(IntEnum):
    """All 17 FX effects supported by Neewer RGB lights (RGB62, SL-80, etc.).

    Each effect has specific parameters. Use the fx_* functions below to build
    the correct BLE packet with all parameters for each effect.

    Scene IDs match the NEEWER Studio APK (1-based, sent as first data byte).
    """
    LIGHTNING = 1       # Effet éclair
    PAPARAZZI = 2       # Paparazzi
    FAULTY_BULB = 3     # Ampoule défectueuse
    EXPLOSION = 4       # Explosion
    WELDING = 5         # Soudure
    CCT_FLASH = 6       # Flash CCT
    HUE_FLASH = 7       # Flash H.U.E (couleur)
    CCT_PULSE = 8       # Pulse CCT
    HUE_PULSE = 9       # Pulse H.U.E (couleur)
    COP_CAR = 10        # Voiture de police
    CANDLELIGHT = 11    # Bougie
    HUE_LOOP = 12       # Boucle H.U.E (cycle couleur)
    CCT_LOOP = 13       # Boucle CCT
    BRIGHTNESS_LOOP = 14  # Boucle INT (luminosité)
    TV_SCREEN = 15      # Écran TV
    FIREWORKS = 16      # Feux d'artifice
    PARTY = 17          # Fête


# Legacy effect enum for backward compatibility with simple 0x88 format
class SimpleFX(IntEnum):
    """Legacy 9-effect IDs for the old 0x88 format (effect_id + brightness only)."""
    COP_CAR = 1
    AMBULANCE = 2
    FIRE_TRUCK = 3
    FIREWORKS = 4
    PARTY = 5
    CANDLELIGHT = 6
    LIGHTNING = 7
    PAPARAZZI = 8
    TV_SCREEN = 9


class PoliceColor(IntEnum):
    """Color modes for Cop Car effect."""
    RED_BLUE = 0        # Rouge & Bleu
    WHITE_BLUE = 1      # Blanc & Bleu
    RED_BLUE_WHITE = 2  # Rouge, Bleu & Blanc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


def calculate_checksum(data: List[int]) -> int:
    """Calculates the Neewer simple checksum (sum & 0xFF)."""
    return sum(data) & 0xFF


def build_packet(payload: List[int]) -> bytearray:
    """Appends checksum and converts to bytearray."""
    checksum = calculate_checksum(payload)
    return bytearray(payload + [checksum])


def _build_fx(effect_id: int, params: List[int]) -> bytearray:
    """Build an extended FX packet: [0x78, 0x8B, length, effect_id, ...params, checksum]."""
    data = [effect_id] + params
    return build_packet([CMD_HEADER, CMD_FX_EXTENDED, len(data)] + data)


def _cct_val(temp_k: int) -> int:
    """Convert temperature in Kelvin to CCT byte value (25-85)."""
    if temp_k > 100:
        return _clamp(temp_k // 100, 25, 85)
    return _clamp(temp_k, 25, 85)


# ---------------------------------------------------------------------------
# Basic Commands
# ---------------------------------------------------------------------------

def cmd_power(is_on: bool) -> bytearray:
    """Power ON/OFF. ON: [0x78, 0x81, 0x01, 0x01], OFF: [0x78, 0x81, 0x01, 0x02]."""
    val = 0x01 if is_on else 0x02
    return build_packet([CMD_HEADER, 0x81, 0x01, val])


def cmd_rgb(hue: int, sat: int, bri: int) -> bytearray:
    """HSI Color: [0x78, 0x86, 0x04, HueLo, HueHi, Sat, Bri].

    Args:
        hue: 0-360 degrees
        sat: 0-100 percent
        bri: 0-100 percent
    """
    hue = int(hue) % 360
    sat = _clamp(sat, 0, 100)
    bri = _clamp(bri, 0, 100)
    return build_packet([CMD_HEADER, 0x86, 0x04, hue & 0xFF, (hue >> 8) & 0xFF, sat, bri])


def cmd_cct(temp_k: int, bri: int) -> bytearray:
    """CCT (Color Temperature): [0x78, 0x87, 0x02, Bri, CCT_Val].

    Args:
        temp_k: 2500-8500 Kelvin (or raw 25-85)
        bri: 0-100 percent
    """
    bri = _clamp(bri, 0, 100)
    return build_packet([CMD_HEADER, 0x87, 0x02, bri, _cct_val(temp_k)])


def cmd_cct_gm(temp_k: int, bri: int, gm: int = 50) -> bytearray:
    """CCT with GM tint (3 bytes): [0x78, 0x87, 0x03, Bri, CCT_Val, GM].

    Args:
        temp_k: 2500-8500 Kelvin
        bri: 0-100 percent
        gm: 0-100 (50=neutral, <50=magenta, >50=green)
    """
    bri = _clamp(bri, 0, 100)
    gm = _clamp(gm, 0, 100)
    return build_packet([CMD_HEADER, 0x87, 0x03, bri, _cct_val(temp_k), gm])


def cmd_effect_simple(effect_id: int, bri: int) -> bytearray:
    """Legacy simple FX: [0x78, 0x88, 0x02, EffectID, Bri].

    Only sends effect ID + brightness. No speed/color/GM params.
    Use fx_* functions for full control.
    """
    bri = _clamp(bri, 0, 100)
    effect_id = _clamp(effect_id, 1, 9)
    return build_packet([CMD_HEADER, CMD_FX_SIMPLE, 0x02, effect_id, bri])


def cmd_query_status() -> bytearray:
    """Query device status (power state, mode, etc.)."""
    return build_packet(HANDSHAKE_QUERY)


def cmd_query_channel() -> bytearray:
    """Query channel/mode information."""
    return build_packet(CHANNEL_QUERY)


# ---------------------------------------------------------------------------
# Extended FX Commands (0x8B) — 17 effects with full parameters
# ---------------------------------------------------------------------------
# Byte formats verified against NEEWER Studio APK decompilation (wg.java)

def fx_lightning(bri: int = 50, cct: int = 5500, speed: int = 5) -> bytearray:
    """Effect 1: Lightning / Effet éclair.

    Data: [1, bri, cct_val, speed] — 4 bytes.

    Args:
        bri: brightness 0-100
        cct: color temperature 2500-8500K
        speed: 1-10
    """
    return _build_fx(1, [_clamp(bri, 0, 100), _cct_val(cct), _clamp(speed, 1, 10)])


def fx_paparazzi(bri: int = 50, cct: int = 5500, gm: int = 50, speed: int = 5) -> bytearray:
    """Effect 2: Paparazzi.

    Data: [2, bri, cct_val, gm, speed] — 5 bytes.

    Args:
        bri: brightness 0-100
        cct: color temperature 2500-8500K
        gm: green-magenta tint 0-100 (50=neutral)
        speed: 1-10
    """
    return _build_fx(2, [_clamp(bri, 0, 100), _cct_val(cct), _clamp(gm, 0, 100), _clamp(speed, 1, 10)])


def fx_faulty_bulb(bri: int = 50, cct: int = 5500, gm: int = 50, speed: int = 5) -> bytearray:
    """Effect 3: Faulty Bulb / Ampoule défectueuse.

    Data: [3, bri, cct_val, gm, speed] — 5 bytes.
    """
    return _build_fx(3, [_clamp(bri, 0, 100), _cct_val(cct), _clamp(gm, 0, 100), _clamp(speed, 1, 10)])


def fx_explosion(bri: int = 50, cct: int = 5500, gm: int = 50, speed: int = 5, ember: int = 5) -> bytearray:
    """Effect 4: Explosion.

    Data: [4, bri, cct_val, gm, speed, ember] — 6 bytes.

    Args:
        ember: spark/ember intensity 0-10
    """
    return _build_fx(4, [_clamp(bri, 0, 100), _cct_val(cct), _clamp(gm, 0, 100),
                         _clamp(speed, 1, 10), _clamp(ember, 0, 10)])


def fx_welding(bri_min: int = 0, bri_max: int = 50, cct: int = 5500, gm: int = 50, speed: int = 5) -> bytearray:
    """Effect 5: Welding / Soudure.

    Data: [5, bri_min, bri_max, cct_val, gm, speed] — 6 bytes.

    Args:
        bri_min: minimum brightness 0-100
        bri_max: maximum brightness 0-100
    """
    return _build_fx(5, [_clamp(bri_min, 0, 100), _clamp(bri_max, 0, 100),
                         _cct_val(cct), _clamp(gm, 0, 100), _clamp(speed, 1, 10)])


def fx_cct_flash(bri: int = 50, cct: int = 5500, gm: int = 50, speed: int = 5) -> bytearray:
    """Effect 6: CCT Flash / Flash CCT.

    Data: [6, bri, cct_val, gm, speed] — 5 bytes.
    """
    return _build_fx(6, [_clamp(bri, 0, 100), _cct_val(cct), _clamp(gm, 0, 100), _clamp(speed, 1, 10)])


def fx_hue_flash(bri: int = 50, hue: int = 210, sat: int = 100, speed: int = 5) -> bytearray:
    """Effect 7: Hue Flash / Flash H.U.E.

    Data: [7, bri, hue_lo, hue_hi, sat, speed] — 6 bytes.

    Args:
        hue: 0-360 degrees
        sat: saturation 0-100
    """
    h = _clamp(hue, 0, 360)
    return _build_fx(7, [_clamp(bri, 0, 100), h & 0xFF, (h >> 8) & 0xFF,
                         _clamp(sat, 0, 100), _clamp(speed, 1, 10)])


def fx_cct_pulse(bri: int = 50, cct: int = 5500, gm: int = 50, speed: int = 5) -> bytearray:
    """Effect 8: CCT Pulse / Pulse CCT.

    Data: [8, bri, cct_val, gm, speed] — 5 bytes.
    """
    return _build_fx(8, [_clamp(bri, 0, 100), _cct_val(cct), _clamp(gm, 0, 100), _clamp(speed, 1, 10)])


def fx_hue_pulse(bri: int = 50, hue: int = 210, sat: int = 100, speed: int = 5) -> bytearray:
    """Effect 9: Hue Pulse / Pulse H.U.E.

    Data: [9, bri, hue_lo, hue_hi, sat, speed] — 6 bytes.
    """
    h = _clamp(hue, 0, 360)
    return _build_fx(9, [_clamp(bri, 0, 100), h & 0xFF, (h >> 8) & 0xFF,
                         _clamp(sat, 0, 100), _clamp(speed, 1, 10)])


def fx_cop_car(bri: int = 50, color: int = 0, speed: int = 5) -> bytearray:
    """Effect 10: Cop Car / Voiture de police.

    Data: [10, bri, color_num, speed] — 4 bytes.

    Args:
        color: 0=Red&Blue, 1=White&Blue, 2=Red+Blue+White (see PoliceColor enum)
    """
    return _build_fx(10, [_clamp(bri, 0, 100), _clamp(color, 0, 2), _clamp(speed, 1, 10)])


def fx_candlelight(bri_min: int = 0, bri_max: int = 100, cct: int = 3200, gm: int = 50,
                   speed: int = 5, ember: int = 5) -> bytearray:
    """Effect 11: Candlelight / Bougie.

    Data: [11, bri_min, bri_max, cct_val, gm, speed, ember] — 7 bytes.
    """
    return _build_fx(11, [_clamp(bri_min, 0, 100), _clamp(bri_max, 0, 100),
                          _cct_val(cct), _clamp(gm, 0, 100),
                          _clamp(speed, 1, 10), _clamp(ember, 0, 10)])


def fx_hue_loop(bri: int = 50, hue_min: int = 0, hue_max: int = 360, speed: int = 5) -> bytearray:
    """Effect 12: Hue Loop / Boucle H.U.E (color cycle).

    Data: [12, bri, hue_min_lo, hue_min_hi, hue_max_lo, hue_max_hi, speed] — 7 bytes.

    Args:
        hue_min: start hue 0-360
        hue_max: end hue 0-360
    """
    h_min = _clamp(hue_min, 0, 360)
    h_max = _clamp(hue_max, 0, 360)
    return _build_fx(12, [_clamp(bri, 0, 100),
                          h_min & 0xFF, (h_min >> 8) & 0xFF,
                          h_max & 0xFF, (h_max >> 8) & 0xFF,
                          _clamp(speed, 1, 10)])


def fx_cct_loop(bri: int = 50, cct_min: int = 2500, cct_max: int = 8500, speed: int = 5) -> bytearray:
    """Effect 13: CCT Loop / Boucle CCT.

    Data: [13, bri, cct_min_val, cct_max_val, speed] — 5 bytes.

    Args:
        cct_min: minimum color temperature in Kelvin
        cct_max: maximum color temperature in Kelvin
    """
    return _build_fx(13, [_clamp(bri, 0, 100), _cct_val(cct_min), _cct_val(cct_max),
                          _clamp(speed, 1, 10)])


def fx_brightness_loop(bri_min: int = 0, bri_max: int = 50, cct: int = 5500,
                       hue: int = 210, speed: int = 5, cct_hsi_mode: int = 0) -> bytearray:
    """Effect 14: Brightness Loop / Boucle INT.

    Data: [14, cct_hsi_num, bri_min, bri_max, hue_lo, hue_hi, cct_val, speed] — 8 bytes.

    Args:
        cct_hsi_mode: 0=CCT mode (uses cct param), 1=HSI mode (uses hue param)
        hue: hue 0-360 (used when cct_hsi_mode=1)
    """
    h = _clamp(hue, 0, 360)
    return _build_fx(14, [_clamp(cct_hsi_mode, 0, 1),
                          _clamp(bri_min, 0, 100), _clamp(bri_max, 0, 100),
                          h & 0xFF, (h >> 8) & 0xFF,
                          _cct_val(cct), _clamp(speed, 1, 10)])


def fx_tv_screen(bri_min: int = 0, bri_max: int = 50, cct: int = 5500, gm: int = 50,
                 speed: int = 5) -> bytearray:
    """Effect 15: TV Screen / Écran TV.

    Data: [15, bri_min, bri_max, cct_val, gm, speed] — 6 bytes.
    """
    return _build_fx(15, [_clamp(bri_min, 0, 100), _clamp(bri_max, 0, 100),
                          _cct_val(cct), _clamp(gm, 0, 100), _clamp(speed, 1, 10)])


def fx_fireworks(bri: int = 50, mode: int = 0, speed: int = 5, ember: int = 5) -> bytearray:
    """Effect 16: Fireworks / Feux d'artifice.

    Data: [16, bri, mode_num, speed, ember] — 5 bytes.

    Args:
        mode: color mode 0-2
        ember: spark intensity 0-10
    """
    return _build_fx(16, [_clamp(bri, 0, 100), _clamp(mode, 0, 2),
                          _clamp(speed, 1, 10), _clamp(ember, 0, 10)])


def fx_party(bri: int = 50, mode: int = 0, speed: int = 5) -> bytearray:
    """Effect 17: Party / Fête.

    Data: [17, bri, mode_num, speed] — 4 bytes.

    Args:
        mode: color mode 0-2
    """
    return _build_fx(17, [_clamp(bri, 0, 100), _clamp(mode, 0, 2), _clamp(speed, 1, 10)])


# ---------------------------------------------------------------------------
# Convenience: build FX by NeewerEffect enum
# ---------------------------------------------------------------------------

@dataclass
class FXParams:
    """Parameters for FX effects. Not all params are used by every effect."""
    brightness: int = 50
    brightness_min: int = 0
    brightness_max: int = 50
    cct: int = 5500         # Color temperature in Kelvin
    gm: int = 50            # Green-Magenta tint (0-100, 50=neutral)
    speed: int = 5          # 1-10
    ember: int = 5          # Spark intensity 0-10
    hue: int = 210          # 0-360
    saturation: int = 100   # 0-100
    color_mode: int = 0     # 0-2 for Police/Fireworks/Party
    hue_min: int = 0        # 0-360
    hue_max: int = 360      # 0-360
    cct_min: int = 2500     # Kelvin
    cct_max: int = 8500     # Kelvin
    cct_hsi_mode: int = 0   # 0=CCT, 1=HSI (for Brightness Loop)


def build_fx(effect: NeewerEffect, params: Optional[FXParams] = None) -> bytearray:
    """Build a complete FX command for any of the 17 effects.

    Args:
        effect: NeewerEffect enum value (1-17)
        params: FXParams with the relevant parameters (uses defaults if None)

    Returns:
        bytearray ready to send via BLE write characteristic
    """
    p = params or FXParams()
    match effect:
        case NeewerEffect.LIGHTNING:
            return fx_lightning(p.brightness, p.cct, p.speed)
        case NeewerEffect.PAPARAZZI:
            return fx_paparazzi(p.brightness, p.cct, p.gm, p.speed)
        case NeewerEffect.FAULTY_BULB:
            return fx_faulty_bulb(p.brightness, p.cct, p.gm, p.speed)
        case NeewerEffect.EXPLOSION:
            return fx_explosion(p.brightness, p.cct, p.gm, p.speed, p.ember)
        case NeewerEffect.WELDING:
            return fx_welding(p.brightness_min, p.brightness_max, p.cct, p.gm, p.speed)
        case NeewerEffect.CCT_FLASH:
            return fx_cct_flash(p.brightness, p.cct, p.gm, p.speed)
        case NeewerEffect.HUE_FLASH:
            return fx_hue_flash(p.brightness, p.hue, p.saturation, p.speed)
        case NeewerEffect.CCT_PULSE:
            return fx_cct_pulse(p.brightness, p.cct, p.gm, p.speed)
        case NeewerEffect.HUE_PULSE:
            return fx_hue_pulse(p.brightness, p.hue, p.saturation, p.speed)
        case NeewerEffect.COP_CAR:
            return fx_cop_car(p.brightness, p.color_mode, p.speed)
        case NeewerEffect.CANDLELIGHT:
            return fx_candlelight(p.brightness_min, p.brightness_max, p.cct, p.gm, p.speed, p.ember)
        case NeewerEffect.HUE_LOOP:
            return fx_hue_loop(p.brightness, p.hue_min, p.hue_max, p.speed)
        case NeewerEffect.CCT_LOOP:
            return fx_cct_loop(p.brightness, p.cct_min, p.cct_max, p.speed)
        case NeewerEffect.BRIGHTNESS_LOOP:
            return fx_brightness_loop(p.brightness_min, p.brightness_max, p.cct, p.hue, p.speed, p.cct_hsi_mode)
        case NeewerEffect.TV_SCREEN:
            return fx_tv_screen(p.brightness_min, p.brightness_max, p.cct, p.gm, p.speed)
        case NeewerEffect.FIREWORKS:
            return fx_fireworks(p.brightness, p.color_mode, p.speed, p.ember)
        case NeewerEffect.PARTY:
            return fx_party(p.brightness, p.color_mode, p.speed)
        case _:
            raise ValueError(f"Unknown effect: {effect}")


# Backward compatibility alias
cmd_effect = cmd_effect_simple


# ===========================================================================
# NEEWER HOME PROTOCOL (0x7A) — NH-PD / NS02 series (LED strips)
# ===========================================================================
# These devices use a different header byte (0x7A) and different data IDs.
# Packet format: [0x7A, dataId, dataLen, ...data, checksum]
# Long packets:  [0x7A, dataId, lenHi, lenLo, ...data, checksum]

HOME_HEADER = 0x7A


def _build_home_packet(data_id: int, data: List[int]) -> bytearray:
    """Build a Neewer Home short packet: [0x7A, dataId, len, ...data, checksum]."""
    payload = [HOME_HEADER, data_id, len(data)] + data
    checksum = calculate_checksum(payload)
    return bytearray(payload + [checksum])


def _build_home_long_packet(data_id: int, data: List[int]) -> bytearray:
    """Build a Neewer Home long packet: [0x7A, dataId, lenHi, lenLo, ...data, checksum]."""
    len_hi = (len(data) >> 8) & 0xFF
    len_lo = len(data) & 0xFF
    payload = [HOME_HEADER, data_id, len_hi, len_lo] + data
    checksum = calculate_checksum(payload)
    return bytearray(payload + [checksum])


def _bcd_brightness(bri: int) -> tuple:
    """Encode brightness 0-1000 as BCD pair (hi, lo) for NH protocol."""
    bri = _clamp(bri, 0, 1000)
    return (bri // 10, bri % 10)


# --- Power ---

def home_power_on() -> bytearray:
    """NH: Turn light ON."""
    return _build_home_packet(0x0A, [0x01])


def home_power_off() -> bytearray:
    """NH: Turn light OFF."""
    return _build_home_packet(0x0A, [0x02])


# --- Query ---

def home_query_all() -> bytearray:
    """NH: Query all device parameters (power, mode, brightness, etc.)."""
    return _build_home_packet(0x08, [0x00])


# --- CCT / Lighting ---

def home_set_lighting(brightness: int, temperature: int) -> bytearray:
    """NH: Set CCT mode.

    Args:
        brightness: 0-1000 (thousandths precision)
        temperature: color temp in device units (e.g. 27=2700K, 65=6500K)
    """
    bri_hi, bri_lo = _bcd_brightness(brightness)
    temp = _clamp(temperature, 22, 65)
    return _build_home_packet(0x0C, [bri_hi, bri_lo, temp, 0x00, 0x01, 0x00])


# --- Color (HSI, all segments same color) ---

def home_set_color(brightness: int, hue: int, saturation: int, lightness: int = 100) -> bytearray:
    """NH: Set all segments to one HSI color.

    Args:
        brightness: 0-1000
        hue: 0-360
        saturation: 0-100
        lightness: 0-100
    """
    bri_hi, bri_lo = _bcd_brightness(brightness)
    h = _clamp(hue, 0, 360)
    hue_hi = (h >> 8) & 0xFF
    hue_lo = h & 0xFF
    sat = _clamp(saturation, 0, 100)
    light = _clamp(lightness, 0, 100)
    return _build_home_long_packet(0x0D, [
        bri_hi, bri_lo, 0x01, light, hue_hi, hue_lo, sat, 0x00, 0x01, 0x00
    ])


# --- Music Mode ---

def home_music_mode(brightness: int, mode_id: int = 0, speed: int = 50,
                    sensitivity: int = 80) -> bytearray:
    """NH: Activate music reactive mode.

    The strip uses the phone's microphone to modulate the light.

    Args:
        brightness: 0-100
        mode_id: 0-5 (Energie, Respiration, Battre, Meteore, Ciel étoilé, Néon)
        speed: 0-100
        sensitivity: 0-100 (mic sensitivity)
    """
    bri = _clamp(brightness, 0, 100)
    data = [
        0x01,                           # enable
        0x00,                           # padding
        bri,
        _clamp(mode_id, 0, 10),
        _clamp(speed, 0, 100),
        _clamp(sensitivity, 0, 100),
        0x01,                           # colorMode = HSI
        0x08,                           # numColors = 8
    ]
    # 8 rainbow colors: [lightness, hueHi, hueLo, saturation]
    hues = [0, 45, 90, 135, 180, 225, 270, 315]
    for h in hues:
        data.extend([100, (h >> 8) & 0xFF, h & 0xFF, 100])
    data.append(0x01)  # gradient
    data.append(0x00)  # startPoint

    return _build_home_packet(0x0E, data)


# ===========================================================================
# Device type detection
# ===========================================================================

def is_neewer_home(name: str) -> bool:
    """Returns True if the device name indicates a Neewer Home (NH/NS02) device."""
    n = (name or "").upper()
    return n.startswith("NH-") or "NS02" in n


def is_neewer_studio(name: str) -> bool:
    """Returns True if the device name indicates a standard Neewer Studio light."""
    n = (name or "").upper()
    return any(k in n for k in ["NEEWER", "RGB62", "RGB660", "SL-", "GL1", "ZN-", "NW-"])

