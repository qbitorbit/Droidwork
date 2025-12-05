#!/usr/bin/env python3
"""Test for File Operations tools."""

import json

from deepagents.android_tools import (
    list_files,
    file_exists,
    file_stats,
    list_app_databases,
)


def test_file_ops():
    print("=" * 60)
    print("FILE OPERATIONS TOOLS TEST")
    print("=" * 60)
    
    # Test 1: List files in /sdcard
    print("\n[1/5] Testing list_files on /sdcard...")
    result = list_files.invoke({"path": "/sdcard"})
    data = json.loads(result)
    if data.get("success"):
        print(f"  ✓ Found {data.get('total_files', 0)} files, {data.get('total_directories', 0)} directories")
    else:
        print(f"  ✗ Failed: {data.get('error')}")
    
    # Test 2: List files in /sdcard/Download
    print("\n[2/5] Testing list_files on /sdcard/Download...")
    result = list_files.invoke({"path": "/sdcard/Download"})
    data = json.loads(result)
    if data.get("success"):
        print(f"  ✓ Found {data.get('total_files', 0)} files in Download folder")
        # Show first 3 files
        for f in data.get("files", [])[:3]:
            print(f"    - {f.get('name')} ({f.get('size_formatted')})")
    else:
        print(f"  ✗ Failed: {data.get('error')}")
    
    # Test 3: Check if /sdcard exists
    print("\n[3/5] Testing file_exists on /sdcard...")
    result = file_exists.invoke({"path": "/sdcard"})
    data = json.loads(result)
    if data.get("success"):
        print(f"  ✓ /sdcard exists: {data.get('exists')}, type: {data.get('type')}")
    else:
        print(f"  ✗ Failed: {data.get('error')}")
    
    # Test 4: Get stats for /sdcard
    print("\n[4/5] Testing file_stats on /sdcard...")
    result = file_stats.invoke({"path": "/sdcard"})
    data = json.loads(result)
    if data.get("success"):
        print(f"  ✓ Type: {data.get('type')}, Permissions: {data.get('permissions')}")
        if data.get('file_count'):
            print(f"    Files: {data.get('file_count')}, Dirs: {data.get('directory_count')}")
    else:
        print(f"  ✗ Failed: {data.get('error')}")
    
    # Test 5: List app databases (try with a common app)
    print("\n[5/5] Testing list_app_databases...")
    # Try Chrome or Settings
    test_packages = [
        "com.android.chrome",
        "com.android.providers.contacts",
        "com.samsung.android.messaging"
    ]
    
    found_db = False
    for pkg in test_packages:
        result = list_app_databases.invoke({"package_name": pkg})
        data = json.loads(result)
        if data.get("success") and data.get("count", 0) > 0:
            print(f"  ✓ Found {data.get('count')} databases for {pkg}")
            print(f"    Access method: {data.get('access_method')}")
            for db in data.get("databases", [])[:3]:
                print(f"    - {db.get('name')} ({db.get('size_formatted')})")
            found_db = True
            break
    
    if not found_db:
        print(f"  ⚠ Could not access app databases (device may not be rooted/debuggable)")
    
    print("\n" + "=" * 60)
    print("FILE OPERATIONS TEST COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    test_file_ops()
