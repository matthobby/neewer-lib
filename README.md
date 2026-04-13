# NeewerLite v0.3.0

Python library for controlling **all Neewer lights** via Bluetooth LE:
- **Studio lights** (RGB62, RGB660, SL-80, GL1, etc.) — standard 0x78 protocol, 17 FX effects
- **Home strips** (NH-PD, NS02) — Neewer Home 0x7A protocol, music mode

## Features
- **Auto-detection** : detects protocol (Studio vs Home) from device name
- **Power control** : on/off with state sync
- **RGB / HSI** : hue, saturation, brightness
- **CCT** : color temperature 2500K-8500K with optional GM tint
- **17 FX effects** (studio) : lightning, paparazzi, cop car, candlelight, hue/cct loops, etc.
- **Music mode** (home strips) : microphone-reactive lighting
- **Scanner** : BLE discovery with signal strength sorting

## Installation

```bash
pip install neewerlite
```

From source:
```bash
pip install -e .
```

## Quick Start

### Scan for lights
```python
import asyncio
from neewerlite import NeewerScanner

async def main():
    devices = await NeewerScanner.scan()
    for d in devices:
        print(f"{d.name} ({d.address})")

asyncio.run(main())
```

### Control a studio light (RGB62, SL-80, etc.)
```python
import asyncio
from neewerlite import NeewerLight, NeewerEffect

async def main():
    light = NeewerLight("AA:BB:CC:DD:EE:FF", name="NEEWER-RGB62")
    await light.connect()

    # Power
    await light.turn_on()

    # RGB color (hue=0-360, saturation=0-100, brightness=0-100)
    await light.set_rgb(210, 100, 80)

    # White temperature (Kelvin, brightness, GM tint)
    await light.set_cct(5500, 80, gm=50)

    # FX effect with full parameters
    await light.set_effect(NeewerEffect.COP_CAR, brightness=80, color_mode=2, speed=7)
    await light.set_effect(NeewerEffect.CANDLELIGHT, brightness_min=10, brightness_max=80, cct=3200)
    await light.set_effect(NeewerEffect.HUE_LOOP, brightness=60, hue_min=0, hue_max=360, speed=5)

    await light.turn_off()
    await light.disconnect()

asyncio.run(main())
```

### Control a Home strip (NS02, NH-PD)
```python
import asyncio
from neewerlite import NeewerLight

async def main():
    light = NeewerLight("AA:BB:CC:DD:EE:FF", name="NS02_XXXX")
    await light.connect()

    await light.turn_on()

    # Color (hue, saturation, brightness 0-100 — auto-scaled to 0-1000)
    await light.set_rgb(120, 100, 80)

    # White temperature
    await light.set_cct(4500, 80)

    # Music reactive mode
    await light.set_music_mode(brightness=50, mode_id=0, speed=50, sensitivity=80)

    await light.disconnect()

asyncio.run(main())
```

## All 17 FX Effects (Studio Lights)

| # | Effect | Parameters |
|---|--------|-----------|
| 1 | Lightning | brightness, cct, speed |
| 2 | Paparazzi | brightness, cct, gm, speed |
| 3 | Faulty Bulb | brightness, cct, gm, speed |
| 4 | Explosion | brightness, cct, gm, speed, ember |
| 5 | Welding | brightness_min, brightness_max, cct, gm, speed |
| 6 | CCT Flash | brightness, cct, gm, speed |
| 7 | Hue Flash | brightness, hue, saturation, speed |
| 8 | CCT Pulse | brightness, cct, gm, speed |
| 9 | Hue Pulse | brightness, hue, saturation, speed |
| 10 | Cop Car | brightness, color_mode (0-4), speed |
| 11 | Candlelight | brightness_min, brightness_max, cct, gm, speed, ember |
| 12 | Hue Loop | brightness, hue_min, hue_max, speed |
| 13 | CCT Loop | brightness, cct_min, cct_max, speed |
| 14 | Brightness Loop | brightness_min, brightness_max, cct, hue, speed, cct_hsi_mode |
| 15 | TV Screen | brightness_min, brightness_max, cct, gm, speed |
| 16 | Fireworks | brightness, color_mode (0-2), speed, ember |
| 17 | Party | brightness, color_mode (0-2), speed |

### Using `set_effect()` with kwargs
```python
await light.set_effect(NeewerEffect.EXPLOSION, brightness=80, cct=5500, gm=50, speed=7, ember=8)
```

### Using individual FX functions (low-level)
```python
await light.fx_cop_car(bri=80, color=2, speed=7)
await light.fx_candlelight(bri_min=10, bri_max=80, cct=3200, gm=50, speed=5, ember=5)
```

### Direct protocol access
```python
from neewerlite import fx_cop_car, fx_lightning, build_fx, NeewerEffect, FXParams

# Build raw packets
packet = fx_cop_car(bri=80, color=2, speed=7)
packet = build_fx(NeewerEffect.LIGHTNING, FXParams(brightness=80, cct=5500, speed=8))
```

## Cop Car Color Modes
| Mode | Colors |
|------|--------|
| 0 | Red |
| 1 | Blue |
| 2 | Red + Blue |
| 3 | White + Blue |
| 4 | Red + Blue + White |

## BLE UUIDs
- Service: `69400001-b5a3-f393-e0a9-e50e24dcca99`
- Write: `69400002-b5a3-f393-e0a9-e50e24dcca99`
- Notify: `69400003-b5a3-f393-e0a9-e50e24dcca99`

## Device Name Patterns
- **Studio**: `NEEWER-*`, `RGB62*`, `RGB660*`, `SL-*`, `GL1*`, `ZN-*`, `NW-*`
- **Home**: `NH-*`, `NS02*`

## License
MIT
