#!/usr/bin/env python3
"""
Git automation script package.
"""

from .logger import Logger
from .error_handler import ErrorHandler, GitAutomationError
from .git_operations import GitOperations, GitStatus, FileChange
from .github_client import GitHubClient, PRState, PullRequest
from .change_analyzer import ChangeAnalyzer, ChangeAnalysis
from .branch_namer import BranchNameGenerator
from .commit_generator import CommitMessageGenerator
from .pre_commit_hooks import PreCommitHooks
from .config_loader import ConfigLoader, Config
from .input_validator import InputValidator
from .dependency_installer import DependencyInstaller

__all__ = [
    'Logger',
    'ErrorHandler',
    'GitAutomationError',
    'GitOperations',
    'GitStatus',
    'FileChange',
    'GitHubClient',
    'PRState',
    'PullRequest',
    'ChangeAnalyzer',
    'ChangeAnalysis',
    'BranchNameGenerator',
    'CommitMessageGenerator',
    'PreCommitHooks',
    'ConfigLoader',
    'Config',
    'InputValidator',
    'DependencyInstaller',
]
