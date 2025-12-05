"""
Device Manager - Android Device Discovery and Management Tools
Provides LangChain tools for listing, selecting, and querying Android devices.
"""

from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from .adb_client import ADBClient
import json


class DeviceManager:
    """Manager for Android device operations via ADB."""
    
    def __init__(self):
        self.adb = ADBClient()
    
    def _get_device_properties(self, device_serial: str) -> Dict[str, Any]:
        """Get comprehensive device properties."""
        props = {}
        
        # Basic device info
        prop_commands = {
            'manufacturer': 'ro.product.manufacturer',
            'model': 'ro.product.model',
            'brand': 'ro.product.brand',
            'device': 'ro.product.device',
            'android_version': 'ro.build.version.release',
            'sdk_version': 'ro.build.version.sdk',
            'build_id': 'ro.build.id',
            'serial': 'ro.serialno',
        }
        
        for key, prop in prop_commands.items():
            result = self.adb.shell(f"getprop {prop}", device_serial)
            props[key] = result.strip() if result else "Unknown"
        
        return props
    
    def _get_device_status(self, device_serial: str) -> Dict[str, Any]:
        """Get device status information."""
        status = {}
        
        # Battery info
        battery = self.adb.shell("dumpsys battery", device_serial)
        if battery:
            for line in battery.split('\n'):
                if 'level:' in line:
                    status['battery_level'] = line.split(':')[1].strip()
                elif 'status:' in line:
                    status['battery_status'] = line.split(':')[1].strip()
        
        # Screen status
        screen = self.adb.shell("dumpsys power | grep 'Display Power'", device_serial)
        status['screen_on'] = 'ON' if 'state=ON' in screen else 'OFF'
        
        # WiFi status
        wifi = self.adb.shell("dumpsys wifi | grep 'Wi-Fi is'", device_serial)
        status['wifi_enabled'] = 'enabled' in wifi.lower()
        
        return status


# Initialize global device manager
_device_manager = DeviceManager()


@tool
def list_android_devices() -> str:
    """
    List all connected Android devices with their serial numbers and basic info.
    
    Returns a formatted list of all Android devices connected via ADB.
    Use this tool when you need to see what devices are available.
    
    Returns:
        str: JSON string containing list of devices with serial numbers and models
    """
    devices = _device_manager.adb.get_devices()
    
    if not devices:
        return json.dumps({
            "status": "no_devices",
            "message": "No Android devices connected",
            "devices": []
        })
    
    device_list = []
    for serial in devices:
        props = _device_manager._get_device_properties(serial)
        device_list.append({
            "serial": serial,
            "manufacturer": props.get('manufacturer', 'Unknown'),
            "model": props.get('model', 'Unknown'),
            "android_version": props.get('android_version', 'Unknown'),
        })
    
    return json.dumps({
        "status": "success",
        "count": len(device_list),
        "devices": device_list
    }, indent=2)


@tool
def get_device_info(device_serial: Optional[str] = None) -> str:
    """
    Get detailed information about a specific Android device.
    
    Retrieves comprehensive device properties including manufacturer, model,
    Android version, build info, and current status (battery, screen, etc.).
    
    Args:
        device_serial: Serial number of the device. If None, uses first available device.
    
    Returns:
        str: JSON string with detailed device information
    """
    # If no serial provided, use first available device
    if not device_serial:
        devices = _device_manager.adb.get_devices()
        if not devices:
            return json.dumps({
                "status": "error",
                "message": "No devices connected"
            })
        device_serial = devices[0]
    
    # Verify device exists
    devices = _device_manager.adb.get_devices()
    if device_serial not in devices:
        return json.dumps({
            "status": "error",
            "message": f"Device {device_serial} not found",
            "available_devices": devices
        })
    
    # Get device properties and status
    props = _device_manager._get_device_properties(device_serial)
    status = _device_manager._get_device_status(device_serial)
    
    return json.dumps({
        "status": "success",
        "serial": device_serial,
        "properties": props,
        "current_status": status
    }, indent=2)


