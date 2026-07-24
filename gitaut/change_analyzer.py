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
    additions: int
    deletions: int
    changed_files: int
    complexity_score: float
    has_imports: bool
    has_function_def: bool
    has_class_def: bool
    has_test_code: bool
    added_function_def: bool
    removed_function_def: bool
    added_class_def: bool
    removed_class_def: bool


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
        self.MAX_DIFF_SIZE = 5 * 1024 * 1024  # 5MB limit
    
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
        
        # Get diff summary with size limit protection
        diff = self.git_ops.get_diff()
        if len(diff.encode('utf-8')) > self.MAX_DIFF_SIZE:
            self.logger.warning(f"Diff size ({len(diff.encode('utf-8')) / 1024 / 1024:.2f}MB) exceeds limit ({self.MAX_DIFF_SIZE / 1024 / 1024}MB). Using simplified analysis.")
            diff = diff[:self.MAX_DIFF_SIZE]  # Truncate for safety
        diff_summary = self._summarize_diff(diff)
        
        # Determine likely change type with enhanced analysis
        diff_analysis = self._analyze_diff_content(diff)
        likely_type = self._determine_change_type(
            added_files, modified_files, deleted_files, renamed_files, diff, file_types, directories, diff_analysis
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
        Extract common patterns from diff using regex to avoid false matches.
        
        Args:
            diff: Git diff output.
            
        Returns:
            List of detected patterns.
        """
        patterns = []
        
        # Common patterns with word boundary regex to avoid false matches
        pattern_keywords = {
            r'\bimport\b': 'imports',
            r'\bclass\b': 'classes',
            r'\bdef\s': 'functions',
            r'\basync def\b': 'async functions',
            r'\btest\b': 'tests',
            r'\bfix\b': 'fixes',
            r'\bbug\b': 'bug fixes',
            r'\berror\b': 'error handling',
            r'\bexception\b': 'exceptions',
            r'\bTODO\b': 'todos',
            r'\bFIXME\b': 'fixmes',
            r'\bdeprecated\b': 'deprecations',
            r'\bmigration\b': 'migration',
            r'\brefactor\b': 'refactoring',
            r'\boptimize\b': 'optimization',
            r'\bperformance\b': 'performance',
            r'\bsecurity\b': 'security',
            r'\bauth\b': 'authentication',
            r'\blogin\b': 'login',
            r'\buser\b': 'user-related',
            r'\bapi\b': 'api',
            r'\bendpoint\b': 'endpoints',
            r'\broute\b': 'routes',
            r'\bmodel\b': 'models',
            r'\bschema\b': 'schemas',
            r'\bdatabase\b': 'database',
            r'\bdb\b': 'database',
            r'\bsql\b': 'sql',
            r'\bquery\b': 'queries',
            r'\bdocker\b': 'docker',
            r'\bdeploy\b': 'deployment',
            r'\bci\b': 'ci/cd',
            r'\bworkflow\b': 'workflows',
            r'\bconfig\b': 'configuration',
            r'\benv\b': 'environment',
            r'\bdependency\b': 'dependencies',
            r'\brequirement\b': 'requirements',
            r'\bpackage\b': 'packages',
            r'\bversion\b': 'version',
            r'\bupdate\b': 'updates',
            r'\bupgrade\b': 'upgrades',
            r'\bdocumentation\b': 'documentation',
            r'\breadme\b': 'readme',
            r'\bdoc\b': 'docs',
            r'\bcomment\b': 'comments',
        }
        
        diff_lower = diff.lower()
        
        for pattern, label in pattern_keywords.items():
            if re.search(pattern, diff_lower):
                patterns.append(label)
        
        return patterns
    
    def _determine_change_type(
        self,
        added_files: List[str],
        modified_files: List[str],
        deleted_files: List[str],
        renamed_files: List[str],
        diff: str,
        file_types: Dict[str, int],
        directories: Dict[str, int],
        diff_analysis: 'DiffAnalysis'
    ) -> str:
        """
        Determine the likely type of change using a scoring system.
        
        Args:
            added_files: List of added files.
            modified_files: List of modified files.
            deleted_files: List of deleted files.
            renamed_files: List of renamed files.
            diff: Git diff output.
            file_types: Dictionary of file types.
            directories: Dictionary of affected directories.
            diff_analysis: DiffAnalysis object with content metrics.
            
        Returns:
            Change type (feat, fix, refactor, chore, docs, etc.).
        """
        diff_lower = diff.lower()
        
        # Initialize scores for each change type
        scores = {
            'feat': 0,
            'fix': 0,
            'refactor': 0,
            'chore': 0,
            'docs': 0,
            'test': 0,
            'ci': 0,
            'build': 0,
            'perf': 0,
            'style': 0,
        }
        
        # Score based on file operations
        if added_files and not modified_files and not deleted_files:
            scores['feat'] += 5
        elif deleted_files and not added_files and not modified_files:
            scores['refactor'] += 3
        elif renamed_files:
            scores['refactor'] += 4  # Rename is almost always refactor
        
        # Score based on file types
        if any(ext in file_types for ext in ['.md', '.rst', '.txt']):
            if diff_analysis.line_count < 5 and diff_analysis.word_count < 20:
                scores['style'] += 3
            else:
                scores['docs'] += 4
        
        if any('test' in f.lower() for f in added_files + modified_files):
            scores['test'] += 5
        
        if any('.github' in d or '.gitlab-ci' in d or 'ci' in d for d in directories):
            scores['ci'] += 5
        
        if any('requirements' in f or 'package' in f or 'setup.py' in f or 'pyproject' in f 
               for f in added_files + modified_files):
            scores['build'] += 4
        
        if any('config' in f or '.env' in f or 'settings' in f for f in added_files + modified_files):
            scores['chore'] += 3
        
        # Score based on diff content patterns (using regex for accuracy)
        fix_keywords = [r'\bfix\b', r'\bbug\b', r'\berror\b', r'\bexception\b', r'\bissue\b', r'\bpatch\b', r'\bresolve\b', r'\bcorrect\b']
        for keyword in fix_keywords:
            if re.search(keyword, diff_lower):
                scores['fix'] += 5
                break
        
        refactor_keywords = [r'\brefactor\b', r'\brework\b', r'\brewrite\b', r'\bsimplify\b', r'\bclean\b', r'\bextract\b', r'\bconsolidate\b']
        for keyword in refactor_keywords:
            if re.search(keyword, diff_lower):
                scores['refactor'] += 4
                break
        
        if re.search(r'\bperformance\b', diff_lower) or re.search(r'\boptimize\b', diff_lower) or re.search(r'\bcache\b', diff_lower):
            scores['perf'] += 4
        
        if re.search(r'\bstyle\b', diff_lower) or re.search(r'\bformat\b', diff_lower) or re.search(r'\blint\b', diff_lower) or re.search(r'\bblack\b', diff_lower):
            scores['style'] += 3
        
        chore_keywords = [r'\bupdate\b', r'\bupgrade\b', r'\bversion\b', r'\bdependency\b', r'\bmigrate\b', r'\bcleanup\b', r'\bremove\b']
        for keyword in chore_keywords:
            if re.search(keyword, diff_lower):
                scores['chore'] += 2
                break
        
        feat_keywords = [r'\badd\b', r'\bimplement\b', r'\bcreate\b', r'\bnew\b', r'\bsupport\b', r'\benable\b']
        for keyword in feat_keywords:
            if re.search(keyword, diff_lower):
                scores['feat'] += 3
                break
        
        # Score based on diff analysis (added vs removed)
        if diff_analysis.added_function_def and not diff_analysis.removed_function_def:
            scores['feat'] += 3
        elif diff_analysis.removed_function_def:
            scores['refactor'] += 2
        
        if diff_analysis.added_class_def and not diff_analysis.removed_class_def:
            scores['feat'] += 2
        elif diff_analysis.removed_class_def:
            scores['refactor'] += 2
        
        # Score based on complexity/scale
        if diff_analysis.complexity_score > 0.8:
            scores['refactor'] += 2  # Large changes are often refactors
        elif diff_analysis.complexity_score < 0.1:
            scores['style'] += 1  # Small changes are often style
        
        # Find the type with the highest score
        max_score = max(scores.values())
        if max_score == 0:
            return 'chore'  # Default fallback
        
        # Get all types with the max score (for tie-breaking)
        max_types = [t for t, s in scores.items() if s == max_score]
        
        # Tie-breaking: prefer more specific types
        priority_order = ['fix', 'feat', 'test', 'ci', 'build', 'docs', 'perf', 'refactor', 'style', 'chore']
        for t in priority_order:
            if t in max_types:
                return t
        
        return max_types[0]  # Fallback to first max
    
    def _analyze_diff_content(self, diff: str) -> 'DiffAnalysis':
        """
        Analyze diff content beyond file names with enhanced metrics.
        
        Args:
            diff: Git diff output.
            
        Returns:
            DiffAnalysis object with content metrics.
        """
        lines = diff.split('\n')
        
        # Separate added and removed lines
        added_lines = []
        removed_lines = []
        
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line)
            elif line.startswith('-') and not line.startswith('---'):
                removed_lines.append(line)
        
        code_lines = added_lines + removed_lines
        
        # Count words in changes
        word_count = sum(len(line.split()) for line in code_lines)
        
        # Check for specific patterns in added vs removed lines
        has_imports = any('import' in line.lower() for line in added_lines)
        
        # Check for function/class definitions separately for added vs removed
        added_function_def = any('def ' in line for line in added_lines)
        removed_function_def = any('def ' in line for line in removed_lines)
        has_function_def = added_function_def or removed_function_def
        
        added_class_def = any('class ' in line for line in added_lines)
        removed_class_def = any('class ' in line for line in removed_lines)
        has_class_def = added_class_def or removed_class_def
        
        has_test_code = any('test' in line.lower() or 'assert' in line.lower() for line in code_lines)
        
        # Calculate complexity score based on scale of changes
        total_files = len(added_lines) + len(removed_lines)
        if total_files == 0:
            complexity_score = 0.0
        else:
            # Complexity based on ratio of additions to total changes
            # More additions = higher complexity (new code)
            # More deletions = lower complexity (removal)
            addition_ratio = len(added_lines) / total_files
            complexity_score = addition_ratio
        
        return DiffAnalysis(
            line_count=len(code_lines),
            word_count=word_count,
            additions=len(added_lines),
            deletions=len(removed_lines),
            changed_files=len(set(lines)),
            complexity_score=complexity_score,
            has_imports=has_imports,
            has_function_def=has_function_def,
            has_class_def=has_class_def,
            has_test_code=has_test_code,
            added_function_def=added_function_def,
            removed_function_def=removed_function_def,
            added_class_def=added_class_def,
            removed_class_def=removed_class_def
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
