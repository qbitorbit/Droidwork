"""
VLA Planner Module

Handles action planning using Qwen Coder LLM.
This is the "Brain" of the VLA pipeline.

Takes UI state from Perception and decides the next action.
"""

import json
import sys
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import requests

sys.path.insert(0, os.path.expanduser("~/deepagents/libs/deepagents"))

from .config import (
    VLLM_BASE_URL,
    VLLM_API_KEY,
    LLM_MODEL,
    LLM_CONFIG,
    VLA_CONFIG,
)
from .perception import UIState
from .executor import Action, ActionType


@dataclass
class PlannerContext:
    """Context for the planner"""
    task: str                          # The goal to achieve
    ui_state: UIState                  # Current screen state
    history: List[Dict[str, Any]]      # Past actions and results
    step_number: int                   # Current step in the flow
    max_steps: int                     # Maximum allowed steps
    
    def to_prompt_context(self) -> str:
        """Format context for LLM prompt"""
        # Format history (last N actions)
        history_limit = VLA_CONFIG.get("history_length", 10)
        recent_history = self.history[-history_limit:] if self.history else []
        
        history_text = ""
        if recent_history:
            history_text = "## Recent Action History\n"
            for i, h in enumerate(recent_history):
                history_text += f"{i+1}. Action: {h.get('action', 'unknown')}\n"
                history_text += f"   Result: {h.get('result', 'unknown')}\n"
                history_text += f"   Screen after: {h.get('screen_summary', 'unknown')}\n"
        
        return f"""## Task
{self.task}

## Current Step
Step {self.step_number} of {self.max_steps}

## Current Screen State
App/Screen: {self.ui_state.app_name}
Description: {self.ui_state.screen_description}

### UI Elements on Screen
{self._format_elements()}

### Error/Popup Status
- Error visible: {self.ui_state.error_message or "None"}
- Popup visible: {self.ui_state.popup_visible}

### Suggested Actions from Vision
{self._format_available_actions()}

{history_text}"""

    def _format_elements(self) -> str:
        """Format UI elements for prompt"""
        if not self.ui_state.elements:
            return "No interactive elements detected"
        
        lines = []
        for i, elem in enumerate(self.ui_state.elements[:20]):  # Limit to 20
            lines.append(
                f"- [{elem.element_type}] \"{elem.text}\" at ({elem.x}, {elem.y})"
                f"{' (clickable)' if elem.clickable else ''}"
            )
        
        if len(self.ui_state.elements) > 20:
            lines.append(f"... and {len(self.ui_state.elements) - 20} more elements")
        
        return "\n".join(lines)
    
    def _format_available_actions(self) -> str:
        """Format available actions for prompt"""
        if not self.ui_state.available_actions:
            return "No specific actions suggested"
        
        return "\n".join(f"- {a}" for a in self.ui_state.available_actions[:10])


class Planner:
    """
    Plans actions using Qwen Coder LLM.
    
    Usage:
        planner = Planner()
        action = planner.plan_next_action(context)
    """
    
    def __init__(self):
        self.api_url = f"{VLLM_BASE_URL}/chat/completions"
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the planner"""
        return """You are an Android automation agent. Your job is to analyze the current screen state and decide the next action to accomplish the given task.

## Available Actions

You can perform these actions:
- TAP(x, y) - Tap at screen coordinates
- LONG_PRESS(x, y, duration_ms) - Long press at coordinates
- SWIPE(start_x, start_y, end_x, end_y) - Swipe gesture
- INPUT_TEXT(text) - Type text (screen must have focused input field)
- PRESS_KEY(key) - Press key: back, home, enter, delete, menu, search
- WAIT(seconds) - Wait for UI to update
- SCROLL_UP() - Scroll the screen up
- SCROLL_DOWN() - Scroll the screen down
- GO_BACK() - Press back button
- GO_HOME() - Press home button
- OPEN_APP(package) - Launch app by package name
- TASK_COMPLETE() - Task is finished successfully
- TASK_FAILED() - Task cannot be completed

## Response Format

You MUST respond with valid JSON only:
````json
{
    "action": "TAP",
    "params": {
        "x": 540,
        "y": 1200
    },
    "reasoning": "Tapping the Install button to begin app installation"
}
````

## Guidelines

