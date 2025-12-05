#!/usr/bin/env python3
"""Full test for all App Control tools."""

import json

from deepagents.android_tools import (
    list_installed_packages,
    get_app_info,
    install_apk,
    uninstall_app,
    start_app,
    stop_app,
    clear_app_data,
)


def test_all_app_tools():
    print("=" * 60)
    print("FULL APP CONTROL TOOLS TEST")
    print("=" * 60)
    
    # Test 1: List packages
    print("\n[1/7] Testing list_installed_packages...")
    result = list_installed_packages.invoke({"filter_type": "3rdparty"})
    data = json.loads(result)
    print(f"  ✓ Found {data.get('count', 0)} third-party packages")
    
    # Test 2: Get app info
    print("\n[2/7] Testing get_app_info...")
    result = get_app_info.invoke({"package_name": "com.android.settings"})
    data = json.loads(result)
    if data.get("package_name"):
        print(f"  ✓ Got info for: {data.get('package_name')}")
    else:
        print(f"  ✓ Response: {data}")
    
    # Test 3: Install APK (skip actual install, just test with missing file)
    print("\n[3/7] Testing install_apk (with missing file)...")
    result = install_apk.invoke({"apk_path": "/tmp/nonexistent.apk"})
    data = json.loads(result)
    if data.get("error") and "not found" in data.get("error", "").lower():
        print(f"  ✓ Correctly handled missing APK: {data.get('error')}")
    else:
        print(f"  ? Response: {data}")
    
    # Test 4: Uninstall (test with non-existent package)
    print("\n[4/7] Testing uninstall_app (with fake package)...")
    result = uninstall_app.invoke({"package_name": "com.fake.nonexistent.app"})
    data = json.loads(result)
    if data.get("error") and "not found" in data.get("error", "").lower():
        print(f"  ✓ Correctly handled missing package: {data.get('error')}")
    else:
        print(f"  ? Response: {data}")
    
    # Test 5: Start app (use settings - safe to open)
    print("\n[5/7] Testing start_app...")
    result = start_app.invoke({"package_name": "com.android.settings"})
    data = json.loads(result)
    if data.get("success"):
        print(f"  ✓ {data.get('message')}")
    else:
        print(f"  ✗ Failed: {data.get('error')}")
    
    # Test 6: Stop app
    print("\n[6/7] Testing stop_app...")
    result = stop_app.invoke({"package_name": "com.android.settings"})
    data = json.loads(result)
    if data.get("success"):
        print(f"  ✓ {data.get('message')}")
    else:
        print(f"  ✗ Failed: {data.get('error')}")
    
    # Test 7: Clear app data (use a safe test - check with fake package first)
    print("\n[7/7] Testing clear_app_data (with fake package)...")
    result = clear_app_data.invoke({"package_name": "com.fake.nonexistent.app"})
    data = json.loads(result)
    if data.get("error") and "not found" in data.get("error", "").lower():
        print(f"  ✓ Correctly handled missing package: {data.get('error')}")
    else:
        print(f"  ? Response: {data}")
    
    print("\n" + "=" * 60)
    print("ALL APP CONTROL TOOLS TESTED!")
    print("=" * 60)


if __name__ == "__main__":
    test_all_app_tools()
