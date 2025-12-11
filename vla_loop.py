"""
VLA Agent Loop

Main orchestration module that combines Perception, Planning, and Execution
into a complete Vision-Language-Action automation loop.

This is the entry point for running VLA automation tasks.
"""

import json
import time
import sys
import os
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

sys.path.insert(0, os.path.expanduser("~/deepagents/libs/deepagents"))

from .config import VLA_CONFIG, SCREENSHOT_DIR
from .perception import Perception, UIState
from .planner import Planner, PlannerContext
from .executor import Executor, Action, ActionType, ActionResult


class AgentStatus(Enum):
    """Status of the VLA agent"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class StepRecord:
    """Record of a single step in the VLA loop"""
    step_number: int
    timestamp: str
    ui_state_summary: str
    action: Dict[str, Any]
    result: Dict[str, Any]
    screenshot_path: Optional[str] = None
    duration_ms: int = 0


@dataclass
class AgentResult:
    """Final result of VLA agent execution"""
    success: bool
    status: AgentStatus
    task: str
    total_steps: int
    total_duration_ms: int
    final_screen: Optional[str] = None
    error: Optional[str] = None
    history: List[StepRecord] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "status": self.status.value,
            "task": self.task,
            "total_steps": self.total_steps,
            "total_duration_ms": self.total_duration_ms,
            "final_screen": self.final_screen,
            "error": self.error,
            "history": [
                {
                    "step": h.step_number,
                    "action": h.action,
                    "result": h.result,
                }
                for h in self.history
            ]
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class VLAAgent:
    """
    Vision-Language-Action Agent for Android automation.
    
    Combines:
    - Perception (Qwen VL): Analyzes screenshots to understand UI
    - Planning (Qwen Coder): Decides next action based on task and UI
    - Execution (ADB tools): Performs actions on the device
    
    Usage:
        agent = VLAAgent(
            task="Open Play Store and search for WhatsApp",
            device_serial="RSCR70FW19K"
        )
        result = agent.run()
        
        if result.success:
            print("Task completed!")
        else:
            print(f"Task failed: {result.error}")
    """
    
    def __init__(
        self,
        task: str,
        device_serial: Optional[str] = None,
        max_steps: Optional[int] = None,
        step_delay: Optional[float] = None,
        on_step: Optional[Callable[[StepRecord], None]] = None,
        verbose: bool = True,
    ):
        """
        Initialize VLA Agent.
        
        Args:
            task: Natural language description of what to accomplish
            device_serial: Android device serial (auto-detects if None)
            max_steps: Maximum steps before giving up (default from config)
            step_delay: Seconds to wait between steps (default from config)
            on_step: Optional callback function called after each step
            verbose: Print progress to console
        """
        self.task = task
        self.device_serial = device_serial or self._detect_device()
        self.max_steps = max_steps or VLA_CONFIG["max_steps"]
        self.step_delay = step_delay or VLA_CONFIG["step_delay"]
        self.on_step = on_step
        self.verbose = verbose
        
        # Initialize components
        self.perception = Perception(self.device_serial)
        self.planner = Planner()
        self.executor = Executor(self.device_serial)
        
        # State
        self.status = AgentStatus.IDLE
        self.history: List[StepRecord] = []
        self.current_step = 0
        self._stop_requested = False
    
    def _detect_device(self) -> str:
        """Auto-detect connected Android device"""
        import subprocess
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().split('\n')[1:]
        for line in lines:
            if '\t' in line and 'device' in line:
                return line.split('\t')[0]
        raise RuntimeError("No Android device connected")
    
    def _log(self, message: str):
        """Print log message if verbose"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")
    
    def _log_step(self, step: int, action: str, status: str):
        """Print step progress"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Step {step}/{self.max_steps}: {action} → {status}")
    
    def stop(self):
        """Request the agent to stop after current step"""
        self._stop_requested = True
        self._log("Stop requested - will stop after current step")
    
    def run(self) -> AgentResult:
        """
        Execute the VLA automation loop.
        
        Returns:
            AgentResult with success status and execution history
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        self.history = []
        self.current_step = 0
        self._stop_requested = False
        
        self._log(f"Starting VLA Agent")
        self._log(f"Task: {self.task}")
        self._log(f"Device: {self.device_serial}")
        self._log(f"Max steps: {self.max_steps}")
        self._log("-" * 50)
        
        try:
            for step in range(1, self.max_steps + 1):
                self.current_step = step
                
                # Check for stop request
                if self._stop_requested:
                    self.status = AgentStatus.STOPPED
                    return self._build_result(
                        success=False,
                        error="Agent stopped by user",
                        start_time=start_time
                    )
                
                # Execute one step of the VLA loop
                step_result = self._execute_step(step)
                
                # Check if task is complete or failed
                if step_result.action.action_type == ActionType.TASK_COMPLETE:
                    self.status = AgentStatus.COMPLETED
                    self._log("✅ Task completed successfully!")
                    return self._build_result(
                        success=True,
                        start_time=start_time
                    )
                
                if step_result.action.action_type == ActionType.TASK_FAILED:
                    self.status = AgentStatus.FAILED
                    self._log(f"❌ Task failed: {step_result.action.reasoning}")
                    return self._build_result(
                        success=False,
                        error=step_result.action.reasoning,
                        start_time=start_time
                    )
                
                # Wait before next step
                time.sleep(self.step_delay)
            
            # Max steps reached
            self.status = AgentStatus.FAILED
            self._log(f"❌ Max steps ({self.max_steps}) reached without completing task")
            return self._build_result(
                success=False,
                error=f"Max steps ({self.max_steps}) reached",
                start_time=start_time
            )
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            self._log(f"❌ Agent error: {str(e)}")
            import traceback
            if self.verbose:
                traceback.print_exc()
            return self._build_result(
                success=False,
                error=str(e),
                start_time=start_time
            )
    
    def _execute_step(self, step_number: int) -> ActionResult:
        """Execute a single step of the VLA loop"""
        step_start = time.time()
        
        # 1. PERCEPTION: Capture and analyze screen
        self._log(f"Step {step_number}: Capturing screen...")
        
        # Small delay before screenshot to let UI settle
        time.sleep(VLA_CONFIG.get("screenshot_delay", 0.5))
        
        screenshot_path = self.perception.take_screenshot()
        ui_state = self.perception.analyze_screenshot(screenshot_path)
        
        self._log(f"  Screen: {ui_state.app_name}")
        self._log(f"  Elements: {len(ui_state.elements)} found")
        
        # 2. PLANNING: Decide next action
        self._log(f"  Planning next action...")
        
        # Build history for context
        history_for_planner = [
            {
                "action": h.action,
                "result": h.result.get("success", False),
                "screen_summary": h.ui_state_summary
            }
            for h in self.history[-VLA_CONFIG.get("history_length", 10):]
        ]
        
        context = PlannerContext(
            task=self.task,
            ui_state=ui_state,
            history=history_for_planner,
            step_number=step_number,
            max_steps=self.max_steps
        )
        
        action = self.planner.plan_next_action(context)
        
        self._log(f"  Action: {action.action_type.value} {action.params}")
        self._log(f"  Reason: {action.reasoning[:80]}...")
        
        # 3. EXECUTION: Perform the action
        if action.action_type not in [ActionType.TASK_COMPLETE, ActionType.TASK_FAILED]:
            self._log(f"  Executing...")
            result = self.executor.execute(action)
            status = "✓" if result.success else "✗"
            self._log(f"  Result: {status} {result.message}")
        else:
            # Task complete or failed - no execution needed
            result = ActionResult(
                success=True,
                action=action,
                message=action.reasoning
            )
        
        # Record step
        step_duration = int((time.time() - step_start) * 1000)
        step_record = StepRecord(
            step_number=step_number,
            timestamp=datetime.now().isoformat(),
            ui_state_summary=ui_state.summary,
            action={
                "type": action.action_type.value,
                "params": action.params,
                "reasoning": action.reasoning
            },
            result={
                "success": result.success,
                "message": result.message,
                "error": result.error
            },
            screenshot_path=screenshot_path,
            duration_ms=step_duration
        )
        self.history.append(step_record)
        
        # Call step callback if provided
        if self.on_step:
            self.on_step(step_record)
        
        self._log_step(
            step_number,
            f"{action.action_type.value}",
            "OK" if result.success else f"FAIL: {result.error}"
        )
        
        return result
    
    def _build_result(
        self,
        success: bool,
        start_time: float,
        error: Optional[str] = None
    ) -> AgentResult:
        """Build the final agent result"""
        total_duration = int((time.time() - start_time) * 1000)
        
        # Get final screenshot path
        final_screen = None
        if self.history:
            final_screen = self.history[-1].screenshot_path
        
        return AgentResult(
            success=success,
            status=self.status,
            task=self.task,
            total_steps=len(self.history),
            total_duration_ms=total_duration,
            final_screen=final_screen,
            error=error,
            history=self.history
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "status": self.status.value,
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "task": self.task,
            "device": self.device_serial,
            "history_length": len(self.history)
        }


