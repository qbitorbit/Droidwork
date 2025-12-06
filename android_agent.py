"""
Android Control Agent for DeepAgents

This module creates a DeepAgent with Android device control capabilities.
Uses internal vLLM server with Qwen Coder model.

Usage:
    cd ~/deepagents
    source venv/bin/activate
    env -u http_proxy python android_agent.py
"""

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

# Import all Android tools
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

# vLLM Server Configuration
LLM_BASE_URL = "http://10.202.1.3:8000/v1"
LLM_API_KEY = "dummy-key"
DEFAULT_MODEL = "/models/Qwen/Qwen3-Coder-30BB-A3B-Instruct"


def create_model():
    """Create LLM model configured for internal vLLM server."""
    return ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=DEFAULT_MODEL,
        temperature=0.1,
        max_tokens=3000,
        timeout=60,
        streaming=False,  # CRITICAL: Fixes 502 streaming errors
    )


# Collect all Android tools
ANDROID_TOOLS = [
    # Device Manager
    list_android_devices,
    get_device_info,
    get_device_battery_info,
    get_device_screen_info,
    reboot_device,
    # App Control
    list_installed_packages,
    get_app_info,
    install_apk,
    uninstall_app,
    start_app,
    stop_app,
    clear_app_data,
    # File Operations
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

# System prompt for Android control
ANDROID_SYSTEM_PROMPT = """You are an Android device control assistant with access to connected Android devices via ADB.

## Your Capabilities

### Device Management
- List connected devices and their status
- Get device information (manufacturer, model, Android version)
- Check battery status (level, charging state, health)
- Get screen information (resolution, density, state)
- Reboot devices (normal, recovery, bootloader)

### App Control
- List installed packages (all, system, third-party, enabled, disabled)
- Get app details (version, install date, permissions)
- Install APK files
- Uninstall apps
- Start/launch apps
- Force stop apps
- Clear app data and cache

### File Operations
- List files and directories on device
- Pull files from device to Mac (downloads to ~/Downloads)
- Push files from Mac to device
- Delete files/directories
- Create directories
- Check if files exist
- Read text file contents
- Write text to files
- Get file statistics
- List and extract app databases

## Important Notes

1. **Device Serial**: Most tools accept an optional `device_serial` parameter. If not provided, the first connected device is used automatically.

2. **Connected Devices**: Currently 2 Samsung devices are connected:
   - RSCR70FW19K
   - RSCRB072D9X

3. **File Paths**: 
   - Device paths start with `/` (e.g., `/sdcard/Download`)
   - Mac paths use standard paths (e.g., `~/Downloads` or `/Users/hi/...`)

4. **App Packages**: Use full package names like `com.android.chrome` or `com.whatsapp`

5. **Permissions**: Some operations may require the device to be rooted or the app to be debuggable (e.g., accessing app databases)

## Response Format

All tools return JSON strings. Parse them to check:
- `success`: Boolean indicating if operation succeeded
- `data` or relevant field: The actual result data
- `error`: Error message if operation failed
- `device`: Serial of device used

When listing devices or packages, format the results clearly for the user.
When performing file operations, confirm what was done.
Always let the user know which device you're operating on.
"""


def create_android_agent():
    """Create a DeepAgent with Android control capabilities."""
    model = create_model()
    
    agent = create_deep_agent(
        model=model,
        tools=ANDROID_TOOLS,
        system_prompt=ANDROID_SYSTEM_PROMPT,
    )
    
    return agent


def run_interactive():
    """Run interactive Android control session."""
    print("=" * 60)
    print("Android Control Agent")
    print("=" * 60)
    print(f"Model: {DEFAULT_MODEL}")
    print(f"Server: {LLM_BASE_URL}")
    print(f"Tools: {len(ANDROID_TOOLS)} Android control tools")
    print("=" * 60)
    print("\nType 'quit' or 'exit' to stop.\n")
    
    agent = create_android_agent()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            print("\nAgent: ", end="", flush=True)
            
            result = agent.invoke({
                "messages": [{"role": "user", "content": user_input}]
            })
            
            # Extract the last assistant message
            if "messages" in result:
                for msg in reversed(result["messages"]):
                    if hasattr(msg, 'content') and msg.type == "ai":
                        print(msg.content)
                        break
            else:
                print(result)
                
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    run_interactive()
