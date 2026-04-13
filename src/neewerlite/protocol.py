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
# NEEWER HOME SCENES (0x12) — 73 pre-built scenes for NH strips
# ===========================================================================
# Scene packet: [0x7A, 0x12, lenHi, lenLo, ...data, checksum]
# Each scene has multiple frames with different animation modes (0-17).

@dataclass
class SceneFrame:
    """A single animation frame within a Home strip scene.

    Args:
        colors: List of (hue, saturation, lightness) tuples. Hue 0-360, others 0-100.
        speed: Effect speed/value 0-100
        method: Effect method flag
        mode: Animation mode (0-17):
            0=static, 1=breathe, 2=flicker, 3=chase_left, 4=chase_right,
            5=flash/strobe, 6=wave, 7=pulse, 8=scan, 9=pulse2,
            11=gradient_sweep, 12=random_cycle, 13=gradient,
            14=sparkle, 15=meteor, 16=theater_chase, 17=hold
        direction: 0=none, 1=forward, 2=reverse
        main_light: Main light effect (usually 0)
        extras: Mode-specific parameters (e.g., seg, mir, tail, gap, bgH, bgS, bgL, etc.)
    """
    colors: list  # List of (hue, sat, light) tuples
    speed: int = 50
    method: int = 1
    mode: int = 0
    direction: int = 0
    main_light: int = 0
    extras: Optional[dict] = None

    def _encode(self) -> list:
        """Encode this frame into BLE bytes."""
        block = []

        # effectMode
        block.append(self.mode)

        # Mode-specific params
        extras = self.extras or {}
        if self.mode == 0:
            block.append(min(255, self.speed * 10))
        elif self.mode == 1:
            block.append(self.speed)
            block.append(0 if self.method == 1 else 1)
        elif self.mode == 2:
            block.append(self.speed)
            block.append(0 if self.method == 1 else 1)
            block.append(1)  # flickerAmount
        elif self.mode in (3, 4):
            block.append(self.speed)
            d = self.direction if self.direction > 0 else 1
            block.append(d)
            block.append(0 if d == 1 else 1)
        elif self.mode == 5:
            block.append(self.speed)
            block.append(0 if self.method == 5 else 1)
        elif self.mode in (6, 8):
            block.append(self.speed)
            d = self.direction if self.direction > 0 else 1
            block.append(d)
            block.append(0 if d == 1 else 1)
        elif self.mode in (7, 9):
            block.append(self.speed)
        elif self.mode == 11:
            block.append(self.speed)
            d = self.direction if self.direction > 0 else 1
            block.append(d)
            block.append(0 if d == 1 else 1)
        elif self.mode == 12:
            block.append(self.speed)
            block.append(extras.get("longestSeg", 5))
            block.append(extras.get("minOccur", 5))
            block.append(extras.get("cycleTimes", 5))
        elif self.mode == 13:
            block.append(self.speed)
            d = self.direction if self.direction > 0 else 1
            block.append(d)
            block.append(0 if d == 1 else 1)
        elif self.mode == 14:
            block.append(self.speed)
            block.append(extras.get("src", 1))
            block.append(extras.get("mul", 1))
            block.append(extras.get("dis", 0))
            bg_h = extras.get("bgH", 0)
            block.extend([extras.get("bgL", 0), (bg_h >> 8) & 0xFF, bg_h & 0xFF, extras.get("bgS", 0)])
        elif self.mode == 15:
            block.append(self.speed)
            d = self.direction if self.direction > 0 else 1
            block.append(d)
            block.append(extras.get("seg", 1))
            block.append(extras.get("mir", 0))
            block.append(extras.get("tail", 6))
            block.append(extras.get("spc", 0))
            block.append(extras.get("dM", 0))
            block.append(extras.get("dE", 5))
            if "bgH" in extras:
                bg_h = extras["bgH"]
                block.extend([extras.get("bgL", 0), (bg_h >> 8) & 0xFF, bg_h & 0xFF, extras.get("bgS", 0)])
        elif self.mode == 16:
            block.append(self.speed)
            d = self.direction if self.direction > 0 else 1
            block.append(d)
            block.append(extras.get("seg", 4))
            block.append(extras.get("mir", 0))
            block.append(extras.get("gap", 0))
        elif self.mode == 17:
            block.append(self.speed)
        else:
            block.append(self.speed)

        # mainLightEffect + 4 zero bytes
        block.append(self.main_light)
        block.extend([0x00, 0x00, 0x00, 0x00])

        # colorCount + colors [lightness, hueHi, hueLo, saturation]
        block.append(len(self.colors))
        for h, s, l in self.colors:
            block.extend([l, (h >> 8) & 0xFF, h & 0xFF, s])

        # Effect trailer
        block.extend([0x00, 0x01, self.speed])

        return block


