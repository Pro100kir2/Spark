"""Pre-commit hooks runner module."""

import subprocess
import shlex
from typing import List, Dict, Tuple
from dataclasses import dataclass

from .logger import Logger
from .error_handler import GitOperationError


@dataclass
class HookResult:
    """Result of running a pre-commit hook."""
    command: str
    success: bool
    output: str
    error: str


class PreCommitHooks:
    """Runs pre-commit hooks before commit."""
    
    def __init__(self, logger: Logger, commands: List[str], dry_run: bool = False):
        """
        Initialize pre-commit hooks runner.
        
        Args:
            logger: Logger instance.
            commands: List of commands to run.
            dry_run: If True, don't execute actual commands.
        """
        self.logger = logger
        self.commands = commands
        self.dry_run = dry_run
    
    def run_all(self) -> Tuple[bool, List[HookResult]]:
        """
        Run all pre-commit hooks.
        
        Returns:
            Tuple of (all_passed, results).
        """
        if not self.commands:
            self.logger.info("No pre-commit hooks configured")
            return True, []
        
        self.logger.step("Running pre-commit hooks")
        
        results = []
        all_passed = True
        
        for command in self.commands:
            result = self._run_hook(command)
            results.append(result)
            
            if not result.success:
                all_passed = False
                self.logger.failure(f"Hook failed: {command}")
            else:
                self.logger.success(f"Hook passed: {command}")
        
        return all_passed, results
    
    def _run_hook(self, command: str) -> HookResult:
        """
        Run a single pre-commit hook.
        
        Args:
            command: Command to run.
            
        Returns:
            HookResult object.
        """
        self.logger.info(f"Running: {command}")
        
        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would run: {command}")
            return HookResult(
                command=command,
                success=True,
                output="[DRY-RUN] Command not executed",
                error=""
            )
        
        try:
            # Parse command safely using shlex to prevent shell injection
            args = shlex.split(command)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            success = result.returncode == 0
            
            return HookResult(
                command=command,
                success=success,
                output=result.stdout,
                error=result.stderr
            )
            
        except subprocess.TimeoutExpired:
            return HookResult(
                command=command,
                success=False,
                output="",
                error="Command timed out"
            )
        except (ValueError, FileNotFoundError) as e:
            return HookResult(
                command=command,
                success=False,
                output="",
                error=f"Command parsing or execution error: {str(e)}"
            )
        except Exception as e:
            return HookResult(
                command=command,
                success=False,
                output="",
                error=f"Unexpected error: {str(e)}"
            )
