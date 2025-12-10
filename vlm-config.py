"""
VLA Android Configuration

Centralized configuration for the VLA skill.
Modify these settings to match your environment.
"""

# =============================================================================
# vLLM SERVER CONFIGURATION
# =============================================================================

VLLM_BASE_URL = "http://10.202.1.3:8000/v1"
VLLM_API_KEY = "dummy-key"

# =============================================================================
# MODEL PATHS
# =============================================================================

# Vision-Language Model (for screenshot analysis)
VLM_MODEL = "/models/Qwen/Qwen3-VL-30B-A3B-Instruct"

# Language Model (for planning/reasoning)
LLM_MODEL = "/models/Qwen/Qwen3-Coder-30BB-A3B-Instruct"

# =============================================================================
# MODEL PARAMETERS
# =============================================================================

VLM_CONFIG = {
    "temperature": 0.1,
    "max_tokens": 4000,  # VLM needs more tokens for visual output
    "timeout": 120,      # Vision analysis can take longer
    "streaming": False,  # Must be False for your vLLM setup
}

LLM_CONFIG = {
    "temperature": 0.1,
    "max_tokens": 2000,
    "timeout": 60,
    "streaming": False,
}

# =============================================================================
# VLA AGENT SETTINGS
# =============================================================================

VLA_CONFIG = {
    "max_steps": 30,              # Maximum actions before giving up
    "step_delay": 1.5,            # Seconds to wait after each action
    "screenshot_delay": 0.5,      # Seconds to wait before taking screenshot
    "retry_on_error": 3,          # Number of retries on action failure
    "history_length": 10,         # Number of past actions to include in context
}

# =============================================================================
# IMAGE CONFIGURATION
# =============================================================================

IMAGE_CONFIG = {
    "format": "base64",           # base64 is standard for OpenAI-compatible API
    "quality": 95,                # JPEG quality if compression needed
    "max_width": 1080,            # Resize if larger (None to disable)
    "max_height": 2400,           # Resize if larger (None to disable)
}

# =============================================================================
# PATHS
# =============================================================================

import os

# Screenshot save location
SCREENSHOT_DIR = os.path.expanduser("~/Downloads/vla_screenshots")

# Ensure directory exists
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