# =============================================================================
# Convenience functions for quick tasks
# =============================================================================

def run_task(
    task: str,
    device_serial: Optional[str] = None,
    max_steps: int = 30,
    verbose: bool = True
) -> AgentResult:
    """
    Quick function to run a VLA task.
    
    Args:
        task: What to accomplish
        device_serial: Device to use (auto-detect if None)
        max_steps: Maximum steps
        verbose: Print progress
        
    Returns:
        AgentResult
    """
    agent = VLAAgent(
        task=task,
        device_serial=device_serial,
        max_steps=max_steps,
        verbose=verbose
    )
    return agent.run()


def open_app_and_search(
    app_name: str,
    search_term: str,
    device_serial: Optional[str] = None
) -> AgentResult:
    """
    Convenience function: Open an app and search for something.
    
    Args:
        app_name: Name of the app (e.g., "Play Store", "Chrome")
        search_term: What to search for
        device_serial: Device to use
        
    Returns:
        AgentResult
    """
    task = f"Open {app_name}, find the search bar, and search for '{search_term}'"
    return run_task(task, device_serial)


def install_app_from_play_store(
    app_name: str,
    device_serial: Optional[str] = None
) -> AgentResult:
    """
    Convenience function: Install an app from Play Store.
    
    Args:
        app_name: Name of the app to install
        device_serial: Device to use
        
    Returns:
        AgentResult
    """
    task = f"""Open the Google Play Store app, search for '{app_name}', 
    tap on the correct app from results, tap Install, wait for installation 
    to complete, then tap Open to launch the app. Mark complete when the app opens."""
    return run_task(task, device_serial, max_steps=40)


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Command line entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="VLA Android Automation Agent")
    parser.add_argument("task", help="Task to accomplish")
    parser.add_argument("-d", "--device", help="Device serial")
    parser.add_argument("-s", "--steps", type=int, default=30, help="Max steps")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")
    
    args = parser.parse_args()
    
    result = run_task(
        task=args.task,
        device_serial=args.device,
        max_steps=args.steps,
        verbose=not args.quiet
    )
    
    print("\n" + "=" * 50)
    print("RESULT:", "SUCCESS" if result.success else "FAILED")
    print("Steps:", result.total_steps)
    print("Duration:", f"{result.total_duration_ms / 1000:.1f}s")
    if result.error:
        print("Error:", result.error)
    print("=" * 50)
    
    # Exit with appropriate code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
