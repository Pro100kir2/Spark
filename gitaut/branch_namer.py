#!/usr/bin/env python3
"""
Branch name generator module for Git automation script.
Generates meaningful branch names based on change analysis.
"""

import re
from typing import List, Optional

from .logger import Logger
from .change_analyzer import ChangeAnalysis


class BranchNameGenerator:
    """Generates meaningful branch names following Git Flow conventions."""
    
    def __init__(self, logger: Logger):
        """
        Initialize branch name generator.
        
        Args:
            logger: Logger instance.
        """
        self.logger = logger
    
    def generate_branch_name(self, analysis: ChangeAnalysis, custom_name: Optional[str] = None) -> str:
        """
        Generate a branch name based on change analysis.
        
        Args:
            analysis: ChangeAnalysis object.
            custom_name: Optional custom name override.
            
        Returns:
            Generated branch name.
        """
        if custom_name:
            return self._sanitize_branch_name(custom_name)
        
        self.logger.step("Генерация названия ветки")
        
        # Generate the descriptive part
        description = self._generate_description(analysis)
        
        # Use only description for branch name (type prefix only in commit messages)
        branch_name = description
        
        # Sanitize the branch name
        branch_name = self._sanitize_branch_name(branch_name)
        
        self.logger.info(f"Generated branch name: {branch_name}")
        return branch_name

    
    def _generate_description(self, analysis: ChangeAnalysis) -> str:
        """
        Generate a descriptive part of the branch name.
        
        Rules:
        - Semantic: action + entity (what changed, not where)
        - Max 3-4 words
        - kebab-case
        - Max ~50 chars
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            Description string.
        """
        # Extract action verb from change type
        action = self._extract_action(analysis)
        
        # Extract entity/object from diff content
        entity = self._extract_entity(analysis)
        
        if action and entity:
            description = f"{action}-{entity}"
        elif action:
            description = action
        elif entity:
            description = f"update-{entity}"
        else:
            # Fallback to generic description
            description = self._get_generic_description(analysis)
        
        # Smart truncation - don't break words
        description = self._smart_truncate(description, max_length=50)
        
        return description
    
    def _extract_action(self, analysis: ChangeAnalysis) -> str:
        """
        Extract action verb from change analysis.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            Action verb (add, fix, update, remove, refactor, etc.).
        """
        # Map likely change types to actions
        type_to_action = {
            'feat': 'add',
            'fix': 'fix',
            'bugfix': 'fix',
            'refactor': 'refactor',
            'perf': 'optimize',
            'style': 'format',
            'test': 'test',
            'docs': 'docs',
            'chore': 'update',
            'ci': 'ci',
            'build': 'build',
        }
        
        action = type_to_action.get(analysis.likely_type, 'update')
        
        # Override based on file operations
        if analysis.added_files and not analysis.modified_files and not analysis.deleted_files:
            action = 'add'
        elif analysis.deleted_files and not analysis.added_files and not analysis.modified_files:
            action = 'remove'
        
        return action
    
    def _extract_entity(self, analysis: ChangeAnalysis) -> str:
        """
        Extract entity/object from diff content.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            Entity name (what was changed).
        """
        # Extract from file names first (more specific than directories)
        entity = self._extract_entity_from_files(analysis)
        
        if not entity:
            # Fallback to diff patterns
            entity = self._extract_entity_from_diff(analysis.diff_summary)
        
        return entity
    
    def _extract_entity_from_files(self, analysis: ChangeAnalysis) -> str:
        """
        Extract entity from file names.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            Entity name.
        """
        all_files = analysis.added_files + analysis.modified_files + analysis.deleted_files
        
        # Common entity patterns in file names
        entity_keywords = [
            'auth', 'login', 'user', 'token', 'jwt', 'session', 'password',
            'api', 'endpoint', 'route', 'controller', 'handler',
            'model', 'schema', 'database', 'migration', 'query',
            'service', 'worker', 'job', 'task',
            'config', 'setting', 'env', 'environment',
            'cache', 'redis', 'queue',
            'payment', 'order', 'cart', 'checkout', 'invoice',
            'notification', 'email', 'sms', 'push',
            'upload', 'file', 'image', 'media',
            'search', 'filter', 'pagination',
            'validation', 'sanitization',
            'middleware', 'guard', 'interceptor',
            'component', 'widget', 'view', 'template',
            'hook', 'plugin', 'extension',
            'docker', 'deploy', 'ci', 'workflow',
        ]
        
        for file_path in all_files:
            file_name = file_path.split('/')[-1].lower()
            for keyword in entity_keywords:
                if keyword in file_name:
                    return keyword
        
        return ''
    
    def _extract_entity_from_diff(self, diff_summary: str) -> str:
        """
        Extract entity from diff summary.
        
        Args:
            diff_summary: Diff summary string.
            
        Returns:
            Entity name.
        """
        # Same keywords as file-based extraction
        entity_keywords = [
            'auth', 'login', 'user', 'token', 'jwt', 'session', 'password',
            'api', 'endpoint', 'route', 'controller', 'handler',
            'model', 'schema', 'database', 'migration', 'query',
            'service', 'worker', 'job', 'task',
            'config', 'setting', 'env', 'environment',
            'cache', 'redis', 'queue',
            'payment', 'order', 'cart', 'checkout', 'invoice',
            'notification', 'email', 'sms', 'push',
            'upload', 'file', 'image', 'media',
            'search', 'filter', 'pagination',
            'validation', 'sanitization',
            'middleware', 'guard', 'interceptor',
            'component', 'widget', 'view', 'template',
            'hook', 'plugin', 'extension',
            'docker', 'deploy', 'ci', 'workflow',
        ]
        
        diff_lower = diff_summary.lower()
        for keyword in entity_keywords:
            if keyword in diff_lower:
                return keyword
        
        return ''
    
    
    
    def _smart_truncate(self, text: str, max_length: int) -> str:
        """
        Truncate text without breaking words.
        
        Args:
            text: Text to truncate.
            max_length: Maximum length.
            
        Returns:
            Truncated text.
        """
        if len(text) <= max_length:
            return text
        
        # Find the last hyphen before max_length
        last_hyphen = text.rfind('-', 0, max_length)
        if last_hyphen > 0:
            return text[:last_hyphen]
        
        # If no hyphen, just truncate
        return text[:max_length]
    
    def _get_generic_description(self, analysis: ChangeAnalysis) -> str:
        """
        Get a generic description when no specific keywords are found.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            Generic description string.
        """
        if analysis.added_files:
            return 'add-feature'
        elif analysis.deleted_files:
            return 'remove-feature'
        elif analysis.modified_files:
            return 'update-feature'
        else:
            return 'changes'
    
    def _sanitize_branch_name(self, name: str) -> str:
        """
        Sanitize branch name to follow Git conventions.
        
        Args:
            name: Raw branch name.
            
        Returns:
            Sanitized branch name.
        """
        # Convert to lowercase
        name = name.lower()
        
        # Replace spaces, underscores, and colons with hyphens
        name = re.sub(r'[\s_:]+', '-', name)
        
        # Remove special characters except hyphens and alphanumerics
        name = re.sub(
            r'[^a-z0-9-]',
            '-',
            name
        )
        
        # Remove consecutive hyphens
        name = re.sub(r'-+', '-', name)
        
        # Remove leading/trailing hyphens
        name = name.strip('-')
        
        # Ensure it's not empty
        if not name:
            name = 'feature-branch'
        
        # Ensure it's not too long (Git limit is around 255 chars)
        if len(name) > 100:
            name = name[:100]
        
        return name
    
    def validate_branch_name(self, name: str) -> bool:
        """
        Validate that a branch name follows Git conventions.
        Uses git check-ref-format for official validation.
        
        Args:
            name: Branch name to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        # Check for empty name
        if not name:
            return False
        
        # Use git check-ref-format for official validation
        try:
            from .git_operations import GitOperations
            # Create a temporary GitOperations instance for validation
            # We need a logger, but we can create a minimal one
            from .logger import Logger
            temp_logger = Logger(verbose=False)
            git_ops = GitOperations(logger=temp_logger, dry_run=True)
            
            # Use git check-ref-format to validate
            result = git_ops._run_git_command(
                ['git', 'check-ref-format', '--allow-onelevel', f'refs/heads/{name}'],
                check=True,
                ignore_dry_run=True
            )
            return True
        except Exception:
            # If git command fails, name is invalid
            return False
