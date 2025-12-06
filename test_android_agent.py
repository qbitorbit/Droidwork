"""
Test script to verify Android tools integration with DeepAgents.

Run this first to make sure all imports work:
    cd ~/deepagents
    source venv/bin/activate
    env -u http_proxy python test_android_agent.py
"""

import json

print("=" * 60)
print("Testing Android Tools Integration")
print("=" * 60)

# Test 1: Import all tools
print("\n[1/4] Testing imports...")
try:
    from deepagents.android_tools import (
        # Device Manager (5 tools)
        list_android_devices,
        get_device_info,
        get_device_battery_info,
        get_device_screen_info,
        reboot_device,
        # App Control (7 tools)
        list_installed_packages,
        get_app_info,
        install_apk,
        uninstall_app,
        start_app,
        stop_app,
        clear_app_data,
        # File Operations (11 tools)
        list_files,
        pull_file,
        push_file,
        delete_file,
        create_directory,
        file_exists,
        read_file,
        write_file,
        file_stats,
        list_app_databases,
        pull_app_database,
    )
    print("  ✅ All 23 tools imported successfully")
except ImportError as e:
    print(f"  ❌ Import error: {e}")
    exit(1)

# Test 2: Verify tools are callable
print("\n[2/4] Verifying tools are LangChain tools...")
tools = [
    list_android_devices,
    get_device_info,
    get_device_battery_info,
    get_device_screen_info,
    reboot_device,
    list_installed_packages,
    get_app_info,
    install_apk,
    uninstall_app,
    start_app,
    stop_app,
    clear_app_data,
    list_files,
    pull_file,
    push_file,
    delete_file,
    create_directory,
    file_exists,
    read_file,
    write_file,
    file_stats,
    list_app_databases,
    pull_app_database,
]

for tool in tools:
    if not hasattr(tool, 'name'):
        print(f"  ❌ {tool} is not a valid LangChain tool")
        exit(1)

print(f"  ✅ All {len(tools)} tools verified")

# Test 3: Test list_android_devices (actual device check)
print("\n[3/4] Testing device connection...")
try:
    result = list_android_devices.invoke({})
    data = json.loads(result)
    
    if data.get('success'):
        devices = data.get('devices', [])
        print(f"  ✅ Found {len(devices)} device(s):")
        for d in devices:
            serial = d.get('serial', 'unknown')
            model = d.get('model', 'unknown')
            print(f"     - {serial} ({model})")
    else:
        print(f"  ⚠️  No devices or error: {data.get('error')}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 4: Test LLM connection
print("\n[4/4] Testing LLM connection...")
try:
    from langchain_openai import ChatOpenAI
    
    LLM_BASE_URL = "http://10.202.1.3:8000/v1"
    LLM_API_KEY = "dummy-key"
    DEFAULT_MODEL = "/models/Qwen/Qwen3-Coder-30BB-A3B-Instruct"
    
    model = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=DEFAULT_MODEL,
        temperature=0.1,
        max_tokens=100,
        timeout=30,
        streaming=False,
    )
    
    response = model.invoke("Say 'Hello' in one word.")
    print(f"  ✅ LLM responded: {response.content[:50]}...")
except Exception as e:
    print(f"  ❌ LLM error: {e}")
    print("     Make sure you're on the internal network")

# Test 5: Test DeepAgents import
print("\n[5/5] Testing DeepAgents import...")
try:
    from deepagents import create_deep_agent
    print("  ✅ create_deep_agent imported successfully")
except ImportError as e:
    print(f"  ❌ Import error: {e}")
    print("     Run: pip install deepagents")

print("\n" + "=" * 60)
print("Integration test complete!")
print("=" * 60)
print("\nIf all tests passed, run:")
print("  env -u http_proxy python android_agent.py")
