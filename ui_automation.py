"""UI Automation tools for Android devices."""
import json
from typing import Optional
from langchain_core.tools import tool
from .adb_client import ADBClient


class UIAutomation:
    """Manager for UI automation."""
    
    def __init__(self):
        self.adb = ADBClient()


_ui = UIAutomation()


@tool
def tap(x: int, y: int, device_serial: Optional[str] = None) -> str:
    """Tap on screen coordinates.
    
    Args:
        x: X coordinate
        y: Y coordinate
        device_serial: Device serial (optional, uses first device if not specified)
    
    Returns:
        JSON string with success status
    """
    if not device_serial:
        devices = _ui.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    try:
        adb = ADBClient(device_serial)
        success, stdout, stderr = adb._run_adb(["shell", "input", "tap", str(x), str(y)])
        
        if not success:
            return json.dumps({"success": False, "error": f"Tap failed: {stderr}"})
        
        return json.dumps({
            "success": True,
            "action": "tap",
            "x": x,
            "y": y,
            "device": device_serial
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def long_press(x: int, y: int, duration_ms: int = 1000, device_serial: Optional[str] = None) -> str:
    """Long press on screen coordinates.
    
    Args:
        x: X coordinate
        y: Y coordinate
        duration_ms: Duration in milliseconds (default: 1000)
        device_serial: Device serial (optional, uses first device if not specified)
    
    Returns:
        JSON string with success status
    """
    if not device_serial:
        devices = _ui.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    try:
        adb = ADBClient(device_serial)
        # Long press is a swipe from point to same point with duration
        success, stdout, stderr = adb._run_adb([
            "shell", "input", "swipe", 
            str(x), str(y), str(x), str(y), str(duration_ms)
        ])
        
        if not success:
            return json.dumps({"success": False, "error": f"Long press failed: {stderr}"})
        
        return json.dumps({
            "success": True,
            "action": "long_press",
            "x": x,
            "y": y,
            "duration_ms": duration_ms,
            "device": device_serial
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def swipe(
    start_x: int, 
    start_y: int, 
    end_x: int, 
    end_y: int, 
    duration_ms: int = 300,
    device_serial: Optional[str] = None
) -> str:
    """Swipe from one point to another.
    
    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        duration_ms: Swipe duration in milliseconds (default: 300, higher = slower)
        device_serial: Device serial (optional, uses first device if not specified)
    
    Returns:
        JSON string with success status
    """
    if not device_serial:
        devices = _ui.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    try:
        adb = ADBClient(device_serial)
        success, stdout, stderr = adb._run_adb([
            "shell", "input", "swipe",
            str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)
        ])
        
        if not success:
            return json.dumps({"success": False, "error": f"Swipe failed: {stderr}"})
        
        return json.dumps({
            "success": True,
            "action": "swipe",
            "start": {"x": start_x, "y": start_y},
            "end": {"x": end_x, "y": end_y},
            "duration_ms": duration_ms,
            "device": device_serial
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int = 1000,
    device_serial: Optional[str] = None
) -> str:
    """Drag from one point to another (like swipe but slower, for drag-and-drop).
    
    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        duration_ms: Drag duration in milliseconds (default: 1000)
        device_serial: Device serial (optional, uses first device if not specified)
    
    Returns:
        JSON string with success status
    """
    if not device_serial:
        devices = _ui.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    try:
        adb = ADBClient(device_serial)
        # Drag is essentially a slow swipe
        success, stdout, stderr = adb._run_adb([
            "shell", "input", "draganddrop",
            str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)
        ])
        
        # Fallback to swipe if draganddrop not supported (older Android)
        if not success:
            success, stdout, stderr = adb._run_adb([
                "shell", "input", "swipe",
                str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)
            ])
        
        if not success:
            return json.dumps({"success": False, "error": f"Drag failed: {stderr}"})
        
        return json.dumps({
            "success": True,
            "action": "drag",
            "start": {"x": start_x, "y": start_y},
            "end": {"x": end_x, "y": end_y},
            "duration_ms": duration_ms,
            "device": device_serial
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def input_text(text: str, device_serial: Optional[str] = None) -> str:
    """Type text on the device (focus must be on a text field).
    
    Args:
        text: Text to type. Spaces are supported. Special characters may need escaping.
        device_serial: Device serial (optional, uses first device if not specified)
    
    Returns:
        JSON string with success status
    """
    if not device_serial:
        devices = _ui.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    try:
        adb = ADBClient(device_serial)
        
        # Escape special characters for shell
        # Replace spaces with %s (ADB input text format)
        escaped_text = text.replace(" ", "%s")
        # Escape other special characters
        for char in ["'", '"', "\\", "&", "|", ";", "$", "`", "(", ")", "<", ">"]:
            escaped_text = escaped_text.replace(char, f"\\{char}")
        
        success, stdout, stderr = adb._run_adb(["shell", "input", "text", escaped_text])
        
        if not success:
            return json.dumps({"success": False, "error": f"Input text failed: {stderr}"})
        
        return json.dumps({
            "success": True,
            "action": "input_text",
            "text": text,
            "device": device_serial
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def press_key(keycode: str, longpress: bool = False, device_serial: Optional[str] = None) -> str:
    """Press a key/button on the device.
    
    Args:
        keycode: Key to press. Common values:
            - KEYCODE_HOME (3) - Home button
            - KEYCODE_BACK (4) - Back button
            - KEYCODE_MENU (82) - Menu button
            - KEYCODE_ENTER (66) - Enter key
            - KEYCODE_DEL (67) - Backspace/Delete
            - KEYCODE_POWER (26) - Power button
            - KEYCODE_VOLUME_UP (24) - Volume up
            - KEYCODE_VOLUME_DOWN (25) - Volume down
            - KEYCODE_TAB (61) - Tab key
            - KEYCODE_SPACE (62) - Space
            - KEYCODE_CAMERA (27) - Camera button
            - KEYCODE_SEARCH (84) - Search
            Can use name (e.g., "KEYCODE_HOME") or number (e.g., "3")
        longpress: If True, perform a long press of the key
        device_serial: Device serial (optional, uses first device if not specified)
    
    Returns:
        JSON string with success status
    """
    if not device_serial:
        devices = _ui.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    try:
        adb = ADBClient(device_serial)
        
        cmd = ["shell", "input", "keyevent"]
        if longpress:
            cmd.append("--longpress")
        cmd.append(str(keycode))
        
        success, stdout, stderr = adb._run_adb(cmd)
        
        if not success:
            return json.dumps({"success": False, "error": f"Key press failed: {stderr}"})
        
        return json.dumps({
            "success": True,
            "action": "press_key",
            "keycode": keycode,
            "longpress": longpress,
            "device": device_serial
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def get_ui_hierarchy(device_serial: Optional[str] = None) -> str:
    """Dump the UI hierarchy (XML) of the current screen.
    
    Useful for finding UI elements, their bounds, and text content.
    Can be used with vision models to understand screen layout.
    
    Args:
        device_serial: Device serial (optional, uses first device if not specified)
    
    Returns:
        JSON string with success status and UI hierarchy XML
    """
    if not device_serial:
        devices = _ui.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    try:
        adb = ADBClient(device_serial)
        
        # Dump UI hierarchy to device temp file
        device_temp = "/sdcard/ui_dump.xml"
        success, stdout, stderr = adb._run_adb([
            "shell", "uiautomator", "dump", device_temp
        ])
        
        if not success:
            return json.dumps({"success": False, "error": f"UI dump failed: {stderr}"})
        
        # Read the dump file
        success, stdout, stderr = adb._run_adb(["shell", "cat", device_temp])
        
        if not success:
            return json.dumps({"success": False, "error": f"Failed to read UI dump: {stderr}"})
        
        # Clean up
        adb._run_adb(["shell", "rm", device_temp])
        
        return json.dumps({
            "success": True,
            "hierarchy": stdout,
            "device": device_serial
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
