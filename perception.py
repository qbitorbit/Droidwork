"""
VLA Perception Module

Handles screenshot capture and visual analysis using Qwen VL.
This is the "Eyes" of the VLA pipeline.
"""

import base64
import json
import os
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

import requests
from PIL import Image
import io

from .config import (
    VLLM_BASE_URL,
    VLLM_API_KEY,
    VLM_MODEL,
    VLM_CONFIG,
    IMAGE_CONFIG,
    SCREENSHOT_DIR,
)


@dataclass
class UIElement:
    """Represents a detected UI element"""
    element_type: str          # button, input, text, checkbox, image, etc.
    text: str                  # Visible text/label
    x: int                     # Center X coordinate
    y: int                     # Center Y coordinate
    width: Optional[int] = None
    height: Optional[int] = None
    clickable: bool = True
    description: Optional[str] = None


@dataclass
class UIState:
    """Represents the analyzed state of the screen"""
    app_name: str                           # Current app/screen
    screen_description: str                 # What's on screen
    elements: List[UIElement] = field(default_factory=list)
    error_message: Optional[str] = None     # Any visible error
    popup_visible: bool = False             # Is there a popup/dialog
    available_actions: List[str] = field(default_factory=list)
    raw_response: Optional[str] = None      # Raw VLM response
    
    def to_json(self) -> str:
        """Convert to JSON for LLM context"""
        return json.dumps({
            "app_name": self.app_name,
            "screen_description": self.screen_description,
            "elements": [
                {
                    "type": e.element_type,
                    "text": e.text,
                    "x": e.x,
                    "y": e.y,
                    "clickable": e.clickable,
                }
                for e in self.elements
            ],
            "error_message": self.error_message,
            "popup_visible": self.popup_visible,
            "available_actions": self.available_actions,
        }, indent=2)
    
    @property
    def summary(self) -> str:
        """Short summary for action history"""
        return f"{self.app_name}: {self.screen_description[:100]}"


