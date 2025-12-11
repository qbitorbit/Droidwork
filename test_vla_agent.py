"""
Test script for VLA Agent - Full Pipeline

Tests the complete Vision-Language-Action loop with real tasks.

Usage:
    cd ~/deepagents
    source venv/bin/activate
    env -u http_proxy python ~/.deepagents/agent/skills/vla-android/scripts/test_vla_agent.py
"""

import sys
import os
import time
import argparse

# Add paths for imports
sys.path.insert(0, os.path.expanduser("~/.deepagents/agent/skills/vla-android"))
sys.path.insert(0, os.path.expanduser("~/deepagents/libs/deepagents"))

from scripts.vla_loop import (
    VLAAgent,
    run_task,
    open_app_and_search,
    install_app_from_play_store,
    AgentStatus,
)
from scripts.config import VLLM_BASE_URL, VLM_MODEL, LLM_MODEL


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_result(result):
    """Print agent result summary"""
    print("\n" + "-" * 60)
    print("RESULT SUMMARY")
    print("-" * 60)
    print(f"  Success:    {result.success}")
    print(f"  Status:     {result.status.value}")
    print(f"  Steps:      {result.total_steps}")
    print(f"  Duration:   {result.total_duration_ms / 1000:.1f} seconds")
    
    if result.error:
        print(f"  Error:      {result.error}")
    
    if result.history:
        print(f"\n  Step History:")
        for step in result.history:
            action_type = step.action.get("type", "unknown")
            success = "✓" if step.result.get("success") else "✗"
            print(f"    {step.step_number}. [{success}] {action_type}")
    
    print("-" * 60)


def check_prerequisites():
    """Check that everything is ready"""
    print_header("PREREQUISITE CHECK")
    
    import subprocess
    import requests
    
    all_ok = True
    
    # Check device
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')[1:]
    devices = [l.split('\t')[0] for l in lines if '\t' in l and 'device' in l]
    
    if devices:
        print(f"  ✅ Device connected: {devices[0]}")
        device_serial = devices[0]
    else:
        print("  ❌ No device connected")
        all_ok = False
        device_serial = None
    
    # Check VLM server
    try:
        response = requests.get(
            f"{VLLM_BASE_URL}/models",
            headers={"Authorization": "Bearer dummy-key"},
            timeout=10
        )
        if response.status_code == 200:
            print(f"  ✅ VLM server responding")
        else:
            print(f"  ❌ VLM server error: {response.status_code}")
            all_ok = False
    except Exception as e:
        print(f"  ❌ VLM server not reachable: {e}")
        all_ok = False
    
    # Check models
    print(f"  ℹ️  VLM Model: {VLM_MODEL}")
    print(f"  ℹ️  LLM Model: {LLM_MODEL}")
    
    return all_ok, device_serial


def test_simple_task(device_serial: str):
    """Test 1: Simple navigation task"""
    print_header("TEST 1: Simple Task - Open Settings")
    
    print("Task: Open the Settings app")
    print("This tests basic perception → planning → execution loop")
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    result = run_task(
        task="Press the Home button, then open the Settings app from the home screen or app drawer",
        device_serial=device_serial,
        max_steps=15,
        verbose=True
    )
    
    print_result(result)
    return result.success


def test_play_store_search(device_serial: str):
    """Test 2: Play Store search"""
    print_header("TEST 2: Play Store Search")
    
    print("Task: Open Play Store and search for WhatsApp")
    print("This tests multi-step navigation and text input")
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    result = open_app_and_search(
        app_name="Play Store",
        search_term="WhatsApp",
        device_serial=device_serial
    )
    
    print_result(result)
    return result.success


def test_play_store_install(device_serial: str, app_name: str = "Calculator"):
    """Test 3: Full Play Store install flow"""
    print_header("TEST 3: Play Store Install Flow")
    
    print(f"Task: Install '{app_name}' from Play Store")
    print("This tests the complete install flow")
    print("\n⚠️  Note: This will actually install an app!")
    print("\nStarting in 5 seconds...")
    time.sleep(5)
    
    result = install_app_from_play_store(
        app_name=app_name,
        device_serial=device_serial
    )
    
    print_result(result)
    return result.success


def test_custom_task(device_serial: str, task: str, max_steps: int = 30):
    """Test with custom task"""
    print_header("CUSTOM TASK")
    
    print(f"Task: {task}")
    print(f"Max steps: {max_steps}")
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    result = run_task(
        task=task,
        device_serial=device_serial,
        max_steps=max_steps,
        verbose=True
    )
    
    print_result(result)
    return result.success


def interactive_mode(device_serial: str):
    """Interactive mode - run custom tasks"""
    print_header("INTERACTIVE MODE")
    print("Enter tasks to execute. Type 'quit' to exit.\n")
    
    while True:
        try:
            task = input("\n📱 Enter task (or 'quit'): ").strip()
            
            if task.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not task:
                continue
            
            result = run_task(
                task=task,
                device_serial=device_serial,
                max_steps=30,
                verbose=True
            )
            
            print_result(result)
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="VLA Agent Test Suite")
    parser.add_argument(
        "--test", 
        choices=["simple", "search", "install", "custom", "interactive", "all"],
        default="simple",
        help="Which test to run"
    )
    parser.add_argument(
        "--task",
        help="Custom task (for --test custom)"
    )
    parser.add_argument(
        "--app",
        default="Calculator",
        help="App to install (for --test install)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=30,
        help="Max steps for custom task"
    )
    parser.add_argument(
        "--device",
        help="Device serial (auto-detect if not specified)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "🤖 " * 20)
    print("   VLA AGENT TEST SUITE")
    print("🤖 " * 20)
    
    # Check prerequisites
    all_ok, detected_device = check_prerequisites()
    
    device_serial = args.device or detected_device
    
    if not all_ok:
        print("\n❌ Prerequisites not met. Please fix issues above.")
        sys.exit(1)
    
    if not device_serial:
        print("\n❌ No device available.")
        sys.exit(1)
    
    print(f"\n✅ Using device: {device_serial}")
    
    # Run selected test
    if args.test == "simple":
        success = test_simple_task(device_serial)
    
    elif args.test == "search":
        success = test_play_store_search(device_serial)
    
    elif args.test == "install":
        success = test_play_store_install(device_serial, args.app)
    
    elif args.test == "custom":
        if not args.task:
            print("❌ --task required for custom test")
            sys.exit(1)
        success = test_custom_task(device_serial, args.task, args.steps)
    
    elif args.test == "interactive":
        interactive_mode(device_serial)
        success = True
    
    elif args.test == "all":
        print("\n🏃 Running all tests...\n")
        
        results = {}
        
        # Test 1
        results["simple"] = test_simple_task(device_serial)
        time.sleep(2)
        
        # Test 2
        results["search"] = test_play_store_search(device_serial)
        time.sleep(2)
        
        # Summary
        print_header("ALL TESTS SUMMARY")
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        success = all(results.values())
    
    # Final status
    print("\n" + "=" * 60)
    if success:
        print("  🎉 TEST PASSED!")
    else:
        print("  ❌ TEST FAILED")
    print("=" * 60 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
