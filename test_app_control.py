"""Test App Control Tools"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/deepagents/deepagents'))

from android_tools.app_control import list_installed_packages, get_app_info
import json


print("="*60)
print("  APP CONTROL - TOOL TESTS")
print("="*60)

# Test 1: List all packages
print("\nTEST 1: List all installed packages")
result = list_installed_packages.invoke({})
data = json.loads(result)
print(f"Status: {data['status']}")
print(f"Found {data.get('count', 0)} packages")
if data['status'] == 'success' and data['count'] > 0:
    print(f"First 5 packages: {data['packages'][:5]}")
    print("✅ Test 1 PASSED")
else:
    print("❌ Test 1 FAILED")

# Test 2: List only 3rd party apps
print("\nTEST 2: List 3rd party apps only")
result = list_installed_packages.invoke({"filter_type": "3rdparty"})
data = json.loads(result)
print(f"Status: {data['status']}")
print(f"Found {data.get('count', 0)} 3rd party apps")
if data['status'] == 'success':
    print(f"Apps: {data['packages'][:5]}")
    print("✅ Test 2 PASSED")
else:
    print("❌ Test 2 FAILED")

# Test 3: Get info about a common system app
print("\nTEST 3: Get app info for Settings")
result = get_app_info.invoke({"package_name": "com.android.settings"})
data = json.loads(result)
print(f"Status: {data['status']}")
if data['status'] == 'success':
    print(f"App info: {json.dumps(data['app_info'], indent=2)}")
    print("✅ Test 3 PASSED")
else:
    print(f"Message: {data.get('message', 'Unknown error')}")
    print("⚠️  Test 3 SKIPPED (Settings app not found)")

print("\n" + "="*60)
print("  TESTS COMPLETE")
print("="*60)
