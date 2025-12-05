"""
App Control - Android Application Management Tools
Provides LangChain tools for installing, uninstalling, and managing Android apps.
"""

from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from .adb_client import ADBClient
import json
import os


class AppController:
    """Manager for Android application operations via ADB."""
    
    def __init__(self):
        self.adb = ADBClient()


# Initialize global app controller
_app_controller = AppController()


@tool
def list_installed_packages(device_serial: Optional[str] = None, filter_type: str = "all") -> str:
    """
    List installed packages on an Android device.
    
    Returns a list of installed applications filtered by type.
    
    Args:
        device_serial: Serial number of the device. If None, uses first available device.
        filter_type: Filter type - "all", "system", "3rdparty", "enabled", "disabled"
    
    Returns:
        str: JSON string with list of installed packages
    """
    if not device_serial:
        devices = _app_controller.adb.get_devices()
        if not devices:
            return json.dumps({"status": "error", "message": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    # Build pm list command based on filter
    filter_map = {
        "all": "",
        "system": "-s",
        "3rdparty": "-3",
        "enabled": "-e",
        "disabled": "-d"
    }
    
    if filter_type not in filter_map:
        return json.dumps({
            "status": "error",
            "message": f"Invalid filter_type '{filter_type}'. Valid: {list(filter_map.keys())}"
        })
    
    filter_flag = filter_map[filter_type]
    cmd = f"pm list packages {filter_flag}".strip()
    
    output = _app_controller.adb.shell(cmd, device_serial)
    
    if not output:
        return json.dumps({
            "status": "error",
            "message": "Failed to list packages"
        })
    
    # Parse package names (format: "package:com.example.app")
    packages = []
    for line in output.split('\n'):
        if line.startswith('package:'):
            package_name = line.replace('package:', '').strip()
            if package_name:
                packages.append(package_name)
    
    return json.dumps({
        "status": "success",
        "serial": device_serial,
        "filter": filter_type,
        "count": len(packages),
        "packages": packages
    }, indent=2)


@tool
def get_app_info(package_name: str, device_serial: Optional[str] = None) -> str:
    """
    Get detailed information about an installed application.
    
    Returns package details including version, install location, permissions, etc.
    
    Args:
        package_name: Package name (e.g., "com.android.chrome")
        device_serial: Serial number of the device. If None, uses first available device.
    
    Returns:
        str: JSON string with application information
    """
    if not device_serial:
        devices = _app_controller.adb.get_devices()
        if not devices:
            return json.dumps({"status": "error", "message": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    # Get package info using dumpsys
    output = _app_controller.adb.shell(f"dumpsys package {package_name}", device_serial)
    
    if not output or "Unable to find package" in output:
        return json.dumps({
            "status": "error",
            "message": f"Package '{package_name}' not found on device"
        })
    
    # Parse key information
    app_info = {"package_name": package_name}
    
    for line in output.split('\n'):
        line = line.strip()
        
        if 'versionName=' in line:
            app_info['version_name'] = line.split('versionName=')[1].split()[0]
        elif 'versionCode=' in line:
            app_info['version_code'] = line.split('versionCode=')[1].split()[0]
        elif 'firstInstallTime=' in line:
            app_info['first_install_time'] = line.split('firstInstallTime=')[1].strip()
        elif 'lastUpdateTime=' in line:
            app_info['last_update_time'] = line.split('lastUpdateTime=')[1].strip()
        elif 'installerPackageName=' in line:
            app_info['installer'] = line.split('installerPackageName=')[1].strip()
    
    return json.dumps({
        "status": "success",
        "serial": device_serial,
        "app_info": app_info
    }, indent=2)


@tool
def install_apk(apk_path: str, device_serial: Optional[str] = None) -> str:
    """Install an APK file on an Android device.
    
    Args:
        apk_path: Path to the APK file on local machine
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with installation result
    """
    # Validate APK exists
    if not os.path.exists(apk_path):
        return json.dumps({
            "success": False,
            "error": f"APK file not found: {apk_path}"
        })
    
    if not apk_path.endswith('.apk'):
        return json.dumps({
            "success": False,
            "error": "File must be an APK (.apk extension)"
        })
    
    if not device_serial:
        devices = _app_controller.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    # Install APK using adb install command
    adb = ADBClient(device_serial)
    success, stdout, stderr = adb._run_adb(["install", "-r", apk_path], timeout=120)
    
    if success and "Success" in stdout:
        return json.dumps({
            "success": True,
            "message": f"Successfully installed {os.path.basename(apk_path)}",
            "device": device_serial
        })
    else:
        error_msg = stderr or stdout or "Unknown installation error"
        return json.dumps({
            "success": False,
            "error": error_msg,
            "device": device_serial
        })


@tool
def uninstall_app(package_name: str, device_serial: Optional[str] = None) -> str:
    """Uninstall an app from an Android device.
    
    Args:
        package_name: Package name to uninstall (e.g., 'com.example.app')
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with uninstallation result
    """
    if not device_serial:
        devices = _app_controller.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    # Check if package exists first
    output = _app_controller.adb.shell(f"pm list packages {package_name}", device_serial)
    
    if not output or package_name not in output:
        return json.dumps({
            "success": False,
            "error": f"Package not found: {package_name}"
        })
    
    # Uninstall the package
    adb = ADBClient(device_serial)
    success, stdout, stderr = adb._run_adb(["uninstall", package_name], timeout=60)
    
    if success and "Success" in stdout:
        return json.dumps({
            "success": True,
            "message": f"Successfully uninstalled {package_name}",
            "device": device_serial
        })
    else:
        error_msg = stderr or stdout or "Unknown uninstallation error"
        return json.dumps({
            "success": False,
            "error": error_msg,
            "device": device_serial
        })


@tool
def start_app(package_name: str, device_serial: Optional[str] = None) -> str:
    """Launch an app on an Android device.
    
    Args:
        package_name: Package name to launch (e.g., 'com.android.settings')
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with launch result
    """
    if not device_serial:
        devices = _app_controller.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    # Use monkey tool to launch app (works without knowing activity name)
    output = _app_controller.adb.shell(
        f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1",
        device_serial
    )
    
    if output and "Events injected: 1" in output:
        return json.dumps({
            "success": True,
            "message": f"Successfully launched {package_name}",
            "device": device_serial
        })
    else:
        # Check if package exists
        check_output = _app_controller.adb.shell(f"pm list packages {package_name}", device_serial)
        
        if not check_output or package_name not in check_output:
            return json.dumps({
                "success": False,
                "error": f"Package not found: {package_name}"
            })
        
        return json.dumps({
            "success": False,
            "error": output or "Failed to launch app",
            "device": device_serial
        })


@tool
def stop_app(package_name: str, device_serial: Optional[str] = None) -> str:
    """Force stop an app on an Android device.
    
    Args:
        package_name: Package name to stop (e.g., 'com.android.settings')
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with stop result
    """
    if not device_serial:
        devices = _app_controller.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    # Check if package exists first
    output = _app_controller.adb.shell(f"pm list packages {package_name}", device_serial)
    
    if not output or package_name not in output:
        return json.dumps({
            "success": False,
            "error": f"Package not found: {package_name}"
        })
    
    # Force stop the app
    _app_controller.adb.shell(f"am force-stop {package_name}", device_serial)
    
    return json.dumps({
        "success": True,
        "message": f"Successfully stopped {package_name}",
        "device": device_serial
    })


@tool
def clear_app_data(package_name: str, device_serial: Optional[str] = None) -> str:
    """Clear app data and cache on an Android device.
    
    Args:
        package_name: Package name to clear data for (e.g., 'com.android.chrome')
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with clear result
    """
    if not device_serial:
        devices = _app_controller.adb.get_devices()
        if not devices:
            return json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    
    # Check if package exists first
    output = _app_controller.adb.shell(f"pm list packages {package_name}", device_serial)
    
    if not output or package_name not in output:
        return json.dumps({
            "success": False,
            "error": f"Package not found: {package_name}"
        })
    
    # Clear app data
    output = _app_controller.adb.shell(f"pm clear {package_name}", device_serial)
    
    if output and "Success" in output:
        return json.dumps({
            "success": True,
            "message": f"Successfully cleared data for {package_name}",
            "device": device_serial
        })
    else:
        return json.dumps({
            "success": False,
            "error": output or "Failed to clear app data",
            "device": device_serial
        })


# Export all tools
__all__ = [
    'AppController',
    'list_installed_packages',
    'get_app_info',
]