1. Always check if the task is already complete before taking action
2. If you see an error or unexpected popup, handle it first
3. Use exact coordinates from the UI elements when tapping
4. After typing text, you may need to tap a button or press enter
5. If stuck, try scrolling to find the needed element
6. If task seems impossible, return TASK_FAILED with explanation
7. Be patient - some actions take time (install, download, etc.)
8. Maximum steps allowed - if running out, prioritize completion

## Common Patterns

- To search: tap search field → input text → tap search button or press enter
- To install app: tap Install → wait → tap Open (or handle permissions)
- To login: input username → tap next → input password → tap login
- To scroll: use SCROLL_DOWN to see more content
- To dismiss popup: tap outside, tap X, or press back"""

    def plan_next_action(self, context: PlannerContext) -> Action:
        """
        Plan the next action based on current context.
        
        Args:
            context: Current planner context with task, UI state, history
            
        Returns:
            Action to execute
        """
        # Build the user message
        user_message = f"""{context.to_prompt_context()}

## Your Task
Based on the current screen state and task goal, what is the single next action to take?

Remember:
- Respond with JSON only
- Use exact coordinates from the UI elements list
- If task is complete, use TASK_COMPLETE
- If task is impossible, use TASK_FAILED with explanation"""

        # Make LLM request
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": LLM_CONFIG["temperature"],
            "max_tokens": LLM_CONFIG["max_tokens"],
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VLLM_API_KEY}"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=LLM_CONFIG["timeout"]
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            return self._parse_llm_response(content)
            
        except requests.exceptions.Timeout:
            # On timeout, wait and retry or fail gracefully
            return Action(
                action_type=ActionType.WAIT,
                params={"seconds": 2},
                reasoning="LLM timeout - waiting before retry"
            )
        except Exception as e:
            return Action(
                action_type=ActionType.TASK_FAILED,
                params={},
                reasoning=f"Planner error: {str(e)}"
            )
    
    def _parse_llm_response(self, response: str) -> Action:
        """Parse LLM response into Action"""
        try:
            # Extract JSON from response
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            return Action.from_dict(data)
            
        except json.JSONDecodeError:
            # Try to extract action from plain text
            response_lower = response.lower()
            
            if "task_complete" in response_lower or "task is complete" in response_lower:
                return Action(
                    action_type=ActionType.TASK_COMPLETE,
                    params={},
                    reasoning=response[:200]
                )
            elif "task_failed" in response_lower or "cannot complete" in response_lower:
                return Action(
                    action_type=ActionType.TASK_FAILED,
                    params={},
                    reasoning=response[:200]
                )
            else:
                # Default to wait if can't parse
                return Action(
                    action_type=ActionType.WAIT,
                    params={"seconds": 1},
                    reasoning=f"Could not parse response: {response[:100]}"
                )
    
    def evaluate_completion(
        self, 
        task: str, 
        ui_state: UIState,
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate if task is complete based on current state.
        
        Returns:
            Dict with 'complete' (bool), 'confidence' (float), 'reason' (str)
        """
        user_message = f"""## Task
{task}

## Current Screen
App: {ui_state.app_name}
Description: {ui_state.screen_description}

## Action History
{len(history)} actions taken

## Question
Is this task complete? Evaluate the current screen against the task goal.

Respond with JSON:
````json
{{
    "complete": true/false,
    "confidence": 0.0-1.0,
    "reason": "explanation"
}}
```"""

        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": "You evaluate if Android automation tasks are complete. Respond with JSON only."},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.1,
            "max_tokens": 500,
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VLLM_API_KEY}"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            
            return json.loads(json_str.strip())
            
        except Exception as e:
            return {
                "complete": False,
                "confidence": 0.0,
                "reason": f"Evaluation error: {str(e)}"
            }


# =============================================================================
# Convenience functions
# =============================================================================

def plan_action(
    task: str,
    ui_state: UIState,
    history: List[Dict[str, Any]] = None,
    step_number: int = 1
) -> Action:
    """Quick function to plan next action"""
    planner = Planner()
    context = PlannerContext(
        task=task,
        ui_state=ui_state,
        history=history or [],
        step_number=step_number,
        max_steps=VLA_CONFIG["max_steps"]
    )
    return planner.plan_next_action(context)


def is_task_complete(
    task: str,
    ui_state: UIState,
    history: List[Dict[str, Any]] = None
) -> bool:
    """Quick function to check if task is complete"""
    planner = Planner()
    result = planner.evaluate_completion(task, ui_state, history or [])
    return result.get("complete", False) and result.get("confidence", 0) > 0.7
  
