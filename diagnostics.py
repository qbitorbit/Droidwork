"""Diagnostics tools for Android devices."""
import json
import os
from typing import Optional
from langchain_core.tools import tool
from .adb_client import ADBClient


class DiagnosticsManager:
    """Manager for device diagnostics."""
    
    def __init__(self):
        self.adb = ADBClient()


_manager = DiagnosticsManager()


@tool
def take_screenshot(output_path: Optional[str] = None, device_serial: Optional[str] = None) -> str:
    """Capture a screenshot from the Android device.
    
    Args:
        output_path: Where to save on Mac (default: ~/Downloads/screenshot_<timestamp>.png)
        device_serial: Device serial (optional, uses first device if not specified)
    
    Returns:
        JSON string with success status and file path
    """
    import time
    
    # Get device serial
    if not device_serial:
        devices = _manager.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    # Set default output path
    if not output_path:
        timestamp = int(time.time())
        output_path = os.path.expanduser(f"~/Downloads/screenshot_{timestamp}.png")
    else:
        output_path = os.path.expanduser(output_path)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        adb = ADBClient(device_serial)
        
        # Capture screenshot to device temp location
        device_temp = "/sdcard/screenshot_temp.png"
        success, stdout, stderr = adb._run_adb(["shell", "screencap", "-p", device_temp])
        
        if not success:
            return json.dumps({"success": False, "error": f"Failed to capture: {stderr}"})
        
        # Pull to Mac
        success, stdout, stderr = adb._run_adb(["pull", device_temp, output_path])
        
        if not success:
            return json.dumps({"success": False, "error": f"Failed to pull: {stderr}"})
        
        # Clean up temp file on device
        adb._run_adb(["shell", "rm", device_temp])
        
        return json.dumps({
            "success": True,
            "path": output_path,
            "device": device_serial
        })
        
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
