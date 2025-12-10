import asyncio
from typing import List, Dict, Optional
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from . import protocol

class NeewerScanner:
    """Helper to discover Neewer lights that might be hidden or unnamed."""

    @staticmethod
    async def scan(timeout: float = 5.0) -> List[BLEDevice]:
        """
        Scans for devices exposing the Neewer Service or having a Neewer-like name.
        Returns a list of BLEDevice objects.
        """
        found_devices: List[BLEDevice] = []
        
        def filter_device(device: BLEDevice, adv: AdvertisementData):
            # 1. Check Service UUID (Most reliable)
            if protocol.UUID_SERVICE in adv.service_uuids:
                return True
            
            # 2. Check Name (Fallback)
            name = device.name or adv.local_name or ""
            if any(k in name.upper() for k in ["NEEWER", "RGB62", "RGB660", "SL-", "GL1", "ZN-"]):
                return True
                
            return False

        # Use BleakScanner to find devices
        devices_dict = await BleakScanner.discover(return_adv=True, timeout=timeout)
        
        found_candidates: List[tuple[BLEDevice, int]] = []
        
        for d, adv in devices_dict.values():
            if filter_device(d, adv):
                found_candidates.append((d, adv.rssi))
                
        # Sort by signal strength (strongest first)
        found_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Return only the device objects
        return [c[0] for c in found_candidates]

    @staticmethod
    async def find_first(timeout: float = 5.0) -> Optional[BLEDevice]:
        """Returns the first (strongest) Neewer light found."""
        devices = await NeewerScanner.scan(timeout)
        return devices[0] if devices else None
