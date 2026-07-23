#!/usr/bin/env python3
"""
Configuration loader module for Git automation script.
Loads and validates configuration from YAML files.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass

from .logger import Logger


@dataclass
class PreCommitConfig:
    """Pre-commit hooks configuration."""
    enabled: bool
    commands: List[str]


@dataclass
class GitConfig:
    """Git configuration."""
    main_branches: List[str]


@dataclass
class BranchNamingConfig:
    """Branch naming configuration."""
    max_length: int
    reserved_names: List[str]


@dataclass
class CommitConfig:
    """Commit message configuration."""
    max_description_length: int
    language: str


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str
    format: str
    date_format: str


@dataclass
class GitHubConfig:
    """GitHub configuration."""
    pr_poll_interval: int
    draft_prs: bool


@dataclass
class SecurityConfig:
    """Security configuration."""
    sensitive_files: List[str]


@dataclass
class Config:
    """Main configuration class."""
    github: GitHubConfig
    git: GitConfig
    branch_naming: BranchNamingConfig
    commit: CommitConfig
    pre_commit: PreCommitConfig
    logging: LoggingConfig
    security: SecurityConfig


class ConfigLoader:
    """Loads and validates configuration from YAML files."""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    
    def __init__(self, logger: Logger, config_path: Path = None):
        """
        Initialize config loader.
        
        Args:
            logger: Logger instance.
            config_path: Path to config file. If None, uses default.
        """
        self.logger = logger
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
    
    def load_config(self) -> Config:
        """
        Load configuration from YAML file.
        
        Returns:
            Config object with loaded settings.
            
        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config is invalid.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        self.logger.debug(f"Loading configuration from: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Validate and parse configuration
        return self._parse_config(config_data)
    
    def _parse_config(self, data: Dict[str, Any]) -> Config:
        """
        Parse and validate configuration data.
        
        Args:
            data: Raw configuration data from YAML.
            
        Returns:
            Parsed Config object.
            
        Raises:
            ValueError: If configuration is invalid.
        """
        try:
            # Parse GitHub config
            github_data = data.get('github', {})
            github = GitHubConfig(
                pr_poll_interval=github_data.get('pr_poll_interval', 60),
                draft_prs=github_data.get('draft_prs', False)
            )
            
            # Parse Git config
            git_data = data.get('git', {})
            git = GitConfig(
                main_branches=git_data.get('main_branches', ['main', 'master', 'develop'])
            )
            
            # Parse branch naming config
            branch_naming_data = data.get('branch_naming', {})
            branch_naming = BranchNamingConfig(
                max_length=branch_naming_data.get('max_length', 40),
                reserved_names=branch_naming_data.get('reserved_names', ['head', 'main', 'master', 'develop'])
            )
            
            # Parse commit config
            commit_data = data.get('commit', {})
            commit = CommitConfig(
                max_description_length=commit_data.get('max_description_length', 72),
                language=commit_data.get('language', 'en')
            )
            
            # Parse pre-commit config
            pre_commit_data = data.get('pre_commit', {})
            pre_commit = PreCommitConfig(
                enabled=pre_commit_data.get('enabled', True),
                commands=pre_commit_data.get('commands', [])
            )
            
            # Parse logging config
            logging_data = data.get('logging', {})
            logging = LoggingConfig(
                level=logging_data.get('level', 'INFO'),
                format=logging_data.get('format', '%(asctime)s - %(levelname)s - %(message)s'),
                date_format=logging_data.get('date_format', '%Y-%m-%d %H:%M:%S')
            )
            
            # Parse security config
            security_data = data.get('security', {})
            security = SecurityConfig(
                sensitive_files=security_data.get('sensitive_files', [
                    '.env', '.gitignore', '.idea', '.vscode', 'node_modules',
                    'dist', 'build', 'coverage', '__pycache__', '.venv', 'venv'
                ])
            )
            
            return Config(
                github=github,
                git=git,
                branch_naming=branch_naming,
                commit=commit,
                pre_commit=pre_commit,
                logging=logging,
                security=security
            )
            
        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
    
    def get_pre_commit_commands(self) -> List[str]:
        """
        Get pre-commit commands from configuration.
        
        Returns:
            List of pre-commit commands.
        """
        config = self.load_config()
        return config.pre_commit.commands if config.pre_commit.enabled else []
    
    def get_sensitive_files(self) -> List[str]:
        """
        Get sensitive files list from configuration.
        
        Returns:
            List of sensitive file patterns.
        """
        config = self.load_config()
        return config.security.sensitive_files
