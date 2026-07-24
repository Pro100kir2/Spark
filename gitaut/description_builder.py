#!/usr/bin/env python3
"""
Description builder module for Git automation script.
Builds human-readable descriptions from change intent.
"""

import re
from typing import Optional, List
from dataclasses import dataclass

from .logger import Logger
from .change_analyzer import ChangeAnalysis
from .change_classifier import ChangeIntent


class DescriptionBuilder:
    """Builds human-readable descriptions from change intent."""
    
    def __init__(self, logger: Logger):
        """
        Initialize description builder.
        
        Args:
            logger: Logger instance.
        """
        self.logger = logger
    
    def build_description(self, intent: ChangeIntent, analysis: Optional[ChangeAnalysis] = None) -> str:
        """
        Build description from ChangeIntent.
        
        Args:
            intent: ChangeIntent object.
            analysis: Optional ChangeAnalysis for fallback.
            
        Returns:
            Description string.
        """
        # Use semantic target instead of random keywords
        if intent.target:
            target = intent.target.replace('-', ' ')
            description = f"{intent.action} {target}"
        else:
            # Fallback to action only
            description = intent.action
        
        # Smart truncation - don't break words
        description = self._smart_truncate(description, max_length=50)
        
        return description
    
    def build_description_from_analysis(self, analysis: ChangeAnalysis) -> str:
        """
        Build description from ChangeAnalysis (legacy fallback).
        
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
        
        # Smart truncation - don't break words
        description = self._smart_truncate(description, max_length=50)
        
        return description
    
    def _extract_keywords(self, analysis: ChangeAnalysis) -> List[str]:
        """
        Extract relevant keywords from analysis using regex for accuracy.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            List of keywords.
        """
        keywords = []
        
        # Extract from file names (more specific than directories)
        all_files = analysis.added_files + analysis.modified_files + analysis.deleted_files
        
        # Common entity keywords in file names
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
                if re.search(rf'\b{keyword}\b', file_name) and keyword not in keywords:
                    keywords.append(keyword)
        
        # Extract from diff summary with regex
        diff_lower = analysis.diff_summary.lower()
        common_keywords = [
            'import', 'class', 'function', 'test', 'fix', 'bug', 'error',
            'exception', 'auth', 'login', 'user', 'api', 'endpoint',
            'route', 'model', 'schema', 'database', 'query', 'docker',
            'deploy', 'config', 'dependency', 'version', 'documentation',
            'migration', 'refactor', 'optimize', 'performance', 'security'
        ]
        
        for keyword in common_keywords:
            if re.search(rf'\b{keyword}\b', diff_lower) and keyword not in keywords:
                keywords.append(keyword)
        
        return keywords[:5]  # Limit to top 5 keywords
    
    def _build_description(self, change_type: str, keyword: str, analysis: ChangeAnalysis) -> str:
        """
        Build description based on change type and keyword with better templates.
        
        Args:
            change_type: Type of change.
            keyword: Main keyword.
            analysis: ChangeAnalysis object.
            
        Returns:
            Description string.
        """
        # More descriptive templates based on context
        type_templates = {
            'feat': [
                f'add {keyword}',
                f'implement {keyword}',
                f'create {keyword}',
                f'enable {keyword}',
            ],
            'fix': [
                f'fix {keyword}',
                f'resolve {keyword} issue',
                f'correct {keyword}',
                f'patch {keyword}',
            ],
            'refactor': [
                f'refactor {keyword}',
                f'rework {keyword}',
                f'simplify {keyword}',
                f'clean up {keyword}',
            ],
            'chore': [
                f'update {keyword}',
                f'maintain {keyword}',
                f'upgrade {keyword}',
            ],
            'docs': [
                f'document {keyword}',
                f'update {keyword} docs',
                f'add {keyword} documentation',
            ],
            'style': [
                f'format {keyword}',
                f'lint {keyword}',
                f'style {keyword}',
            ],
            'test': [
                f'test {keyword}',
                f'add {keyword} tests',
                f'fix {keyword} tests',
            ],
            'perf': [
                f'optimize {keyword}',
                f'improve {keyword} performance',
                f'cache {keyword}',
            ],
            'build': [
                f'build {keyword}',
                f'update {keyword} build',
                f'configure {keyword}',
            ],
            'ci': [
                f'ci {keyword}',
                f'update {keyword} ci',
                f'automate {keyword}',
            ],
        }
        
        if change_type in type_templates:
            templates = type_templates[change_type]
            # Choose template based on analysis context
            if analysis.added_files and not analysis.modified_files:
                return templates[0]  # First template (add/implement)
            elif analysis.deleted_files:
                return templates[-1]  # Last template (remove/clean)
            else:
                return templates[1] if len(templates) > 1 else templates[0]
        
        return f'update {keyword}'
    
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
        
        # Find the last space before max_length
        last_space = text.rfind(' ', 0, max_length)
        if last_space > 0:
            return text[:last_space]
        
        # If no space, just truncate
        return text[:max_length]