@dataclass
class HomeScene:
    """A complete scene for Neewer Home strips (NH/NS02).

    Contains one or more animation frames that play in sequence.
    Use HomeScene.all() to get all 73 built-in scenes.

    Example:
        scene = HomeScene.by_name("Arc-en-ciel")
        packet = scene.build_packet(brightness=80)
    """
    id: int
    name: str
    category: str
    frames: list  # List of SceneFrame

    def build_packet(self, brightness: int = 50) -> bytearray:
        """Build the BLE packet for this scene.

        Args:
            brightness: 0-100 (auto-scaled to 0-1000 internally)

        Returns:
            bytearray ready to send via BLE write characteristic
        """
        data = []

        # effectId (16-bit BE)
        data.append((self.id >> 8) & 0xFF)
        data.append(self.id & 0xFF)

        # brightness BCD
        bri = _clamp(brightness * 10, 0, 1000)
        data.append(bri // 10)
        data.append(bri % 10)

        # frame count + constants
        data.append(len(self.frames))
        data.extend([0x01, 0x00])

        # Each frame with length prefix
        for frame in self.frames:
            block = frame._encode()
            data.append((len(block) >> 8) & 0xFF)
            data.append(len(block) & 0xFF)
            data.extend(block)

        # Panel trailer
        data.extend([0x00, 0x01, 0x00])

        return _build_home_long_packet(0x12, data)

    @staticmethod
    def by_name(name: str) -> Optional['HomeScene']:
        """Find a scene by name (case-insensitive)."""
        name_lower = name.lower()
        for s in HOME_SCENES:
            if s.name.lower() == name_lower:
                return s
        return None

    @staticmethod
    def by_id(scene_id: int) -> Optional['HomeScene']:
        """Find a scene by ID (1-73)."""
        for s in HOME_SCENES:
            if s.id == scene_id:
                return s
        return None

    @staticmethod
    def by_category(category: str) -> list:
        """Get all scenes in a category (Naturel, Vie, Festival, Emotion, Sport)."""
        cat_lower = category.lower()
        return [s for s in HOME_SCENES if s.category.lower() == cat_lower]

    @staticmethod
    def all() -> list:
        """Get all 73 built-in scenes."""
        return list(HOME_SCENES)

    @staticmethod
    def categories() -> list:
        """Get all category names."""
        return ["Naturel", "Vie", "Festival", "Emotion", "Sport"]


def _f(colors, speed, method, mode, direction, main_light):
    """Shorthand for SceneFrame without extras."""
    return SceneFrame(colors=colors, speed=speed, method=method, mode=mode,
                      direction=direction, main_light=main_light)

def _fe(colors, speed, method, mode, direction, main_light, extras):
    """Shorthand for SceneFrame with extras."""
    return SceneFrame(colors=colors, speed=speed, method=method, mode=mode,
                      direction=direction, main_light=main_light, extras=extras)


# All 73 scenes from NEEWER Home Cloud API
HOME_SCENES: List['HomeScene'] = [
    # === Naturel (24) ===
    HomeScene(1, "Arc-en-ciel", "Naturel", [_f([(0,100,100), (360,100,100)], 50, 2, 13, 1, 0)]),
    HomeScene(2, "Ciel etoile", "Naturel", [_f([(230,100,50), (230,40,100), (230,100,50), (230,100,50), (230,40,100), (230,100,50), (230,40,100), (230,100,50), (230,100,50), (230,40,100)], 60, 2, 13, 1, 0)]),
    HomeScene(3, "Flamme", "Naturel", [_f([(25,100,100), (10,100,50), (20,100,100), (30,70,100), (30,100,70), (20,100,50), (20,100,90), (30,100,90), (25,100,100), (10,100,70), (20,100,100), (30,70,70), (30,100,50), (20,100,85), (20,100,90)], 80, 2, 13, 1, 0)]),
    HomeScene(4, "Lever du soleil", "Naturel", [_f([(245,100,100), (245,100,100), (245,80,100), (245,60,100), (40,40,80), (40,60,100), (35,80,100), (30,100,100), (20,100,100), (10,100,100), (10,100,100), (20,100,100), (30,100,100), (40,80,100), (40,40,80), (40,20,80)], 45, 1, 11, 1, 0)]),
    HomeScene(5, "Coucher du soleil", "Naturel", [_f([(40,50,50), (40,60,60), (35,70,70), (35,80,80), (35,90,90), (35,100,100), (35,100,100), (30,100,100), (20,100,100), (20,100,100), (0,95,100), (0,95,100), (360,60,100), (220,80,100), (220,90,90), (360,60,60)], 40, 1, 11, 1, 0)]),
    HomeScene(6, "Fleurs de cerisier", "Naturel", [_fe([(355,60,100), (0,0,0), (355,60,100), (0,0,0), (60,30,100), (0,0,0), (350,60,100), (0,0,0), (352,50,95), (0,0,0), (60,30,100), (0,0,0), (350,60,100), (0,0,0), (355,60,100)], 30, 1, 14, 0, 0, {"bgH": 330, "bgL": 90, "bgS": 20, "dis": 0, "mul": 2, "src": 2})]),
    HomeScene(7, "Foret", "Naturel", [_f([(110,100,100), (110,80,60), (120,50,80), (130,100,100), (120,100,30), (130,100,100), (85,60,80), (110,100,100), (120,80,60), (120,50,80), (130,100,100), (120,100,30), (130,100,100)], 95, 1, 13, 1, 0)]),
    HomeScene(8, "Maree de fleurs", "Naturel", [_f([(340,90,80), (330,30,100), (335,65,100), (65,100,85), (335,80,100), (340,90,80), (75,100,70), (330,30,100), (340,90,80), (330,30,100), (335,65,100), (65,100,85), (335,80,100), (340,90,80), (75,100,70)], 30, 1, 4, 1, 0)]),
    HomeScene(9, "Glacier", "Naturel", [_fe([(205,100,100), (0,0,0), (200,80,100), (0,0,0), (200,80,100)], 20, 2, 14, 0, 0, {"bgH": 205, "bgL": 50, "bgS": 100, "dis": 0, "mul": 5, "src": 3}), _fe([(210,70,100), (0,0,0), (210,50,100), (0,0,0), (210,15,100)], 20, 2, 14, 0, 0, {"bgH": 205, "bgL": 50, "bgS": 100, "dis": 0, "mul": 5, "src": 3})]),
    HomeScene(10, "Vagues", "Naturel", [_f([(220,100,100), (220,100,100), (220,60,100), (220,50,60), (220,100,100), (220,100,100), (220,60,100), (220,50,60), (220,100,100), (220,100,100), (220,60,100), (220,50,60), (220,100,100), (220,100,100), (220,60,100)], 80, 1, 4, 1, 0), _f([(220,100,100), (220,100,100), (220,60,100), (220,50,100), (220,50,60), (220,50,90), (220,50,60), (220,50,50), (220,100,100), (220,100,100), (220,60,100), (220,50,100), (220,50,60), (220,50,90), (220,50,60)], 80, 1, 4, 1, 0), _f([(220,100,100), (220,100,100), (220,50,100), (220,100,100), (220,100,100), (220,60,100), (220,50,80), (220,50,60), (220,100,100), (220,100,100), (220,50,100), (220,100,100), (220,100,100), (220,60,100), (220,50,80)], 70, 1, 4, 1, 0)]),
    HomeScene(11, "Mer profonde", "Naturel", [_f([(200,100,100), (210,100,100), (220,100,100), (230,100,100), (240,100,100), (230,100,100), (210,100,100)], 20, 1, 1, 0, 0)]),
    HomeScene(12, "Luciole", "Naturel", [_f([(120,100,100), (120,100,30), (70,100,50), (120,100,30), (120,100,30), (70,100,100), (120,100,30), (120,100,100), (120,100,30), (120,100,30), (120,100,30), (70,100,50), (120,100,30), (70,100,100), (120,100,30), (120,100,30)], 30, 2, 13, 1, 0)]),
    HomeScene(13, "Reflets ondules", "Naturel", [_f([(195,100,100), (195,100,60), (195,100,20), (195,100,100), (195,100,80), (195,100,60), (195,100,30), (195,100,20), (195,100,100), (195,100,70), (195,100,50), (195,100,40), (195,100,30), (195,100,20), (195,100,10)], 60, 2, 13, 1, 0)]),
    HomeScene(14, "Vagues de Ble", "Naturel", [_f([(50,90,100), (35,90,100), (30,80,100), (35,80,100), (40,100,70), (35,80,100), (35,80,100), (35,90,100), (50,50,100), (40,90,100), (35,100,70), (50,90,100), (35,90,100), (50,50,100)], 80, 2, 13, 1, 0)]),
    HomeScene(15, "Etang de Lotus", "Naturel", [_f([(125,100,60), (120,100,80), (355,40,100), (60,30,100), (355,25,100), (125,100,60), (125,100,60), (125,100,60), (125,100,60), (355,25,100), (355,40,100), (60,30,100), (355,25,100), (125,100,60), (125,100,60)], 20, 1, 4, 1, 0), _f([(125,100,60), (125,100,60), (120,100,80), (355,25,100), (355,40,100), (120,100,80), (125,100,60), (60,30,100), (125,100,60), (125,100,60), (120,100,80), (355,25,100), (355,40,100), (120,100,80), (125,100,60)], 20, 1, 4, 1, 0), _f([(355,40,100), (355,25,100), (120,100,80), (125,100,60), (125,100,60), (60,30,100), (355,40,100), (125,100,60), (355,40,100), (355,5,100), (120,100,80), (125,100,60), (125,100,60), (60,30,100), (355,40,100)], 20, 1, 4, 1, 0)]),
    HomeScene(16, "Aurore", "Naturel", [_f([(200,100,30), (153,100,60), (165,100,70), (80,100,90), (80,100,90), (200,100,30), (215,100,80), (80,100,90)], 70, 2, 13, 1, 0)]),
    HomeScene(17, "Desert Gobi", "Naturel", [_f([(22,82,80), (73,16,100), (153,13,80), (38,32,100), (19,54,80), (97,12,80), (177,37,80), (50,26,80), (22,82,80), (73,16,100), (153,13,80), (38,32,100), (19,54,80), (97,12,80), (177,37,80)], 35, 2, 1, 0, 0), _f([(22,82,80), (153,13,80), (19,54,80), (177,37,80), (38,32,100), (73,16,100), (50,26,80), (97,12,80), (22,82,80), (153,13,80), (19,54,80), (177,37,80), (38,32,100), (73,16,100), (50,26,80)], 35, 2, 1, 0, 0)]),
    HomeScene(18, "Printemps", "Naturel", [_f([(130,100,80), (130,100,80), (300,80,100), (355,80,100), (130,100,60), (40,100,100), (130,100,70), (355,80,100), (130,100,80), (300,80,100), (130,100,70), (130,100,70), (130,80,60), (40,100,100), (130,100,70)], 45, 1, 4, 1, 0)]),
    HomeScene(19, "Ete", "Naturel", [_f([(50,100,100), (50,100,100), (190,100,70), (190,100,90), (190,100,100), (190,40,100), (190,100,90), (190,100,100), (190,40,100), (50,100,100), (190,100,70), (190,100,90), (190,100,100), (190,40,100), (190,100,90)], 80, 1, 4, 1, 0)]),
    HomeScene(20, "Automne", "Naturel", [_f([(25,90,100), (30,100,100), (30,100,100), (50,100,100), (35,100,100), (50,70,90), (10,100,100), (10,100,100), (25,90,100), (30,100,100), (25,90,100), (50,100,100), (50,100,100), (25,100,60)], 50, 2, 13, 1, 0)]),
    HomeScene(21, "Hiver", "Naturel", [_f([(220,100,100), (220,100,100), (220,100,30), (220,40,100), (220,100,100), (220,100,60), (220,100,30), (220,40,100), (220,100,100), (220,100,60), (220,100,30), (220,40,100), (220,100,100), (220,100,60), (220,100,30), (220,100,30)], 15, 1, 4, 1, 0)]),
    HomeScene(22, "Meteore", "Naturel", [_fe([(211,40,100)], 98, 1, 15, 1, 0, {"dE": 5, "dM": 0, "mir": 0, "seg": 1, "spc": 6, "tail": 6}), _fe([(211,40,100), (211,40,100)], 100, 1, 15, 1, 0, {"dE": 7, "dM": 0, "mir": 0, "seg": 1, "spc": 1, "tail": 5}), _fe([(211,40,100)], 95, 1, 15, 1, 0, {"dE": 5, "dM": 0, "mir": 0, "seg": 1, "spc": 1, "tail": 4})]),
    HomeScene(23, "Foudre", "Naturel", [_f([(220,60,8), (220,60,50)], 80, 6, 5, 0, 0), _f([(220,60,8), (220,60,50)], 85, 6, 5, 0, 0), _f([(220,60,100)], 75, 1, 1, 0, 0), _f([(220,60,8), (220,60,50)], 60, 6, 5, 0, 0), _f([(220,60,8), (220,60,8)], 70, 6, 5, 0, 0), _f([(220,60,8), (220,60,50)], 90, 6, 5, 0, 0), _f([(220,60,100)], 55, 1, 1, 0, 0), _f([(220,60,100)], 80, 1, 1, 0, 0)]),
    HomeScene(24, "Pluie torrentielle", "Naturel", [_f([(200,100,100), (200,100,85), (200,100,75), (200,100,60), (200,100,50), (200,100,40), (200,100,30), (200,100,20), (211,100,100), (211,100,60), (211,100,40), (211,100,100), (211,100,60), (211,100,40), (211,100,30)], 100, 1, 4, 1, 0), _f([(180,100,100), (180,100,75), (180,100,50), (180,100,20), (180,100,100), (180,100,75), (180,100,50), (180,100,20), (200,100,100), (200,100,85), (200,100,75), (200,100,60), (200,100,50), (200,100,40), (200,100,30)], 95, 1, 4, 1, 0), _f([(211,100,100), (211,100,60), (211,100,40), (211,100,100), (211,100,60), (211,100,40), (211,100,30), (180,100,100), (180,100,75), (180,100,50), (180,100,20), (180,100,100), (180,100,75), (180,100,50), (180,100,20)], 95, 1, 4, 1, 0)]),
    # === Vie (12) ===
    HomeScene(25, "Colore", "Vie", [_f([(0,100,100), (180,100,100), (360,100,100), (180,100,100)], 90, 1, 13, 1, 0)]),
    HomeScene(26, "Film", "Vie", [_f([(230,100,100), (230,40,100)], 25, 1, 11, 1, 0)]),
    HomeScene(27, "Tea Time", "Vie", [_f([(40,100,100), (40,25,100), (40,100,100), (40,25,100), (40,100,100), (40,25,100), (40,100,100), (40,25,100), (40,100,100), (40,25,100)], 40, 2, 13, 1, 0)]),
    HomeScene(28, "Reve", "Vie", [_f([(220,80,100), (335,60,100), (220,80,100), (335,60,100)], 60, 2, 13, 1, 0)]),
    HomeScene(29, "Loisirs", "Vie", [_f([(100,100,100), (45,100,100), (100,100,100), (45,100,100), (100,100,100), (45,100,100)], 50, 2, 13, 1, 0)]),
    HomeScene(30, "Technologie", "Vie", [_fe([(225,100,100)], 80, 1, 15, 1, 0, {"bgH": 225, "bgL": 100, "bgS": 0, "dE": 5, "dM": 1, "mir": 1, "seg": 6, "spc": 0, "tail": 2}), _fe([(225,100,100)], 80, 1, 15, 2, 0, {"bgH": 225, "bgL": 100, "bgS": 0, "dE": 5, "dM": 1, "mir": 1, "seg": 6, "spc": 0, "tail": 2})]),
    HomeScene(31, "Matin", "Vie", [_f([(210,100,100), (50,100,100), (210,100,100), (50,100,100), (210,100,100), (50,100,100)], 50, 2, 13, 1, 0)]),
    HomeScene(32, "Apres-midi", "Vie", [_f([(40,80,100), (35,95,100), (25,100,100), (35,95,100), (40,80,100), (45,50,100), (45,50,100), (45,50,100), (45,50,100), (45,50,100), (45,50,100), (45,50,100), (45,50,100), (45,50,100), (45,50,100), (45,50,100)], 50, 2, 13, 1, 0)]),
    HomeScene(33, "Feerie Lumineuse", "Vie", [_fe([(340,70,100), (0,0,0), (340,70,100), (0,0,0), (340,70,100), (0,0,0), (340,70,100)], 50, 1, 14, 0, 0, {"bgH": 60, "bgL": 100, "bgS": 100, "dis": 0, "mul": 1, "src": 5})]),
    HomeScene(34, "Romantique", "Vie", [_f([(310,100,30), (310,100,100), (285,100,30), (285,100,100), (270,100,30), (270,100,100), (285,100,30), (285,100,100)], 30, 1, 11, 1, 0)]),
    HomeScene(35, "Fraicheur Estivale", "Vie", [_f([(220,100,100), (220,100,100), (220,30,100), (220,30,100), (220,100,100), (220,100,100), (220,30,100), (220,30,100), (220,100,100), (220,100,100), (220,30,100), (220,30,100), (220,100,100), (220,100,100), (220,30,100), (220,30,100)], 50, 2, 13, 1, 0)]),
    HomeScene(36, "Paresseux", "Vie", [_f([(60,80,100), (100,80,100), (140,80,100), (180,80,100)], 30, 1, 11, 1, 0)]),
    # === Festival (7) ===
    HomeScene(37, "Fete", "Festival", [_f([(185,100,100), (120,100,100), (300,100,100), (360,100,100), (60,100,100), (35,100,100)], 80, 1, 1, 0, 0)]),
    HomeScene(38, "Anniversaire", "Festival", [_fe([(0,100,100), (35,100,100), (60,100,100), (120,100,100), (180,100,100), (220,100,100), (270,100,100), (320,100,100)], 60, 6, 12, 0, 0, {"cycleTimes": 5, "longestSeg": 5, "minOccur": 5})]),
    HomeScene(39, "Bal de promo", "Festival", [_f([(20,100,90), (260,100,90), (220,100,100), (35,100,95), (250,100,90), (50,100,100), (20,100,90), (10,100,95), (320,100,100), (320,100,100), (245,100,95), (35,100,95), (290,100,90), (50,100,100), (20,100,90)], 80, 1, 1, 0, 0)]),
    HomeScene(40, "Noel", "Festival", [_f([(0,100,100), (120,100,80), (120,100,80), (0,100,100), (120,100,80), (0,100,100), (0,100,100), (120,100,80), (120,100,80), (0,100,100), (120,100,80), (0,100,100), (120,100,80), (120,100,80), (0,100,100)], 50, 1, 4, 1, 0)]),
    HomeScene(41, "Halloween", "Festival", [_fe([(30,100,100), (30,100,100), (60,100,100), (270,100,90), (30,100,100), (270,100,90), (60,100,100), (30,100,100)], 70, 2, 16, 1, 0, {"gap": 5, "mir": 0, "seg": 8})]),
    HomeScene(42, "Nouvelle annee", "Festival", [_f([(0,100,100), (0,100,100), (0,100,100), (40,100,100), (40,100,100), (160,100,60), (0,100,100), (0,100,100), (40,100,100), (40,100,100), (0,100,100), (40,100,100), (40,100,100), (160,100,60), (0,100,100)], 60, 1, 4, 1, 0)]),
    HomeScene(43, "Feux d'artifice", "Festival", [_fe([(30,100,100), (120,100,100), (10,100,100)], 100, 1, 15, 1, 0, {"dE": 7, "dM": 0, "mir": 0, "seg": 1, "spc": 3, "tail": 10}), _f([(30,100,100), (120,100,100), (10,100,100)], 70, 1, 1, 0, 0), _fe([(195,100,100), (280,100,100), (175,100,100)], 100, 1, 15, 1, 0, {"dE": 7, "dM": 0, "mir": 0, "seg": 1, "spc": 3, "tail": 10}), _f([(195,100,100), (280,100,100), (175,100,100)], 70, 1, 1, 0, 0)]),
    # === Emotion (8) ===
    HomeScene(44, "Doux", "Emotion", [_f([(340,70,100), (340,20,100), (340,70,100), (340,20,100), (340,70,100), (340,20,100), (340,70,100), (340,20,100)], 50, 2, 13, 1, 0)]),
    HomeScene(45, "Enthousiasme", "Emotion", [_fe([(0,100,100), (30,100,100)], 80, 1, 15, 1, 0, {"bgH": 0, "bgL": 100, "bgS": 0, "dE": 4, "dM": 1, "mir": 1, "seg": 6, "spc": 0, "tail": 2})]),
    HomeScene(46, "Confortable", "Emotion", [_f([(180,100,100), (120,100,100), (180,100,100), (120,100,100), (180,100,100), (120,100,100)], 50, 2, 13, 1, 0)]),
    HomeScene(47, "Mystere", "Emotion", [_f([(240,100,30), (270,100,100), (240,100,30), (270,100,100)], 40, 2, 13, 1, 0)]),
    HomeScene(48, "Joyeux", "Emotion", [_fe([(15,60,100), (40,100,100), (35,50,100), (65,100,100), (85,100,100), (85,50,100), (185,80,100), (220,100,100)], 90, 2, 16, 1, 0, {"gap": 0, "mir": 0, "seg": 5})]),
    HomeScene(49, "Melancolique", "Emotion", [_f([(250,100,40), (190,100,70), (250,100,40), (190,100,70), (250,100,40), (190,100,70), (250,100,40), (190,100,70), (250,100,40), (190,100,70)], 40, 2, 13, 1, 0)]),
    HomeScene(50, "Excite", "Emotion", [_fe([(30,100,100), (30,70,100), (45,100,100), (220,50,100), (220,100,100), (200,50,100), (30,50,100)], 85, 1, 15, 2, 0, {"bgH": 0, "bgL": 100, "bgS": 0, "dE": 1, "dM": 1, "mir": 1, "seg": 6, "spc": 0, "tail": 1})]),
    HomeScene(51, "Battement de coeur", "Emotion", [_f([(0,100,100)], 30, 1, 1, 0, 0), _f([(0,20,100), (0,30,100), (0,40,100), (0,50,100), (0,65,100), (0,80,100), (0,100,100), (0,100,100), (0,80,100), (0,65,100), (0,50,100), (0,40,100), (0,30,100), (0,20,100)], 70, 2, 1, 0, 0), _f([(0,100,100), (0,80,100), (0,65,100), (0,50,100), (0,40,100), (0,30,100), (0,20,100), (0,20,100), (0,30,100), (0,40,100), (0,50,100), (0,65,100), (0,80,100), (0,100,100)], 70, 2, 1, 0, 0)]),
    # === Sport (22) ===
    HomeScene(52, "Dallas Football", "Sport", [_fe([(215,95,30), (215,0,70), (215,100,30), (215,0,70)], 80, 1, 16, 1, 0, {"gap": 1, "mir": 1, "seg": 4}), _fe([(215,0,70), (215,95,30), (215,0,70), (215,95,30)], 80, 1, 16, 2, 0, {"gap": 1, "mir": 1, "seg": 4}), _fe([(215,95,30), (215,0,70)], 100, 1, 16, 1, 0, {"gap": 1, "mir": 0, "seg": 1}), _fe([(215,0,70), (215,95,30)], 100, 1, 16, 2, 0, {"gap": 1, "mir": 0, "seg": 1})]),
    HomeScene(53, "New England Football", "Sport", [_f([(0,100,50), (220,100,50), (0,0,80), (0,100,50), (220,100,50), (0,0,80)], 50, 1, 4, 1, 0), _f([(0,0,80), (220,100,50), (0,100,50), (0,0,80), (220,100,50), (0,100,50)], 50, 1, 4, 2, 0), _f([(0,100,50), (220,100,50), (0,0,80), (0,100,50), (220,100,50), (0,0,80)], 70, 6, 5, 0, 0)]),
    HomeScene(54, "Kansas City Football", "Sport", [_fe([(350,100,70), (350,0,50), (350,100,70), (350,0,50)], 90, 1, 15, 1, 0, {"bgH": 0, "bgL": 0, "bgS": 0, "dE": 2, "dM": 0, "mir": 1, "seg": 2, "spc": 1, "tail": 5}), _fe([(350,100,70), (350,0,50), (350,100,70), (350,0,50)], 90, 1, 16, 1, 0, {"gap": 1, "mir": 1, "seg": 2}), _fe([(350,0,50), (350,100,70), (350,0,50), (350,100,70)], 90, 1, 15, 2, 0, {"bgH": 0, "bgL": 0, "bgS": 0, "dE": 2, "dM": 0, "mir": 1, "seg": 2, "spc": 1, "tail": 5}), _fe([(350,0,50), (350,100,70), (350,0,50), (350,100,70)], 90, 1, 16, 2, 0, {"gap": 1, "mir": 1, "seg": 2}), _fe([(350,100,70), (350,0,50), (350,100,70), (350,0,50), (350,100,70)], 70, 6, 12, 0, 0, {"cycleTimes": 5, "longestSeg": 3, "minOccur": 3})]),
    HomeScene(55, "Madrid Soccer", "Sport", [_f([(0,100,80), (45,100,80), (0,100,80), (45,100,80)], 50, 2, 13, 1, 0), _f([(0,100,80), (0,100,0), (0,100,80)], 70, 1, 13, 1, 0), _f([(45,100,80), (45,100,0), (45,100,80)], 70, 1, 13, 1, 0), _f([(210,100,80), (210,100,0), (210,100,80)], 70, 1, 13, 1, 0), _f([(45,100,80), (0,100,80), (45,100,80), (0,100,80)], 50, 1, 11, 1, 0)]),
    HomeScene(56, "Barcelona Soccer", "Sport", [_f([(220,100,50), (0,100,50), (50,100,70), (220,100,50), (0,100,50), (50,100,70)], 50, 1, 4, 1, 0), _f([(50,100,70), (0,100,50), (220,100,50)], 70, 6, 5, 0, 0), _f([(50,100,70), (0,100,50), (220,100,50)], 50, 1, 4, 2, 0), _f([(0,100,50), (50,100,70), (220,100,50)], 70, 6, 5, 0, 0)]),
    HomeScene(57, "Manchester Soccer", "Sport", [_f([(0,100,70), (0,100,20), (50,100,80), (50,100,20)], 40, 2, 13, 1, 0), _f([(0,100,70), (0,100,20), (50,100,80), (50,100,20)], 40, 2, 13, 1, 0), _f([(0,100,70), (50,100,80)], 55, 6, 5, 0, 0), _f([(0,100,70), (50,100,80), (0,100,70), (50,100,80)], 40, 1, 13, 1, 0), _f([(50,100,80), (0,100,70)], 55, 6, 5, 0, 0)]),
    HomeScene(58, "Paris Soccer", "Sport", [_fe([(220,100,30), (0,100,50), (220,100,30), (0,100,50)], 90, 1, 16, 1, 0, {"gap": 1, "mir": 1, "seg": 2}), _fe([(0,100,50), (220,100,30)], 100, 1, 16, 2, 0, {"gap": 1, "mir": 0, "seg": 1}), _fe([(0,100,50), (220,100,30), (0,100,50), (220,100,30)], 90, 1, 16, 2, 0, {"gap": 1, "mir": 1, "seg": 2}), _fe([(220,100,30), (0,100,50)], 100, 1, 16, 1, 0, {"gap": 1, "mir": 0, "seg": 1}), _fe([(0,100,50), (220,100,30)], 85, 1, 16, 1, 0, {"gap": 1, "mir": 1, "seg": 4}), _fe([(220,100,30), (0,100,50)], 85, 1, 16, 2, 0, {"gap": 1, "mir": 1, "seg": 4})]),
    HomeScene(59, "Munich Soccer", "Sport", [_f([(0,100,70), (220,100,70), (0,100,70), (220,100,70)], 50, 1, 4, 1, 0), _f([(0,100,70), (220,100,70), (0,100,70), (220,100,70)], 5, 1, 17, 0, 0), _f([(0,100,70), (220,100,70), (0,100,70)], 5, 1, 17, 0, 0), _f([(220,100,70), (0,100,70)], 5, 1, 17, 0, 0), _f([(220,100,70), (0,100,70), (220,100,70), (0,100,70)], 70, 6, 5, 0, 0)]),
    HomeScene(60, "Los Angeles Basketball", "Sport", [_f([(45,100,70), (280,100,70), (45,100,70), (280,100,70)], 50, 1, 4, 1, 0), _f([(280,100,70), (45,100,70)], 70, 6, 5, 0, 0), _f([(280,100,70), (45,100,70), (280,100,70), (45,100,70)], 50, 1, 4, 1, 0), _f([(45,100,70), (280,100,70)], 70, 6, 5, 0, 0)]),
    HomeScene(61, "Golden State Basketball", "Sport", [_fe([(210,100,50), (47,100,70), (210,100,50), (47,100,70)], 95, 1, 16, 2, 0, {"gap": 1, "mir": 1, "seg": 2}), _fe([(47,100,70), (210,100,50)], 80, 1, 16, 1, 0, {"gap": 1, "mir": 1, "seg": 4}), _fe([(47,100,70), (210,100,50)], 95, 1, 16, 2, 0, {"gap": 1, "mir": 1, "seg": 2}), _fe([(210,100,50), (47,100,70), (210,100,50), (47,100,70)], 80, 1, 16, 1, 0, {"gap": 1, "mir": 1, "seg": 4})]),
    HomeScene(62, "Chicago Basketball", "Sport", [_f([(345,90,80), (345,90,20), (345,90,80), (345,90,20)], 40, 2, 13, 1, 0), _f([(345,90,80), (345,90,20), (345,90,80), (345,90,20)], 40, 2, 13, 1, 0), _f([(345,90,80), (345,90,20), (345,90,80), (345,90,20)], 30, 1, 11, 1, 0), _f([(345,90,20), (345,90,80), (345,90,20), (345,90,80)], 60, 1, 13, 1, 0), _f([(345,90,80), (345,90,20), (345,90,80), (345,90,20)], 30, 1, 11, 1, 0)]),
    HomeScene(63, "Boston Basketball", "Sport", [_fe([(120,100,30), (10,70,40), (40,100,45), (120,100,30), (10,70,40)], 80, 1, 16, 1, 0, {"gap": 1, "mir": 1, "seg": 4}), _fe([(10,70,40), (120,100,30), (40,100,45), (10,70,40), (120,100,30), (40,100,45)], 70, 6, 12, 0, 0, {"cycleTimes": 6, "longestSeg": 3, "minOccur": 3}), _fe([(40,100,45), (120,100,30), (10,70,40), (40,100,45), (120,100,30)], 80, 1, 16, 2, 0, {"gap": 1, "mir": 1, "seg": 4}), _f([(120,100,30), (10,70,40), (40,100,45), (120,100,30), (10,70,40)], 75, 6, 5, 0, 0)]),
    HomeScene(64, "New York Baseball", "Sport", [_f([(225,100,30), (225,15,100), (225,100,30), (225,15,100), (225,100,30), (225,15,100)], 50, 2, 11, 1, 0), _f([(225,100,30), (225,100,30), (225,15,100), (225,15,100), (225,15,100), (225,100,30), (225,15,100), (225,100,30)], 55, 2, 13, 1, 0), _f([(225,100,30), (225,100,30), (225,15,100), (225,15,100), (225,15,100), (225,100,30), (225,15,100), (225,100,30)], 55, 2, 13, 1, 0)]),
    HomeScene(65, "Los Angeles Baseball", "Sport", [_f([(210,0,100), (210,100,30), (210,100,30), (210,100,0), (210,100,0), (210,100,0)], 65, 2, 13, 1, 0), _f([(210,100,30), (210,0,100), (210,100,30), (210,100,30), (210,100,0), (210,100,0), (210,100,0)], 65, 2, 13, 1, 0), _f([(210,0,100), (210,100,30), (210,100,30), (210,100,0), (210,100,0), (210,100,0)], 90, 2, 13, 2, 0), _f([(210,100,30), (210,0,100), (210,100,30), (210,100,0), (210,100,0), (210,100,0)], 65, 2, 13, 1, 0), _f([(210,100,30), (210,0,100), (210,100,30), (210,100,0), (210,100,0), (210,100,0)], 65, 2, 13, 1, 0), _f([(210,0,100), (210,100,30), (210,100,30), (210,100,0), (210,100,0), (210,100,0)], 90, 2, 13, 2, 0)]),
    HomeScene(66, "Boston Baseball", "Sport", [_f([(0,100,35), (0,100,10), (0,0,100), (0,100,35)], 45, 2, 13, 1, 0), _f([(220,100,30), (220,100,10), (220,0,100), (220,100,30)], 45, 2, 13, 2, 0)]),
    HomeScene(67, "Chicago Baseball", "Sport", [_fe([(0,100,60), (215,100,36), (0,100,60), (215,100,36)], 60, 1, 15, 1, 0, {"bgH": 0, "bgL": 100, "bgS": 0, "dE": 2, "dM": 0, "mir": 0, "seg": 3, "spc": 1, "tail": 3}), _fe([(0,100,60), (0,100,60)], 60, 1, 15, 2, 0, {"bgH": 0, "bgL": 0, "bgS": 0, "dE": 2, "dM": 0, "mir": 1, "seg": 3, "spc": 0, "tail": 3}), _fe([(215,100,36), (215,100,36)], 60, 1, 15, 1, 0, {"bgH": 0, "bgL": 0, "bgS": 0, "dE": 2, "dM": 0, "mir": 1, "seg": 3, "spc": 0, "tail": 3})]),
    HomeScene(68, "San Francisco Baseball", "Sport", [_fe([(28,100,100)], 80, 1, 15, 1, 0, {"bgH": 0, "bgL": 0, "bgS": 0, "dE": 2, "dM": 1, "mir": 1, "seg": 3, "spc": 0, "tail": 5}), _fe([(28,100,100)], 80, 1, 15, 2, 0, {"bgH": 0, "bgL": 0, "bgS": 0, "dE": 2, "dM": 1, "mir": 1, "seg": 3, "spc": 0, "tail": 5})]),
    HomeScene(69, "Toronto Hockey", "Sport", [_f([(220,100,50), (220,100,10), (220,100,50), (220,100,10)], 55, 2, 13, 1, 0), _f([(220,100,50), (220,100,10), (220,100,50), (220,100,10)], 55, 2, 13, 2, 0)]),
    HomeScene(70, "Montreal Hockey", "Sport", [_f([(215,100,35), (0,0,100), (0,100,50), (0,100,50), (0,0,100), (215,100,35), (0,0,100), (0,100,50), (0,100,50), (0,0,100), (215,100,35)], 50, 1, 4, 1, 0), _fe([(215,100,35), (0,0,100), (0,100,50), (0,100,50), (0,0,100), (215,100,35), (0,0,100), (0,100,50), (0,100,50), (0,0,100), (215,100,35)], 70, 6, 12, 0, 0, {"cycleTimes": 5, "longestSeg": 3, "minOccur": 3}), _f([(215,100,35), (0,100,50)], 70, 1, 1, 0, 0)]),
    HomeScene(71, "Chicago Hockey", "Sport", [_fe([(0,100,100), (50,100,100), (155,100,40), (30,100,100)], 65, 1, 16, 1, 0, {"gap": 1, "mir": 0, "seg": 4}), _f([(155,100,35), (50,100,100), (0,100,100), (30,100,100), (0,100,100), (155,100,35)], 65, 1, 4, 1, 0), _f([(0,100,100), (30,100,100), (50,100,100), (155,100,40), (30,100,100), (155,100,40)], 65, 1, 4, 2, 0)]),
    HomeScene(72, "New York Hockey", "Sport", [_f([(220,100,40), (220,0,100), (220,100,40), (220,0,100), (0,100,40), (220,100,40), (220,0,100), (220,100,40)], 60, 1, 4, 1, 0), _f([(220,0,100), (220,100,40), (220,0,100), (220,100,40), (0,100,40), (0,100,40), (220,0,100), (220,100,40)], 60, 1, 4, 2, 0)]),
    HomeScene(73, "Las Vegas Hockey", "Sport", [_f([(45,100,75), (45,100,20), (45,100,75), (45,100,20)], 50, 1, 13, 1, 0), _f([(45,100,65), (45,100,65)], 30, 1, 1, 0, 0)]),
]


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

