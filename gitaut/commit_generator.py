#!/usr/bin/env python3
"""
Commit message generator module for Git automation script.
Generates Conventional Commits messages based on change analysis.
"""

import re
from typing import Optional

from .logger import Logger
from .change_analyzer import ChangeAnalysis


class CommitMessageGenerator:
    """Generates Conventional Commits messages."""
    
    # Conventional Commits types
    CONVENTIONAL_TYPES = [
        'feat', 'fix', 'docs', 'style', 'refactor', 'perf', 
        'test', 'build', 'ci', 'chore', 'revert'
    ]
    
    def __init__(self, logger: Logger):
        """
        Initialize commit message generator.
        
        Args:
            logger: Logger instance.
        """
        self.logger = logger
    
    def generate_commit_message(
        self,
        analysis: ChangeAnalysis,
        custom_message: Optional[str] = None,
        custom_type: Optional[str] = None
    ) -> str:
        """
        Generate a Conventional Commits message.
        
        Args:
            analysis: ChangeAnalysis object.
            custom_message: Optional custom message override.
            custom_type: Optional custom type override.
            
        Returns:
            Generated commit message.
        """
        if custom_message:
            return self._format_conventional_commit(
                custom_type or analysis.likely_type,
                custom_message
            )
        
        self.logger.step("Генерация сообщения коммита")
        
        # Determine the type
        commit_type = custom_type if custom_type else analysis.likely_type
        
        # Generate the description
        description = self._generate_description(analysis)
        
        # Format as conventional commit
        message = self._format_conventional_commit(commit_type, description)
        
        self.logger.info(f"Generated commit message: {message}")
        return message
    
    def _generate_description(self, analysis: ChangeAnalysis) -> str:
        """
        Generate a description for the commit message.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            Description string.
        """
        # Extract keywords from analysis
        keywords = self._extract_keywords(analysis)
        
        if keywords:
            # Use the most relevant keyword
            main_keyword = keywords[0]
            
            # Generate description based on change type and keyword
            description = self._build_description(analysis.likely_type, main_keyword, analysis)
        else:
            # Fallback to generic description
            description = self._get_generic_description(analysis)
        
        # Ensure description is in Russian and meaningful
        description = self._translate_to_russian(description, analysis)
        
        # Ensure it's not too long
        if len(description) > 50:
            description = description[:50]
        
        return description
    
    def _extract_keywords(self, analysis: ChangeAnalysis) -> list:
        """
        Extract relevant keywords from analysis.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            List of keywords.
        """
        keywords = []
        
        # Extract from directories
        for directory in analysis.directories.keys():
            dir_parts = directory.split('/')
            for part in dir_parts:
                if len(part) > 2 and part not in keywords:
                    keywords.append(part)
        
        # Extract from file types
        for ext in analysis.file_types.keys():
            if ext not in keywords:
                keywords.append(ext)
        
        # Extract from diff summary
        diff_lower = analysis.diff_summary.lower()
        common_keywords = [
            'import', 'class', 'function', 'test', 'fix', 'bug', 'error',
            'exception', 'auth', 'login', 'user', 'api', 'endpoint',
            'route', 'model', 'schema', 'database', 'query', 'docker',
            'deploy', 'config', 'dependency', 'version', 'documentation',
            'migration', 'refactor', 'optimize', 'performance', 'security'
        ]
        
        for keyword in common_keywords:
            if keyword in diff_lower and keyword not in keywords:
                keywords.append(keyword)
        
        return keywords[:5]  # Limit to top 5 keywords
    
    def _build_description(self, change_type: str, keyword: str, analysis: ChangeAnalysis) -> str:
        """
        Build description based on change type and keyword.
        
        Args:
            change_type: Type of change.
            keyword: Main keyword.
            analysis: ChangeAnalysis object.
            
        Returns:
            Description string.
        """
        type_templates = {
            'feat': f'add {keyword}',
            'fix': f'fix {keyword}',
            'refactor': f'refactor {keyword}',
            'chore': f'update {keyword}',
            'docs': f'document {keyword}',
            'style': f'format {keyword}',
            'test': f'test {keyword}',
            'perf': f'optimize {keyword}',
            'build': f'build {keyword}',
            'ci': f'ci {keyword}',
        }
        
        if change_type in type_templates:
            return type_templates[change_type]
        
        return f'update {keyword}'
    
    def _translate_to_russian(self, description: str, analysis: ChangeAnalysis) -> str:
        """
        Keep description in English (industry standard for Conventional Commits).
        
        Args:
            description: English description.
            analysis: ChangeAnalysis object.
            
        Returns:
            English description (unchanged).
        """
        # Keep English as industry standard
        return description
    
    def _get_generic_description(self, analysis: ChangeAnalysis) -> str:
        """
        Get a generic description when no specific keywords are found.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            Generic description string (English).
        """
        type_descriptions = {
            'feat': 'add feature',
            'fix': 'fix bug',
            'refactor': 'refactor code',
            'chore': 'update dependencies',
            'docs': 'update documentation',
            'style': 'format code',
            'test': 'add tests',
            'perf': 'optimize performance',
            'build': 'update build',
            'ci': 'update ci/cd',
        }
        
        return type_descriptions.get(analysis.likely_type, 'update code')
    
    def _format_conventional_commit(self, commit_type: str, description: str) -> str:
        """
        Format message as Conventional Commit.
        
        Args:
            commit_type: Type of commit.
            description: Description of changes.
            
        Returns:
            Formatted commit message.
        """
        # Ensure type is valid
        if commit_type not in self.CONVENTIONAL_TYPES:
            commit_type = 'chore'
        
        # Format: type: description
        message = f"{commit_type}: {description}"
        
        # Limit to 72 characters (Git standard)
        if len(message) > 72:
            # Truncate description to fit
            max_desc_length = 72 - len(commit_type) - 2  # -2 for ": "
            description = description[:max_desc_length]
            message = f"{commit_type}: {description}"
        
        return message
    
    def validate_commit_message(self, message: str) -> bool:
        """
        Validate that a message follows Conventional Commits.
        
        Args:
            message: Commit message to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        # Check for conventional commits format
        pattern = r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .{1,72}$'
        return bool(re.match(pattern, message))
