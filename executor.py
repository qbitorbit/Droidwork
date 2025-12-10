"""
VLA Executor Module

Handles action execution on Android devices.
This is the "Hands" of the VLA pipeline.

Wraps your existing 33 ADB tools for use by the VLA agent.
"""

import json
import time
import sys
import os
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Add path for android_tools
sys.path.insert(0, os.path.expanduser("~/deepagents/libs/deepagents"))

from .config import VLA_CONFIG


class ActionType(Enum):
    """Supported action types"""
    TAP = "tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    DRAG = "drag"
    INPUT_TEXT = "input_text"
    PRESS_KEY = "press_key"
    WAIT = "wait"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    GO_BACK = "go_back"
    GO_HOME = "go_home"
    OPEN_APP = "open_app"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"


@dataclass
class Action:
    """Represents an action to execute"""
    action_type: ActionType
    params: Dict[str, Any]
    reasoning: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Action":
        """Create Action from dictionary"""
        action_str = data.get("action", "").lower().replace(" ", "_")
        
        # Map string to ActionType
        action_map = {
            "tap": ActionType.TAP,
            "long_press": ActionType.LONG_PRESS,
            "swipe": ActionType.SWIPE,
            "drag": ActionType.DRAG,
            "input_text": ActionType.INPUT_TEXT,
            "input": ActionType.INPUT_TEXT,
            "type": ActionType.INPUT_TEXT,
            "press_key": ActionType.PRESS_KEY,
            "keypress": ActionType.PRESS_KEY,
            "wait": ActionType.WAIT,
            "scroll_up": ActionType.SCROLL_UP,
            "scroll_down": ActionType.SCROLL_DOWN,
            "go_back": ActionType.GO_BACK,
            "back": ActionType.GO_BACK,
            "go_home": ActionType.GO_HOME,
            "home": ActionType.GO_HOME,
            "open_app": ActionType.OPEN_APP,
            "launch_app": ActionType.OPEN_APP,
            "task_complete": ActionType.TASK_COMPLETE,
            "done": ActionType.TASK_COMPLETE,
            "complete": ActionType.TASK_COMPLETE,
            "task_failed": ActionType.TASK_FAILED,
            "fail": ActionType.TASK_FAILED,
            "failed": ActionType.TASK_FAILED,
        }
        
        action_type = action_map.get(action_str, ActionType.WAIT)
        
        return cls(
            action_type=action_type,
            params=data.get("params", {}),
            reasoning=data.get("reasoning", "")
        )


@dataclass
class ActionResult:
    """Result of an executed action"""
    success: bool
    action: Action
    message: str = ""
    error: Optional[str] = None
    duration_ms: int = 0


