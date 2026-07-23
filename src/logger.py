#!/usr/bin/env python3
"""
Centralized logging system for Git automation script.
Provides detailed logging with timestamps and different log levels.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    """Centralized logger with file and console output."""
    
    def __init__(self, log_dir: Optional[Path] = None, verbose: bool = False):
        """
        Initialize logger.
        
        Args:
            log_dir: Directory for log files. If None, logs only to console.
            verbose: Enable DEBUG level logging.
        """
        self.logger = logging.getLogger('git-automation')
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if log_dir specified)
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f'git-automation-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            self.log_file = log_file
        else:
            self.log_file = None
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: bool = False):
        """Log critical message."""
        self.logger.critical(message, exc_info=exc_info)
    
    def git_command(self, command: str):
        """Log Git command execution."""
        self.debug(f"Git command: {command}")
    
    def github_api(self, action: str, details: str = ""):
        """Log GitHub API call."""
        if details:
            self.debug(f"GitHub API: {action} - {details}")
        else:
            self.debug(f"GitHub API: {action}")
    
    def step(self, step_name: str):
        """Log major workflow step."""
        self.info(f"--- {step_name} ---")
    
    def success(self, message: str):
        """Log success message."""
        self.info(f"✓ {message}")
    
    def failure(self, message: str):
        """Log failure message."""
        self.error(f"✗ {message}")
