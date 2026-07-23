#!/usr/bin/env python3
"""
Change analyzer module for Git automation script.
Analyzes git diff to determine the nature of changes.
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from pathlib import Path

from .logger import Logger
from .git_operations import GitOperations, FileChange


@dataclass
class DiffAnalysis:
    """Represents analysis of diff content."""
    line_count: int
    word_count: int
    has_imports: bool
    has_function_def: bool
    has_class_def: bool
    has_test_code: bool


@dataclass
class ChangeAnalysis:
    """Represents analysis of changes."""
    added_files: List[str]
    modified_files: List[str]
    deleted_files: List[str]
    renamed_files: List[str]
    file_types: Dict[str, int]  # Extension -> count
    directories: Dict[str, int]  # Directory -> count
    diff_summary: str
    likely_type: str  # feat, fix, refactor, chore, docs, etc.


class ChangeAnalyzer:
    """Analyzes changes to determine their nature."""
    
    def __init__(self, git_ops: GitOperations, logger: Logger):
        """
        Initialize change analyzer.
        
        Args:
            git_ops: GitOperations instance.
            logger: Logger instance.
        """
        self.git_ops = git_ops
        self.logger = logger
    
    def analyze_changes(self) -> ChangeAnalysis:
        """
        Analyze current changes.
        
        Returns:
            ChangeAnalysis object with detailed analysis.
        """
        self.logger.step("Анализ изменений")
        
        # Get changed files
        changed_files = self.git_ops.get_changed_files()
        
        # Categorize files
        added_files = []
        modified_files = []
        deleted_files = []
        renamed_files = []
        file_types = {}
        directories = {}
        
        for change in changed_files:
            file_path = Path(change.path)
            
            # Track file types
            if file_path.suffix:
                file_types[file_path.suffix] = file_types.get(file_path.suffix, 0) + 1
            
            # Track directories
            if file_path.parent != Path('.'):
                dir_name = str(file_path.parent)
                directories[dir_name] = directories.get(dir_name, 0) + 1
            
            # Categorize by status
            if change.status == 'added':
                added_files.append(change.path)
            elif change.status == 'modified':
                modified_files.append(change.path)
            elif change.status == 'deleted':
                deleted_files.append(change.path)
            elif change.status == 'renamed':
                renamed_files.append(change.path)
        
        # Get diff summary
        diff = self.git_ops.get_diff()
        diff_summary = self._summarize_diff(diff)
        
        # Determine likely change type
        likely_type = self._determine_change_type(
            added_files, modified_files, deleted_files, diff, file_types, directories
        )
        
        analysis = ChangeAnalysis(
            added_files=added_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            renamed_files=renamed_files,
            file_types=file_types,
            directories=directories,
            diff_summary=diff_summary,
            likely_type=likely_type
        )
        
        self._log_analysis(analysis)
        return analysis
    
    def _summarize_diff(self, diff: str) -> str:
        """
        Create a summary of the diff.
        
        Args:
            diff: Git diff output.
            
        Returns:
            Summary string.
        """
        lines = diff.split('\n')
        
        # Count additions and deletions
        additions = 0
        deletions = 0
        
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1
        
        # Extract key patterns
        patterns = self._extract_patterns(diff)
        
        return f"+{additions} -{deletions} lines. Patterns: {', '.join(patterns) if patterns else 'none'}"
    
    def _extract_patterns(self, diff: str) -> List[str]:
        """
        Extract common patterns from diff.
        
        Args:
            diff: Git diff output.
            
        Returns:
            List of detected patterns.
        """
        patterns = []
        
        # Common patterns to look for
        pattern_keywords = {
            'import': 'imports',
            'class': 'classes',
            'def ': 'functions',
            'async def': 'async functions',
            'test': 'tests',
            'fix': 'fixes',
            'bug': 'bug fixes',
            'error': 'error handling',
            'exception': 'exceptions',
            'TODO': 'todos',
            'FIXME': 'fixmes',
            'deprecated': 'deprecations',
            'migration': 'migration',
            'refactor': 'refactoring',
            'optimize': 'optimization',
            'performance': 'performance',
            'security': 'security',
            'auth': 'authentication',
            'login': 'login',
            'user': 'user-related',
            'api': 'api',
            'endpoint': 'endpoints',
            'route': 'routes',
            'model': 'models',
            'schema': 'schemas',
            'database': 'database',
            'db': 'database',
            'sql': 'sql',
            'query': 'queries',
            'docker': 'docker',
            'deploy': 'deployment',
            'ci': 'ci/cd',
            'workflow': 'workflows',
            'config': 'configuration',
            'env': 'environment',
            'dependency': 'dependencies',
            'requirement': 'requirements',
            'package': 'packages',
            'version': 'version',
            'update': 'updates',
            'upgrade': 'upgrades',
            'documentation': 'documentation',
            'readme': 'readme',
            'doc': 'docs',
            'comment': 'comments',
        }
        
        diff_lower = diff.lower()
        
        for keyword, pattern in pattern_keywords.items():
            if keyword in diff_lower:
                patterns.append(pattern)
        
        return patterns
    
    def _determine_change_type(
        self,
        added_files: List[str],
        modified_files: List[str],
        deleted_files: List[str],
        diff: str,
        file_types: Dict[str, int],
        directories: Dict[str, int]
    ) -> str:
        """
        Determine the likely type of change based on heuristics.
        
        Args:
            added_files: List of added files.
            modified_files: List of modified files.
            deleted_files: List of deleted files.
            diff: Git diff output.
            file_types: Dictionary of file types.
            directories: Dictionary of affected directories.
            
        Returns:
            Change type (feat, fix, refactor, chore, docs, etc.).
        """
        diff_lower = diff.lower()
        
        # Analyze diff content beyond file names
        diff_analysis = self._analyze_diff_content(diff)
        
        # Check for documentation changes based on content
        if any(ext in file_types for ext in ['.md', '.rst', '.txt']):
            # Check if it's a typo fix vs substantial documentation
            if diff_analysis.line_count < 5 and diff_analysis.word_count < 20:
                # Small change - likely typo fix
                return 'style'
            elif any('readme' in f.lower() or 'doc' in f.lower() for f in added_files + modified_files):
                return 'docs'
        
        # Check for test changes
        if any('test' in f.lower() for f in added_files + modified_files):
            return 'test'
        
        # Check for CI/CD changes
        if any('.github' in d or '.gitlab-ci' in d or 'ci' in d for d in directories):
            return 'ci'
        
        # Check for build/dependency changes
        if any('requirements' in f or 'package' in f or 'setup.py' in f or 'pyproject' in f 
               for f in added_files + modified_files):
            return 'build'
        
        # Check for configuration changes
        if any('config' in f or '.env' in f or 'settings' in f for f in added_files + modified_files):
            return 'chore'
        
        # Check for fix patterns in diff content
        fix_keywords = ['fix', 'bug', 'error', 'exception', 'issue', 'patch', 'resolve', 'correct']
        if any(keyword in diff_lower for keyword in fix_keywords):
            return 'fix'
        
        # Check for refactor patterns
        refactor_keywords = ['refactor', 'rework', 'rewrite', 'simplify', 'clean', 'extract', 'consolidate']
        if any(keyword in diff_lower for keyword in refactor_keywords):
            return 'refactor'
        
        # Check for performance
        if 'performance' in diff_lower or 'optimize' in diff_lower or 'cache' in diff_lower:
            return 'perf'
        
        # Check for style changes (formatting, linting)
        if 'style' in diff_lower or 'format' in diff_lower or 'lint' in diff_lower or 'black' in diff_lower:
            return 'style'
        
        # Check for chore/maintenance
        chore_keywords = ['update', 'upgrade', 'version', 'dependency', 'migrate', 'cleanup', 'remove']
        if any(keyword in diff_lower for keyword in chore_keywords):
            return 'chore'
        
        # Check for feature patterns
        feat_keywords = ['add', 'implement', 'create', 'new', 'support', 'enable']
        if any(keyword in diff_lower for keyword in feat_keywords):
            return 'feat'
        
        # Default to feat if adding new files
        if added_files and not deleted_files:
            return 'feat'
        
        # Default to refactor for modifications
        if modified_files:
            return 'refactor'
        
        # Default fallback
        return 'chore'
    
    def _analyze_diff_content(self, diff: str) -> 'DiffAnalysis':
        """
        Analyze diff content beyond file names.
        
        Args:
            diff: Git diff output.
            
        Returns:
            DiffAnalysis object with content metrics.
        """
        lines = diff.split('\n')
        
        # Count actual code changes (excluding diff metadata)
        code_lines = [line for line in lines if line.startswith('+') or line.startswith('-')]
        code_lines = [line for line in code_lines if not line.startswith('+++') and not line.startswith('---')]
        
        # Count words in changes
        word_count = sum(len(line.split()) for line in code_lines)
        
        # Check for specific patterns
        has_imports = any('import' in line.lower() for line in code_lines)
        has_function_def = any('def ' in line for line in code_lines)
        has_class_def = any('class ' in line for line in code_lines)
        has_test_code = any('test' in line.lower() or 'assert' in line.lower() for line in code_lines)
        
        return DiffAnalysis(
            line_count=len(code_lines),
            word_count=word_count,
            has_imports=has_imports,
            has_function_def=has_function_def,
            has_class_def=has_class_def,
            has_test_code=has_test_code
        )
    
    def _log_analysis(self, analysis: ChangeAnalysis) -> None:
        """Log the analysis results."""
        self.logger.info(f"Added files: {len(analysis.added_files)}")
        self.logger.info(f"Modified files: {len(analysis.modified_files)}")
        self.logger.info(f"Deleted files: {len(analysis.deleted_files)}")
        self.logger.info(f"Renamed files: {len(analysis.renamed_files)}")
        self.logger.info(f"File types: {dict(analysis.file_types)}")
        self.logger.info(f"Affected directories: {len(analysis.directories)}")
        self.logger.info(f"Diff summary: {analysis.diff_summary}")
        self.logger.info(f"Likely change type: {analysis.likely_type}")
    
    def get_change_description(self, analysis: ChangeAnalysis) -> str:
        """
        Generate a human-readable description of changes.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            Description string.
        """
        parts = []
        
        if analysis.added_files:
            parts.append(f"{len(analysis.added_files)} new file(s)")
        if analysis.modified_files:
            parts.append(f"{len(analysis.modified_files)} modified file(s)")
        if analysis.deleted_files:
            parts.append(f"{len(analysis.deleted_files)} deleted file(s)")
        if analysis.renamed_files:
            parts.append(f"{len(analysis.renamed_files)} renamed file(s)")
        
        if not parts:
            return "No changes detected"
        
        description = ", ".join(parts)
        
        # Add file type information
        if analysis.file_types:
            top_types = sorted(analysis.file_types.items(), key=lambda x: x[1], reverse=True)[:3]
            types_str = ", ".join([f"{ext} ({count})" for ext, count in top_types])
            description += f" [{types_str}]"
        
        return description
