from .client import NeewerLight
from .scanner import NeewerScanner
from .protocol import (
    NeewerEffect, SimpleFX, PoliceColor, FXParams,
    build_fx, build_packet, calculate_checksum,
    # Standard commands
    cmd_power, cmd_rgb, cmd_cct, cmd_cct_gm, cmd_effect_simple,
    cmd_query_status, cmd_query_channel,
    # Extended FX (17 effects)
    fx_lightning, fx_paparazzi, fx_faulty_bulb, fx_explosion, fx_welding,
    fx_cct_flash, fx_hue_flash, fx_cct_pulse, fx_hue_pulse,
    fx_cop_car, fx_candlelight, fx_hue_loop, fx_cct_loop,
    fx_brightness_loop, fx_tv_screen, fx_fireworks, fx_party,
    # Neewer Home (NH/NS02)
    home_power_on, home_power_off, home_query_all,
    home_set_lighting, home_set_color, home_music_mode,
    # Home scenes
    HomeScene, SceneFrame, HOME_SCENES,
    # Detection
    is_neewer_home, is_neewer_studio,
    # Constants
    UUID_SERVICE, UUID_WRITE, UUID_NOTIFY,
)
from .exceptions import NeewerError, ConnectionError, ProtocolError

__all__ = [
    # Main classes
    "NeewerLight", "NeewerScanner",
    # Enums & dataclasses
    "NeewerEffect", "SimpleFX", "PoliceColor", "FXParams",
    # Protocol helpers
    "build_fx", "build_packet", "calculate_checksum",
    # Standard commands
    "cmd_power", "cmd_rgb", "cmd_cct", "cmd_cct_gm", "cmd_effect_simple",
    "cmd_query_status", "cmd_query_channel",
    # Extended FX
    "fx_lightning", "fx_paparazzi", "fx_faulty_bulb", "fx_explosion", "fx_welding",
    "fx_cct_flash", "fx_hue_flash", "fx_cct_pulse", "fx_hue_pulse",
    "fx_cop_car", "fx_candlelight", "fx_hue_loop", "fx_cct_loop",
    "fx_brightness_loop", "fx_tv_screen", "fx_fireworks", "fx_party",
    # Neewer Home
    "home_power_on", "home_power_off", "home_query_all",
    "home_set_lighting", "home_set_color", "home_music_mode",
    # Home scenes
    "HomeScene", "SceneFrame", "HOME_SCENES",
    # Detection
    "is_neewer_home", "is_neewer_studio",
    # Constants
    "UUID_SERVICE", "UUID_WRITE", "UUID_NOTIFY",
    # Exceptions
    "NeewerError", "ConnectionError", "ProtocolError",
]
__version__ = "0.3.1"
