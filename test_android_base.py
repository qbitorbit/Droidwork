"""Test basic Android ADB connectivity."""

import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent / "libs" / "deepagents"))

from android_tools.adb_client import ADBClient


def test_adb_connection():
    """Test ADB client."""
    print("Testing ADB Connection...")
    print("=" * 60)
    
    # Test 1: List devices
    print("\n1. Testing device listing...")
    client = ADBClient()
    devices = client.get_devices()
    
    print(f"   Found {len(devices)} device(s):")
    for device in devices:
        print(f"   - {device['serial']}: {device['status']}")
    
    if not devices:
        print("   ❌ No devices found!")
        return False
    
    # Test 2: Test shell command on each device
    print("\n2. Testing shell commands...")
    for device in devices:
        print(f"\n   Device: {device['serial']}")
        client = ADBClient(device_serial=device['serial'])
        
        # Get Android version
        success, stdout, stderr = client.shell("getprop ro.build.version.release")
        if success:
            print(f"   ✓ Android version: {stdout}")
        else:
            print(f"   ❌ Failed: {stderr}")
            return False
    
    print("\n" + "=" * 60)
    print("✅ ADB Client Test PASSED!")
    return True


if __name__ == "__main__":
    try:
        success = test_adb_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