@tool
def get_device_battery_info(device_serial: Optional[str] = None) -> str:
    """
    Get battery information for an Android device.
    
    Returns detailed battery status including level, charging state,
    temperature, voltage, and health.
    
    Args:
        device_serial: Serial number of the device. If None, uses first available device.
    
    Returns:
        str: JSON string with battery information
    """
    if not device_serial:
        devices = _device_manager.adb.get_devices()
        if not devices:
            return json.dumps({"status": "error", "message": "No devices connected"})
        device_serial = devices[0]
    
    battery_output = _device_manager.adb.shell("dumpsys battery", device_serial)
    
    if not battery_output:
        return json.dumps({
            "status": "error",
            "message": "Failed to get battery info"
        })
    
    battery_info = {}
    for line in battery_output.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            battery_info[key.strip()] = value.strip()
    
    return json.dumps({
        "status": "success",
        "serial": device_serial,
        "battery": battery_info
    }, indent=2)


@tool
def reboot_device(device_serial: Optional[str] = None, mode: str = "normal") -> str:
    """
    Reboot an Android device.
    
    Reboots the device to normal mode, recovery mode, or bootloader.
    WARNING: This will restart the device immediately.
    
    Args:
        device_serial: Serial number of the device. If None, uses first available device.
        mode: Reboot mode - "normal", "recovery", or "bootloader". Default is "normal".
    
    Returns:
        str: JSON string with reboot status
    """
    if not device_serial:
        devices = _device_manager.adb.get_devices()
        if not devices:
            return json.dumps({"status": "error", "message": "No devices connected"})
        device_serial = devices[0]
    
    valid_modes = ["normal", "recovery", "bootloader"]
    if mode not in valid_modes:
        return json.dumps({
            "status": "error",
            "message": f"Invalid mode '{mode}'. Valid modes: {valid_modes}"
        })
    
    # Build reboot command
    if mode == "normal":
        cmd = ["reboot"]
    elif mode == "recovery":
        cmd = ["reboot", "recovery"]
    else:  # bootloader
        cmd = ["reboot", "bootloader"]
    
    cmd.extend(["-s", device_serial])
    
    result = _device_manager.adb._run_adb(cmd)
    
    if result:
        return json.dumps({
            "status": "success",
            "message": f"Device {device_serial} rebooting to {mode} mode",
            "serial": device_serial,
            "mode": mode
        })
    else:
        return json.dumps({
            "status": "error",
            "message": "Reboot command failed"
        })


@tool
def get_device_screen_info(device_serial: Optional[str] = None) -> str:
    """
    Get screen information for an Android device.
    
    Returns screen resolution, density, and current screen state (on/off).
    
    Args:
        device_serial: Serial number of the device. If None, uses first available device.
    
    Returns:
        str: JSON string with screen information
    """
    if not device_serial:
        devices = _device_manager.adb.get_devices()
        if not devices:
            return json.dumps({"status": "error", "message": "No devices connected"})
        device_serial = devices[0]
    
    screen_info = {}
    
    # Get screen size
    size = _device_manager.adb.shell("wm size", device_serial)
    if size and 'Physical size:' in size:
        screen_info['resolution'] = size.split('Physical size:')[1].strip()
    
    # Get screen density
    density = _device_manager.adb.shell("wm density", device_serial)
    if density and 'Physical density:' in density:
        screen_info['density'] = density.split('Physical density:')[1].strip()
    
    # Get screen state
    power = _device_manager.adb.shell("dumpsys power | grep 'Display Power'", device_serial)
    screen_info['screen_on'] = 'ON' if 'state=ON' in power else 'OFF'
    
    # Get orientation
    orientation = _device_manager.adb.shell("dumpsys input | grep 'SurfaceOrientation'", device_serial)
    if orientation:
        screen_info['orientation'] = orientation.strip()
    
    return json.dumps({
        "status": "success",
        "serial": device_serial,
        "screen": screen_info
    }, indent=2)


# Export all tools for easy importing
__all__ = [
    'DeviceManager',
    'list_android_devices',
    'get_device_info',
    'get_device_battery_info',
    'reboot_device',
    'get_device_screen_info',
]
