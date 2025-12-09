---
name: vla-android
description: Vision-Language-Action automation for Android devices. Uses Qwen VL for visual perception and Qwen Coder for planning to perform human-like device control. Handles complex flows like Play Store installs, account registration, and OTP retrieval. Use when tasks require visual understanding of the screen rather than coordinate-based automation.
---

# VLA Android Automation Skill

## Overview

This skill enables human-like Android device automation using a Vision-Language-Action (VLA) pipeline:

1. **Perception (Eyes)**: Qwen3-VL analyzes screenshots to understand UI state
2. **Planning (Brain)**: Qwen3-Coder decides the next action based on visual context
3. **Execution (Hands)**: ADB tools perform taps, swipes, text input

## When to Use

Use this skill when:
- Tasks require visual understanding (e.g., "find and tap the blue button")
- UI elements don't have stable IDs or coordinates
- Complex multi-step flows with dynamic screens
- Need to handle unexpected popups or errors visually

## Available Scripts

### Core Scripts
- `scripts/perception.py` - Screenshot capture and VLM analysis
- `scripts/planner.py` - Action planning with Qwen Coder
- `scripts/executor.py` - Action execution via ADB tools
- `scripts/vla_loop.py` - Main VLA agent loop

### Utility Scripts
- `scripts/config.py` - Configuration (endpoints, models)
- `scripts/system_bypass.py` - Disable Credential Manager/Autofill

## Usage Examples

### Simple Task
```python
from scripts.vla_loop import VLAAgent

agent = VLAAgent(
    task="Open Play Store and search for WhatsApp",
    device_serial="RSCR70FW19K"
)
result = agent.run()
```

### With System Bypass (for account registration)
```python
from scripts.system_bypass import disable_security_services
from scripts.vla_loop import VLAAgent

# First disable interfering services
disable_security_services(device_serial="RSCR70FW19K")

# Then run the flow
agent = VLAAgent(
    task="Register a new Gmail account with email test@example.com",
    device_serial="RSCR70FW19K"
)
result = agent.run()
```

## Configuration

Edit `scripts/config.py` to modify:
- vLLM server endpoint
- Model paths (VLM and LLM)
- Timeouts and retry settings

## Supported Flows

1. **Play Store Install**: Search → Install → Launch app
2. **Account Registration**: Gmail/Samsung account setup with security bypass
3. **OTP Retrieval**: Extract OTP from notification panel

## Integration

This skill uses the android_tools module from the deepagents library:
- `take_screenshot()` for screen capture
- `tap()`, `swipe()`, `input_text()` for actions
- `get_ui_hierarchy()` as fallback to vision
