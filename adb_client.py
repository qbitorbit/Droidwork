"""ADB client wrapper for Android device control."""
import subprocess
from typing import List, Optional, Dict, Tuple


class ADBClient:
    """Wrapper for ADB commands."""
    
    def __init__(self, device_serial: Optional[str] = None):
        """
        Initialize ADB client.
        
        Args:
            device_serial: Specific device serial. If None, uses first available.
        """
        self.device_serial = device_serial
    
    def _run_adb(self, args: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Run ADB command.
        
        Args:
            args: Command arguments
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        cmd = ["adb"]
        
        # Add device serial if specified
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        
        cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            success = result.returncode == 0
            return success, result.stdout.strip(), result.stderr.strip()
            
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)
    
    def get_devices(self) -> List[Dict[str, str]]:
        """
        Get list of connected devices.
        
        Returns:
            List of device info dicts with 'serial' and 'status' keys
        """
        success, stdout, stderr = self._run_adb(["devices"])
        
        if not success:
            return []
        
        devices = []
        for line in stdout.split("\n")[1:]:  # Skip header
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    devices.append({
                        "serial": parts[0],
                        "status": parts[1]
                    })
        
        return devices
    
    def shell(self, command: str, device_serial: Optional[str] = None, timeout: int = 30) -> str:
        """
        Execute shell command on device.
        
        Args:
            command: Shell command to execute
            device_serial: Target device serial (overrides instance serial)
            timeout: Command timeout
            
        Returns:
            Command output as string (empty string on failure)
        """
        # Build command with device serial
        cmd = ["adb"]
        
        # Use provided serial, or instance serial, or let adb auto-select
        serial = device_serial or self.device_serial
        if serial:
            cmd.extend(["-s", serial])
        
        cmd.extend(["shell", command])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return result.stdout.strip() if result.returncode == 0 else ""
            
        except subprocess.TimeoutExpired:
            return ""
        except Exception as e:
            return ""
