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
        
        # Determine the type prefix
        change_type = analysis.likely_type
        
        # Generate the descriptive part
        description = self._generate_description(analysis)
        
        # Combine type and description with colon (no space after colon for Git compatibility)
        branch_name = f"{change_type}:{description}"
        
        # Sanitize the branch name
        branch_name = self._sanitize_branch_name(branch_name)
        
        self.logger.info(f"Generated branch name: {branch_name}")
        return branch_name
    
    def _generate_description(self, analysis: ChangeAnalysis) -> str:
        """
        Generate a descriptive part of the branch name.
        
        Rules:
        - Max 3 words
        - kebab-case
        - Max ~35 chars (to fit in 40 total with type/)
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            Description string.
        """
        # Extract keywords from affected directories
        directory_keywords = self._extract_directory_keywords(analysis.directories)
        
        # Extract keywords from file types
        file_type_keywords = self._extract_file_type_keywords(analysis.file_types)
        
        # Extract keywords from diff patterns
        diff_keywords = self._extract_diff_keywords(analysis.diff_summary)
        
        # Combine and prioritize keywords
        all_keywords = directory_keywords + file_type_keywords + diff_keywords
        
        if all_keywords:
            # Use the most relevant keyword(s) - max 3 words, kebab-case
            words = all_keywords[:3]  # Max 3 words
            description = '-'.join(words)  # kebab-case
        else:
            # Fallback to generic description
            description = self._get_generic_description(analysis)
        
        # Ensure description is not too long (max ~35 chars to fit in 40 total with type/)
        if len(description) > 35:
            description = description[:35]
        
        return description
    
    def _extract_directory_keywords(self, directories: dict) -> List[str]:
        """
        Extract meaningful keywords from directory paths.
        
        Args:
            directories: Dictionary of directory -> count.
            
        Returns:
            List of keywords.
        """
        keywords = []
        
        # Common meaningful directory names
        meaningful_dirs = {
            'app': 'app',
            'api': 'api',
            'auth': 'auth',
            'user': 'user',
            'admin': 'admin',
            'models': 'models',
            'schemas': 'schemas',
            'services': 'services',
            'controllers': 'controllers',
            'views': 'views',
            'templates': 'templates',
            'static': 'static',
            'tests': 'tests',
            'migrations': 'migrations',
            'scripts': 'scripts',
            'docs': 'docs',
            'config': 'config',
            'utils': 'utils',
            'helpers': 'helpers',
            'middleware': 'middleware',
            'routes': 'routes',
            'handlers': 'handlers',
            'database': 'database',
            'db': 'database',
            'docker': 'docker',
            'deploy': 'deploy',
            'ci': 'ci',
            'github': 'github',
            'frontend': 'frontend',
            'backend': 'backend',
            'client': 'client',
            'server': 'server',
        }
        
        for directory in directories.keys():
            dir_parts = directory.split('/')
            for part in dir_parts:
                if part.lower() in meaningful_dirs:
                    keyword = meaningful_dirs[part.lower()]
                    if keyword not in keywords:
                        keywords.append(keyword)
        
        return keywords
    
    def _extract_file_type_keywords(self, file_types: dict) -> List[str]:
        """
        Extract keywords from file types.
        
        Args:
            file_types: Dictionary of file extension -> count.
            
        Returns:
            List of keywords.
        """
        keywords = []
        
        # Map file extensions to keywords
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'react',
            '.jsx': 'react',
            '.vue': 'vue',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.kt': 'kotlin',
            '.swift': 'swift',
            '.sql': 'sql',
            '.sh': 'shell',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.md': 'markdown',
            '.txt': 'text',
            '.dockerfile': 'docker',
            'dockerfile': 'docker',
        }
        
        for ext in file_types.keys():
            ext_lower = ext.lower()
            if ext_lower in extension_map:
                keyword = extension_map[ext_lower]
                if keyword not in keywords:
                    keywords.append(keyword)
        
        return keywords
    
    def _extract_diff_keywords(self, diff_summary: str) -> List[str]:
        """
        Extract keywords from diff summary.
        
        Args:
            diff_summary: Diff summary string.
            
        Returns:
            List of keywords.
        """
        keywords = []
        
        # Common patterns to look for
        patterns = {
            'import': 'imports',
            'class': 'class',
            'function': 'function',
            'test': 'test',
            'fix': 'fix',
            'bug': 'bug',
            'error': 'error',
            'exception': 'exception',
            'auth': 'auth',
            'login': 'login',
            'user': 'user',
            'api': 'api',
            'endpoint': 'endpoint',
            'route': 'route',
            'model': 'model',
            'schema': 'schema',
            'database': 'database',
            'query': 'query',
            'docker': 'docker',
            'deploy': 'deploy',
            'config': 'config',
            'dependency': 'dependency',
            'version': 'version',
            'documentation': 'docs',
            'readme': 'readme',
            'migration': 'migration',
            'refactor': 'refactor',
            'optimize': 'optimize',
            'performance': 'performance',
            'security': 'security',
            'session': 'session',
            'cache': 'cache',
            'validation': 'validation',
            'pagination': 'pagination',
            'filter': 'filter',
            'search': 'search',
            'upload': 'upload',
            'export': 'export',
            'import': 'import',
            'notification': 'notification',
            'email': 'email',
            'payment': 'payment',
            'order': 'order',
            'product': 'product',
            'cart': 'cart',
            'checkout': 'checkout',
        }
        
        diff_lower = diff_summary.lower()
        
        for pattern, keyword in patterns.items():
            if pattern in diff_lower:
                if keyword not in keywords:
                    keywords.append(keyword)
        
        return keywords
    
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
        
        # Replace spaces and underscores with hyphens, but preserve colon spacing
        # First replace colon + space with colon to avoid double hyphens
        name = re.sub(r':\s+', ':', name)
        
        # Then replace remaining spaces and underscores with hyphens
        name = re.sub(r'[\s_]+', '-', name)
        
        # Remove special characters except hyphens and colons
        name = re.sub(r'[^a-z0-9-:]', '', name)
        
        # Remove consecutive hyphens (but preserve colon)
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
        
        Args:
            name: Branch name to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        # Check for empty name
        if not name:
            return False
        
        # Check for invalid characters
        if re.search(r'[^a-z0-9-]', name):
            return False
        
        # Check for consecutive hyphens
        if '--' in name:
            return False
        
        # Check for leading/trailing hyphens
        if name.startswith('-') or name.endswith('-'):
            return False
        
        # Check for reserved names
        reserved_names = ['head', 'main', 'master', 'develop']
        if name in reserved_names:
            return False
        
        return True
