"""
Test script for VLA Perception Module

Run this to verify:
1. Screenshot capture works
2. Qwen VL connection works
3. UI analysis returns structured data

Usage:
    cd ~/deepagents
    source venv/bin/activate
    env -u http_proxy python ~/.deepagents/agent/skills/vla-android/scripts/test_perception.py
"""

import sys
import os
import json

# Add paths for imports
sys.path.insert(0, os.path.expanduser("~/.deepagents/agent/skills/vla-android"))
sys.path.insert(0, os.path.expanduser("~/deepagents/libs/deepagents"))

from scripts.perception import Perception, analyze_screen
from scripts.config import (
    VLLM_BASE_URL, 
    VLM_MODEL, 
    LLM_MODEL,
    SCREENSHOT_DIR
)


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def test_config():
    """Test 1: Verify configuration"""
    print_header("TEST 1: Configuration Check")
    
    print(f"  vLLM Server:  {VLLM_BASE_URL}")
    print(f"  VLM Model:    {VLM_MODEL}")
    print(f"  LLM Model:    {LLM_MODEL}")
    print(f"  Screenshot Dir: {SCREENSHOT_DIR}")
    
    # Check screenshot directory exists
    if os.path.exists(SCREENSHOT_DIR):
        print(f"  ✅ Screenshot directory exists")
    else:
        print(f"  ❌ Screenshot directory missing")
        return False
    
    return True


def test_device_connection():
    """Test 2: Check Android device connection"""
    print_header("TEST 2: Device Connection")
    
    import subprocess
    result = subprocess.run(
        ["adb", "devices"], 
        capture_output=True, 
        text=True
    )
    
    lines = result.stdout.strip().split('\n')[1:]  # Skip header
    devices = [l.split('\t')[0] for l in lines if '\t' in l and 'device' in l]
    
    if devices:
        print(f"  ✅ Found {len(devices)} device(s):")
        for d in devices:
            print(f"     - {d}")
        return devices[0]  # Return first device serial
    else:
        print("  ❌ No devices connected")
        print("     Run: adb devices")
        return None


def test_screenshot(device_serial: str):
    """Test 3: Capture screenshot"""
    print_header("TEST 3: Screenshot Capture")
    
    perception = Perception(device_serial)
    
    try:
        screenshot_path = perception.take_screenshot()
        print(f"  ✅ Screenshot saved: {screenshot_path}")
        
        # Check file size
        size = os.path.getsize(screenshot_path)
        print(f"     File size: {size / 1024:.1f} KB")
        
        return screenshot_path
    except Exception as e:
        print(f"  ❌ Screenshot failed: {e}")
        return None


def test_vlm_connection():
    """Test 4: Check VLM server connectivity"""
    print_header("TEST 4: VLM Server Connection")
    
    import requests
    
    try:
        # Test models endpoint
        response = requests.get(
            f"{VLLM_BASE_URL}/models",
            headers={"Authorization": "Bearer dummy-key"},
            timeout=10
        )
        
        if response.status_code == 200:
            models = response.json()
            print(f"  ✅ VLM server responding")
            print(f"     Available models:")
            for m in models.get("data", [])[:5]:  # Show first 5
                print(f"     - {m.get('id', 'unknown')}")
            return True
        else:
            print(f"  ❌ Server returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Cannot connect to {VLLM_BASE_URL}")
        print("     Check if vLLM server is running")
        return False
    except Exception as e:
        print(f"  ❌ Connection error: {e}")
        return False


def test_vlm_analysis(screenshot_path: str):
    """Test 5: Run VLM analysis on screenshot"""
    print_header("TEST 5: VLM Screenshot Analysis")
    
    perception = Perception()
    
    print("  Sending screenshot to Qwen VL...")
    print("  (This may take 30-60 seconds)")
    
    try:
        ui_state = perception.analyze_screenshot(screenshot_path)
        
        print(f"\n  ✅ Analysis complete!")
        print(f"\n  App/Screen: {ui_state.app_name}")
        print(f"  Description: {ui_state.screen_description[:100]}...")
        print(f"  Elements found: {len(ui_state.elements)}")
        print(f"  Popup visible: {ui_state.popup_visible}")
        print(f"  Error message: {ui_state.error_message}")
        
        if ui_state.elements:
            print(f"\n  First 5 UI Elements:")
            for i, elem in enumerate(ui_state.elements[:5]):
                print(f"     {i+1}. [{elem.element_type}] \"{elem.text}\" at ({elem.x}, {elem.y})")
        
        if ui_state.available_actions:
            print(f"\n  Available Actions:")
            for action in ui_state.available_actions[:5]:
                print(f"     - {action}")
        
        return ui_state
        
    except Exception as e:
        print(f"  ❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_full_pipeline(device_serial: str):
    """Test 6: Full capture and analyze pipeline"""
    print_header("TEST 6: Full Pipeline (capture_and_analyze)")
    
    print("  Running full pipeline...")
    
    try:
        ui_state = analyze_screen(device_serial)
        
        print(f"  ✅ Full pipeline successful!")
        print(f"\n  Result JSON:")
        print(ui_state.to_json())
        
        return True
        
    except Exception as e:
        print(f"  ❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "🔬 " * 20)
    print("   VLA PERCEPTION MODULE TEST SUITE")
    print("🔬 " * 20)
    
    results = {}
    
    # Test 1: Config
    results["config"] = test_config()
    
    # Test 2: Device
    device_serial = test_device_connection()
    results["device"] = device_serial is not None
    
    if not device_serial:
        print("\n⚠️  Cannot continue without a connected device")
        print("   Connect a device and run again")
        return
    
    # Test 3: Screenshot
    screenshot_path = test_screenshot(device_serial)
    results["screenshot"] = screenshot_path is not None
    
    if not screenshot_path:
        print("\n⚠️  Cannot continue without screenshot")
        return
    
    # Test 4: VLM Connection
    results["vlm_connection"] = test_vlm_connection()
    
    if not results["vlm_connection"]:
        print("\n⚠️  Cannot continue without VLM server")
        print("   Check your vLLM server at", VLLM_BASE_URL)
        return
    
    # Test 5: VLM Analysis
    ui_state = test_vlm_analysis(screenshot_path)
    results["vlm_analysis"] = ui_state is not None
    
    # Test 6: Full Pipeline
    if results["vlm_analysis"]:
        results["full_pipeline"] = test_full_pipeline(device_serial)
    
    # Summary
    print_header("TEST SUMMARY")
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("  🎉 ALL TESTS PASSED! VLA Perception is ready.")
    else:
        print("  ⚠️  Some tests failed. Check errors above.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
