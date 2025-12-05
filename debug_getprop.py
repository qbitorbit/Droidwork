"""Debug script to check getprop output"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/deepagents/deepagents'))

from android_tools.adb_client import ADBClient

adb = ADBClient()
devices = adb.get_devices()

if devices:
    serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    print(f"Testing device: {serial}\n")
    
    # Test various getprop commands
    props_to_test = {
        'manufacturer': 'ro.product.manufacturer',
        'model': 'ro.product.model',
        'brand': 'ro.product.brand',
    }
    
    for name, prop in props_to_test.items():
        result = adb.shell(f"getprop {prop}", serial)
        print(f"{name} ({prop}):")
        print(f"  Type: {type(result)}")
        print(f"  Raw result: {repr(result)}")
        if isinstance(result, tuple):
            print(f"  Output: {repr(result[0])}")
            print(f"  Error: {repr(result[1])}")
        print()
else:
    print("No devices connected")
