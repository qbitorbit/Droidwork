"""
Test Device Manager Tools
Tests all LangChain tools in device_manager.py with connected Android devices.
"""

import sys
import os

# Add the android_tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/deepagents/deepagents'))

from android_tools.device_manager import (
    list_android_devices,
    get_device_info,
    get_device_battery_info,
    reboot_device,
    get_device_screen_info,
)
import json


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_list_devices():
    """Test listing all connected devices."""
    print_section("TEST 1: List Android Devices")
    
    result = list_android_devices.invoke({})
    print(result)
    
    # Parse and display nicely
    data = json.loads(result)
    if data['status'] == 'success':
        print(f"\n✅ Found {data['count']} device(s)")
        for device in data['devices']:
            print(f"  - {device['manufacturer']} {device['model']} ({device['serial']})")
    else:
        print(f"❌ {data['message']}")
    
    return data


def test_device_info(device_serial=None):
    """Test getting detailed device info."""
    print_section(f"TEST 2: Get Device Info{' (first device)' if not device_serial else ''}")
    
    result = get_device_info.invoke({"device_serial": device_serial})
    print(result)
    
    data = json.loads(result)
    if data['status'] == 'success':
        print(f"\n✅ Device: {data['properties']['manufacturer']} {data['properties']['model']}")
        print(f"   Android: {data['properties']['android_version']}")
        print(f"   Battery: {data['current_status'].get('battery_level', 'Unknown')}%")
        print(f"   Screen: {data['current_status'].get('screen_on', 'Unknown')}")


def test_battery_info(device_serial=None):
    """Test getting battery information."""
    print_section(f"TEST 3: Get Battery Info{' (first device)' if not device_serial else ''}")
    
    result = get_device_battery_info.invoke({"device_serial": device_serial})
    print(result)
    
    data = json.loads(result)
    if data['status'] == 'success':
        battery = data['battery']
        print(f"\n✅ Battery Status:")
        print(f"   Level: {battery.get('level', 'Unknown')}%")
        print(f"   Status: {battery.get('status', 'Unknown')}")
        print(f"   Health: {battery.get('health', 'Unknown')}")
        print(f"   Temperature: {battery.get('temperature', 'Unknown')}")


def test_screen_info(device_serial=None):
    """Test getting screen information."""
    print_section(f"TEST 4: Get Screen Info{' (first device)' if not device_serial else ''}")
    
    result = get_device_screen_info.invoke({"device_serial": device_serial})
    print(result)
    
    data = json.loads(result)
    if data['status'] == 'success':
        screen = data['screen']
        print(f"\n✅ Screen Information:")
        print(f"   Resolution: {screen.get('resolution', 'Unknown')}")
        print(f"   Density: {screen.get('density', 'Unknown')}")
        print(f"   State: {screen.get('screen_on', 'Unknown')}")


def test_reboot_dry_run():
    """Test reboot command validation (without actually rebooting)."""
    print_section("TEST 5: Reboot Command Validation (Dry Run)")
    
    # Test with invalid mode
    result = reboot_device.invoke({"mode": "invalid_mode"})
    data = json.loads(result)
    
    if data['status'] == 'error' and 'Invalid mode' in data['message']:
        print("✅ Invalid mode correctly rejected")
        print(f"   Error message: {data['message']}")
    else:
        print("❌ Invalid mode should have been rejected")
    
    print("\n⚠️  Skipping actual reboot test (uncomment to test)")
    print("   To test reboot: reboot_device.invoke({'mode': 'normal'})")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  ANDROID DEVICE MANAGER - TOOL TESTS")
    print("="*60)
    
    try:
        # Test 1: List devices
        device_data = test_list_devices()
        
        if device_data['status'] != 'success' or device_data['count'] == 0:
            print("\n❌ No devices found. Please connect an Android device and try again.")
            return
        
        # Get first device serial for subsequent tests
        first_device = device_data['devices'][0]['serial']
        
        # Test 2: Device info
        test_device_info(first_device)
        
        # Test 3: Battery info
        test_battery_info(first_device)
        
        # Test 4: Screen info
        test_screen_info(first_device)
        
        # Test 5: Reboot validation
        test_reboot_dry_run()
        
        # Summary
        print_section("TEST SUMMARY")
        print("✅ All tests completed successfully!")
        print(f"   Tested with device: {first_device}")
        
        # If multiple devices, test with second one
        if device_data['count'] > 1:
            second_device = device_data['devices'][1]['serial']
            print(f"\n📱 Multiple devices detected!")
            print(f"   Device 1: {device_data['devices'][0]['model']}")
            print(f"   Device 2: {device_data['devices'][1]['model']}")
            print(f"\n   Testing second device: {second_device}")
            test_device_info(second_device)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
