# NeewerLite (v0.2.2)

A Python library to control Neewer RGB lights (specifically tested on RGB62/RGB660 Pro models) via Bluetooth Low Energy (BLE).

## Features
- **Auto-Handshake**: Handles the connection handshake automatically.
- **Power Control**: Turn ON/OFF.
- **RGB Control**: Set Hue, Saturation, Brightness.
- **CCT Control**: Set Color Temperature (3200K - 5600K).
- **Effects (FX)**: [EXPERIMENTAL] Trigger built-in scenes (may be unreliable).
- **Scanner**: Intelligent discovery of Neewer devices.

## Installation

### Standard Installation (PyPI)
Since the library is published on PyPI, you can simply run:
```bash
pip install neewerlite==0.2.2
```

### From Source (Local Development)
If you have cloned the repository:
```bash
pip install -e .
```


## Usage

### 1. Discovering Lights
Neewer lights often don't show up with their real names in system scans. Use the scanner helper:

```python
import asyncio
from neewerlite import NeewerScanner

async def scan():
    print("Scanning...")
    devices = await NeewerScanner.scan()
    for d in devices:
        print(f"Found: {d.name} ({d.address})")

if __name__ == "__main__":
    asyncio.run(scan())
```

### 2. Controlling a Light
```python
import asyncio
from neewerlite import NeewerLight, NeewerEffect

ADDRESS = "AA:BB:CC:DD:EE:FF"  # Your Light's UUID

async def main():
    light = NeewerLight(ADDRESS)
    await light.connect()
    
    # Turn Red
    await light.set_rgb(0, 100, 50)
    
    # Trigger "Police Car" effect
    await light.set_effect(NeewerEffect.COP_CAR, 50)
    
    # Turn Off
    await light.set_power(False)

if __name__ == "__main__":
    asyncio.run(main())
```

## Available Effects
> **Note**: Effects are currently marked as **EXPERIMENTAL**. They may not work reliably on all firmware versions.

- `COP_CAR` (1)
- `AMBULANCE` (2)
- `FIRE_TRUCK` (3)
- `FIREWORKS` (4)
- `PARTY` (5)
- `CANDLELIGHT` (6)
- `LIGHTNING` (7)
- `PAPARAZZI` (8)
- `TV_SCREEN` (9)