class Executor:
    """
    Executes actions on Android devices using ADB tools.
    
    Usage:
        executor = Executor(device_serial="RSCR70FW19K")
        result = executor.execute(action)
    """
    
    def __init__(self, device_serial: Optional[str] = None):
        self.device_serial = device_serial
        self._load_android_tools()
    
    def _load_android_tools(self):
        """Load android_tools functions"""
        try:
            from deepagents.android_tools import (
                tap,
                long_press,
                swipe,
                drag,
                input_text,
                press_key,
                start_app,
                stop_app,
            )
            self._tap = tap
            self._long_press = long_press
            self._swipe = swipe
            self._drag = drag
            self._input_text = input_text
            self._press_key = press_key
            self._start_app = start_app
            self._stop_app = stop_app
            self._tools_loaded = True
        except ImportError as e:
            print(f"Warning: Could not load android_tools: {e}")
            self._tools_loaded = False
    
    def execute(self, action: Action) -> ActionResult:
        """
        Execute an action on the device.
        
        Args:
            action: Action to execute
            
        Returns:
            ActionResult with success status
        """
        start_time = time.time()
        
        try:
            if action.action_type == ActionType.TAP:
                result = self._execute_tap(action.params)
            elif action.action_type == ActionType.LONG_PRESS:
                result = self._execute_long_press(action.params)
            elif action.action_type == ActionType.SWIPE:
                result = self._execute_swipe(action.params)
            elif action.action_type == ActionType.DRAG:
                result = self._execute_drag(action.params)
            elif action.action_type == ActionType.INPUT_TEXT:
                result = self._execute_input_text(action.params)
            elif action.action_type == ActionType.PRESS_KEY:
                result = self._execute_press_key(action.params)
            elif action.action_type == ActionType.WAIT:
                result = self._execute_wait(action.params)
            elif action.action_type == ActionType.SCROLL_UP:
                result = self._execute_scroll_up(action.params)
            elif action.action_type == ActionType.SCROLL_DOWN:
                result = self._execute_scroll_down(action.params)
            elif action.action_type == ActionType.GO_BACK:
                result = self._execute_go_back()
            elif action.action_type == ActionType.GO_HOME:
                result = self._execute_go_home()
            elif action.action_type == ActionType.OPEN_APP:
                result = self._execute_open_app(action.params)
            elif action.action_type == ActionType.TASK_COMPLETE:
                result = (True, "Task marked as complete")
            elif action.action_type == ActionType.TASK_FAILED:
                result = (False, "Task marked as failed")
            else:
                result = (False, f"Unknown action type: {action.action_type}")
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return ActionResult(
                success=result[0],
                action=action,
                message=result[1],
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ActionResult(
                success=False,
                action=action,
                message="Execution failed",
                error=str(e),
                duration_ms=duration_ms
            )
    
    def _parse_tool_result(self, result: str) -> Tuple[bool, str]:
        """Parse JSON result from android_tools"""
        try:
            data = json.loads(result)
            success = data.get("success", False)
            message = data.get("error", "OK") if not success else "OK"
            return (success, message)
        except json.JSONDecodeError:
            return (True, result)  # Assume success if not JSON
    
    def _execute_tap(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute tap action"""
        x = params.get("x", 0)
        y = params.get("y", 0)
        
        result = self._tap.invoke({
            "x": int(x),
            "y": int(y),
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)
    
    def _execute_long_press(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute long press action"""
        x = params.get("x", 0)
        y = params.get("y", 0)
        duration = params.get("duration_ms", 1000)
        
        result = self._long_press.invoke({
            "x": int(x),
            "y": int(y),
            "duration_ms": int(duration),
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)
    
    def _execute_swipe(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute swipe action"""
        result = self._swipe.invoke({
            "start_x": int(params.get("start_x", params.get("x1", 0))),
            "start_y": int(params.get("start_y", params.get("y1", 0))),
            "end_x": int(params.get("end_x", params.get("x2", 0))),
            "end_y": int(params.get("end_y", params.get("y2", 0))),
            "duration_ms": int(params.get("duration_ms", 300)),
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)
    
    def _execute_drag(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute drag action"""
        result = self._drag.invoke({
            "start_x": int(params.get("start_x", params.get("x1", 0))),
            "start_y": int(params.get("start_y", params.get("y1", 0))),
            "end_x": int(params.get("end_x", params.get("x2", 0))),
            "end_y": int(params.get("end_y", params.get("y2", 0))),
            "duration_ms": int(params.get("duration_ms", 1000)),
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)
    
    def _execute_input_text(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute text input action"""
        text = params.get("text", "")
        
        result = self._input_text.invoke({
            "text": str(text),
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)
    
    def _execute_press_key(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute key press action"""
        key = params.get("key", params.get("keycode", ""))
        
        # Map common key names to Android keycodes
        key_map = {
            "back": "KEYCODE_BACK",
            "home": "KEYCODE_HOME",
            "enter": "KEYCODE_ENTER",
            "delete": "KEYCODE_DEL",
            "tab": "KEYCODE_TAB",
            "menu": "KEYCODE_MENU",
            "search": "KEYCODE_SEARCH",
            "power": "KEYCODE_POWER",
            "volume_up": "KEYCODE_VOLUME_UP",
            "volume_down": "KEYCODE_VOLUME_DOWN",
        }
        
        keycode = key_map.get(str(key).lower(), str(key))
        
        result = self._press_key.invoke({
            "keycode": keycode,
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)
    
    def _execute_wait(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute wait action"""
        seconds = params.get("seconds", params.get("duration", 1))
        time.sleep(float(seconds))
        return (True, f"Waited {seconds} seconds")
    
    def _execute_scroll_up(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute scroll up (swipe down to scroll up)"""
        # Default to center of screen, swipe up
        start_x = params.get("x", 540)
        start_y = params.get("start_y", 1500)
        end_y = params.get("end_y", 500)
        
        result = self._swipe.invoke({
            "start_x": int(start_x),
            "start_y": int(start_y),
            "end_x": int(start_x),
            "end_y": int(end_y),
            "duration_ms": 300,
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)
    
    def _execute_scroll_down(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute scroll down (swipe up to scroll down)"""
        start_x = params.get("x", 540)
        start_y = params.get("start_y", 500)
        end_y = params.get("end_y", 1500)
        
        result = self._swipe.invoke({
            "start_x": int(start_x),
            "start_y": int(start_y),
            "end_x": int(start_x),
            "end_y": int(end_y),
            "duration_ms": 300,
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)
    
    def _execute_go_back(self) -> Tuple[bool, str]:
        """Press back button"""
        result = self._press_key.invoke({
            "keycode": "KEYCODE_BACK",
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)
    
    def _execute_go_home(self) -> Tuple[bool, str]:
        """Press home button"""
        result = self._press_key.invoke({
            "keycode": "KEYCODE_HOME",
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)
    
    def _execute_open_app(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Open/launch an app by package name"""
        package = params.get("package", params.get("app", ""))
        
        result = self._start_app.invoke({
            "package_name": package,
            "device_serial": self.device_serial
        })
        return self._parse_tool_result(result)


# =============================================================================
# Convenience functions
# =============================================================================

def tap_at(x: int, y: int, device_serial: str) -> bool:
    """Quick tap at coordinates"""
    executor = Executor(device_serial)
    action = Action(ActionType.TAP, {"x": x, "y": y})
    result = executor.execute(action)
    return result.success


def input_text(text: str, device_serial: str) -> bool:
    """Quick text input"""
    executor = Executor(device_serial)
    action = Action(ActionType.INPUT_TEXT, {"text": text})
    result = executor.execute(action)
    return result.success


def go_back(device_serial: str) -> bool:
    """Quick back button press"""
    executor = Executor(device_serial)
    action = Action(ActionType.GO_BACK, {})
    result = executor.execute(action)
    return result.success


def go_home(device_serial: str) -> bool:
    """Quick home button press"""
    executor = Executor(device_serial)
    action = Action(ActionType.GO_HOME, {})
    result = executor.execute(action)
    return result.success