class Perception:
    """
    Handles visual perception using Qwen VL.
    
    Usage:
        perception = Perception()
        ui_state = perception.analyze_screenshot(screenshot_path)
    """
    
    def __init__(self, device_serial: Optional[str] = None):
        self.device_serial = device_serial
        self.api_url = f"{VLLM_BASE_URL}/chat/completions"
        
    def take_screenshot(self, device_serial: Optional[str] = None) -> str:
        """
        Capture screenshot from Android device.
        Returns path to saved screenshot.
        """
        serial = device_serial or self.device_serial
        timestamp = int(time.time() * 1000)
        output_path = os.path.join(SCREENSHOT_DIR, f"screen_{timestamp}.png")
        
        # Use the existing android_tools screenshot function
        try:
            # Import here to avoid circular imports
            import sys
            sys.path.insert(0, os.path.expanduser("~/deepagents/libs/deepagents"))
            from deepagents.android_tools import take_screenshot as adb_screenshot
            
            result = adb_screenshot.invoke({
                "output_path": output_path,
                "device_serial": serial
            })
            result_data = json.loads(result)
            
            if result_data.get("success"):
                return result_data.get("path", output_path)
            else:
                raise Exception(result_data.get("error", "Screenshot failed"))
                
        except ImportError:
            # Fallback to direct ADB if android_tools not available
            return self._take_screenshot_adb(serial, output_path)
    
    def _take_screenshot_adb(self, device_serial: str, output_path: str) -> str:
        """Fallback: Direct ADB screenshot"""
        import subprocess
        
        device_temp = "/sdcard/vla_screenshot.png"
        
        # Capture on device
        cmd = ["adb"]
        if device_serial:
            cmd.extend(["-s", device_serial])
        cmd.extend(["shell", "screencap", "-p", device_temp])
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Pull to local
        cmd = ["adb"]
        if device_serial:
            cmd.extend(["-s", device_serial])
        cmd.extend(["pull", device_temp, output_path])
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Cleanup device
        cmd = ["adb"]
        if device_serial:
            cmd.extend(["-s", device_serial])
        cmd.extend(["shell", "rm", device_temp])
        subprocess.run(cmd, capture_output=True)
        
        return output_path
    
    def _encode_image_base64(self, image_path: str) -> str:
        """Encode image to base64 string"""
        # Open and optionally resize
        with Image.open(image_path) as img:
            # Resize if needed
            max_w = IMAGE_CONFIG.get("max_width")
            max_h = IMAGE_CONFIG.get("max_height")
            
            if max_w and max_h:
                if img.width > max_w or img.height > max_h:
                    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            return base64.b64encode(buffer.read()).decode("utf-8")
    
    def _build_analysis_prompt(self) -> str:
        """Build the prompt for UI analysis"""
        return """Analyze this Android screenshot and provide a structured analysis.

## Instructions
1. Identify the current app/screen name
2. Describe what is displayed on the screen
3. List ALL interactive UI elements you can see with their:
   - Type (button, input_field, checkbox, text, icon, link, etc.)
   - Visible text or label
   - Approximate center coordinates (x, y) based on screen position
   - Whether it appears clickable
4. Note any error messages or popups
5. List possible actions a user could take

## Response Format (JSON)
```json
{
    "app_name": "Name of the app or screen",
    "screen_description": "Brief description of what's shown",
    "elements": [
        {
            "type": "button",
            "text": "Install",
            "x": 540,
            "y": 1800,
            "clickable": true
        }
    ],
    "error_message": null,
    "popup_visible": false,
    "available_actions": ["tap Install button", "scroll down", "go back"]
}
```

Respond ONLY with valid JSON, no additional text."""

    def analyze_screenshot(
        self, 
        screenshot_path: str,
        custom_prompt: Optional[str] = None
    ) -> UIState:
        """
        Analyze a screenshot using Qwen VL.
        
        Args:
            screenshot_path: Path to the screenshot image
            custom_prompt: Optional custom analysis prompt
            
        Returns:
            UIState object with parsed analysis
        """
        # Encode image
        image_base64 = self._encode_image_base64(screenshot_path)
        
        # Build prompt
        prompt = custom_prompt or self._build_analysis_prompt()
        
        # Prepare request payload
        payload = {
            "model": VLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "temperature": VLM_CONFIG["temperature"],
            "max_tokens": VLM_CONFIG["max_tokens"],
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VLLM_API_KEY}"
        }
        
        # Make request
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=VLM_CONFIG["timeout"]
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            return self._parse_vlm_response(content)
            
        except requests.exceptions.Timeout:
            return UIState(
                app_name="Unknown",
                screen_description="VLM analysis timed out",
                error_message="Analysis timeout - screen may be complex",
                raw_response=None
            )
        except Exception as e:
            return UIState(
                app_name="Unknown",
                screen_description=f"VLM analysis failed: {str(e)}",
                error_message=str(e),
                raw_response=None
            )
    
    def _parse_vlm_response(self, response: str) -> UIState:
        """Parse VLM response into UIState"""
        try:
            # Try to extract JSON from response
            # Handle cases where VLM adds markdown code blocks
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            # Parse elements
            elements = []
            for elem in data.get("elements", []):
                elements.append(UIElement(
                    element_type=elem.get("type", "unknown"),
                    text=elem.get("text", ""),
                    x=elem.get("x", 0),
                    y=elem.get("y", 0),
                    width=elem.get("width"),
                    height=elem.get("height"),
                    clickable=elem.get("clickable", True),
                    description=elem.get("description"),
                ))
            
            return UIState(
                app_name=data.get("app_name", "Unknown"),
                screen_description=data.get("screen_description", ""),
                elements=elements,
                error_message=data.get("error_message"),
                popup_visible=data.get("popup_visible", False),
                available_actions=data.get("available_actions", []),
                raw_response=response
            )
            
        except json.JSONDecodeError:
            # If JSON parsing fails, create basic UIState from text
            return UIState(
                app_name="Unknown",
                screen_description=response[:500],
                error_message="Failed to parse structured response",
                raw_response=response
            )
    
    def capture_and_analyze(
        self, 
        device_serial: Optional[str] = None
    ) -> UIState:
        """
        Convenience method: take screenshot and analyze in one call.
        
        Args:
            device_serial: Optional device serial (uses default if not specified)
            
        Returns:
            UIState with analysis results
        """
        screenshot_path = self.take_screenshot(device_serial)
        return self.analyze_screenshot(screenshot_path)
    
    def find_element_by_text(
        self, 
        ui_state: UIState, 
        text: str,
        partial_match: bool = True
    ) -> Optional[UIElement]:
        """
        Find a UI element by its text content.
        
        Args:
            ui_state: Analyzed UI state
            text: Text to search for
            partial_match: If True, matches substring
            
        Returns:
            UIElement if found, None otherwise
        """
        text_lower = text.lower()
        for element in ui_state.elements:
            elem_text = element.text.lower()
            if partial_match:
                if text_lower in elem_text:
                    return element
            else:
                if text_lower == elem_text:
                    return element
        return None
    
    def find_elements_by_type(
        self, 
        ui_state: UIState, 
        element_type: str
    ) -> List[UIElement]:
        """
        Find all UI elements of a specific type.
        
        Args:
            ui_state: Analyzed UI state
            element_type: Type to filter by (button, input_field, etc.)
            
        Returns:
            List of matching UIElements
        """
        return [
            e for e in ui_state.elements 
            if e.element_type.lower() == element_type.lower()
        ]


# =============================================================================
# Convenience functions for direct use
# =============================================================================

def analyze_screen(device_serial: str) -> UIState:
    """Quick function to capture and analyze current screen"""
    perception = Perception(device_serial)
    return perception.capture_and_analyze()


def get_screen_elements(device_serial: str) -> List[Dict[str, Any]]:
    """Quick function to get list of UI elements as dicts"""
    ui_state = analyze_screen(device_serial)
    return [
        {
            "type": e.element_type,
            "text": e.text,
            "x": e.x,
            "y": e.y,
            "clickable": e.clickable
        }
        for e in ui_state.elements
    ]
