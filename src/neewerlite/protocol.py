from typing import List
from enum import IntEnum

# Constants
UUID_SERVICE = "69400001-b5a3-f393-e0a9-e50e24dcca99"
UUID_WRITE = "69400002-b5a3-f393-e0a9-e50e24dcca99"
UUID_NOTIFY = "69400003-b5a3-f393-e0a9-e50e24dcca99"

# Magic Packets
CMD_HEADER = 0x78
HANDSHAKE_QUERY = [0x78, 0x85, 0x00, 0xFD]

class NeewerEffect(IntEnum):
    COP_CAR = 1
    AMBULANCE = 2
    FIRE_TRUCK = 3
    FIREWORKS = 4
    PARTY = 5
    CANDLELIGHT = 6
    LIGHTNING = 7
    PAPARAZZI = 8
    TV_SCREEN = 9

def calculate_checksum(data: List[int]) -> int:
    """Calculates the Neewer simple checksum (sum & 0xFF)."""
    return sum(data) & 0xFF

def build_packet(payload: List[int]) -> bytearray:
    """Appends checksum and converts to bytearray."""
    checksum = calculate_checksum(payload)
    return bytearray(payload + [checksum])

def cmd_power(is_on: bool) -> bytearray:
    """
    Constructs Power Command.
    ON:  [0x78, 0x81, 0x01, 0x01]
    OFF: [0x78, 0x81, 0x01, 0x02]
    """
    val = 0x01 if is_on else 0x02
    return build_packet([CMD_HEADER, 0x81, 0x01, val])

def cmd_rgb(hue: int, sat: int, bri: int) -> bytearray:
    """
    Constructs HSI Color Command.
    Structure: [0x78, 0x86, 0x04, HueLo, HueHi, Sat, Bri]
    """
    hue = int(hue) % 360
    sat = max(0, min(100, int(sat)))
    bri = max(0, min(100, int(bri)))
    
    hue_lo = hue & 0xFF
    hue_hi = (hue >> 8) & 0xFF
    
    return build_packet([CMD_HEADER, 0x86, 0x04, hue_lo, hue_hi, sat, bri])

def cmd_cct(temp_k: int, bri: int) -> bytearray:
    """
    Constructs CCT (Color Temp) Command.
    Structure: [0x78, 0x87, 0x02, Bri, CCT_Val]
    Range: 3200K - 5600K -> 32 - 56.
    """
    if temp_k > 100:
        cct_val = int(temp_k / 100)
    else:
        cct_val = int(temp_k)
        
    cct_val = max(32, min(56, cct_val))
    bri = max(0, min(100, int(bri)))
    
    return build_packet([CMD_HEADER, 0x87, 0x02, bri, cct_val])

def cmd_effect(effect_id: int, bri: int) -> bytearray:
    """
    [EXPERIMENTAL] Constructs FX Command.
    NOTE: Currently untested/unreliable.
    RGB62 appears to use 0x85 for Scene Mode.
    Structure: [0x78, 0x85, 0x02, EffectID, Bri]
    """
    bri = max(0, min(100, int(bri)))
    effect_id = max(1, min(18, int(effect_id))) # RGB62 has up to 18 modes?
    
    return build_packet([CMD_HEADER, 0x88, 0x02, effect_id, bri])
