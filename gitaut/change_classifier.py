#!/usr/bin/env python3
"""
Change classifier module for Git automation script.
Determines semantic change intent from raw change data.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass

from .logger import Logger


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
class ChangeIntent:
    """Semantic representation of change intent - single source of truth for all generators."""
    type: str  # feat, fix, refactor, chore, docs, test, ci, build, perf, style
    scope: Optional[str]  # gitaut, api, frontend, etc.
    action: str  # add, fix, refactor, update, remove, etc.
    target: str  # what was changed (primary component)
    confidence: float  # 0.0 to 1.0
    primary_component: str  # main component being changed (e.g., "commit-generator", "branch-namer")
    secondary_components: List[str]  # other affected components


class ChangeClassifier:
    """Classifies changes to determine semantic intent."""
    
    def __init__(self, logger: Logger):
        """
        Initialize change classifier.
        
        Args:
            logger: Logger instance.
        """
        self.logger = logger
    
    def classify_change(
        self,
        added_files: List[str],
        modified_files: List[str],
        deleted_files: List[str],
        renamed_files: List[str],
        diff: str,
        file_types: Dict[str, int],
        directories: Dict[str, int],
        diff_analysis: DiffAnalysis
    ) -> ChangeIntent:
        """
        Classify change to determine semantic intent.
        
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
            ChangeIntent object with semantic representation.
        """
        # Ensure diff is a string
        if not isinstance(diff, str):
            self.logger.warning(f"diff is not a string, got {type(diff)}. Converting to string.")
            diff = str(diff)
        
        diff_lower = diff.lower()
        
        # Initialize scores for each change type
        scores = self._initialize_scores()
        
        # Score based on file operations
        self._score_file_operations(scores, added_files, modified_files, deleted_files, renamed_files)
        
        # Score based on file types
        self._score_file_types(scores, file_types, added_files, modified_files, diff_analysis)
        
        # Score based on directories
        self._score_directories(scores, directories)
        
        # Score based on diff content patterns
        self._score_diff_patterns(scores, diff_lower)
        
        # Score based on diff analysis (added vs removed)
        self._score_diff_analysis(scores, diff_analysis)
        
        # Score based on complexity/scale
        self._score_complexity(scores, diff_analysis)
        
        # Determine change type from scores
        change_type, confidence = self._determine_type_from_scores(scores)
        
        # Determine scope from directories
        scope = self._determine_scope(directories)
        
        # Determine action based on type and file operations
        action = self._determine_action(change_type, added_files, modified_files, deleted_files)
        
        # Determine target (what was changed)
        target = self._determine_target(added_files, modified_files, directories, diff_lower)
        
        # Determine primary and secondary components
        primary_component, secondary_components = self._determine_components(added_files, modified_files, directories)
        
        return ChangeIntent(
            type=change_type,
            scope=scope,
            action=action,
            target=target,
            confidence=confidence,
            primary_component=primary_component,
            secondary_components=secondary_components
        )
    
    def _initialize_scores(self) -> Dict[str, int]:
        """Initialize scores for each change type."""
        return {
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
    
    def _score_file_operations(
        self,
        scores: Dict[str, int],
        added_files: List[str],
        modified_files: List[str],
        deleted_files: List[str],
        renamed_files: List[str]
    ) -> None:
        """Score based on file operations."""
        if added_files and not modified_files and not deleted_files:
            scores['feat'] += 5
        elif deleted_files and not added_files and not modified_files:
            scores['refactor'] += 3
        elif renamed_files:
            scores['refactor'] += 4  # Rename is almost always refactor
    
    def _score_file_types(
        self,
        scores: Dict[str, int],
        file_types: Dict[str, int],
        added_files: List[str],
        modified_files: List[str],
        diff_analysis: DiffAnalysis
    ) -> None:
        """Score based on file types."""
        if any(ext in file_types for ext in ['.md', '.rst', '.txt']):
            if diff_analysis.line_count < 5 and diff_analysis.word_count < 20:
                scores['style'] += 3
            else:
                scores['docs'] += 4
        
        if any('test' in f.lower() for f in added_files + modified_files):
            scores['test'] += 5
    
    def _score_directories(self, scores: Dict[str, int], directories: Dict[str, int]) -> None:
        """Score based on directories."""
        if any('.github' in d or '.gitlab-ci' in d or 'ci' in d for d in directories):
            scores['ci'] += 5
        
        if any('requirements' in f or 'package' in f or 'setup.py' in f or 'pyproject' in f 
               for f in directories.keys()):
            scores['build'] += 4
        
        if any('config' in f or '.env' in f or 'settings' in f for f in directories.keys()):
            scores['chore'] += 3
    
    def _score_diff_patterns(self, scores: Dict[str, int], diff_lower: str) -> None:
        """Score based on diff content patterns using regex."""
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
    
    def _score_diff_analysis(self, scores: Dict[str, int], diff_analysis: DiffAnalysis) -> None:
        """Score based on diff analysis (added vs removed)."""
        if diff_analysis.added_function_def and not diff_analysis.removed_function_def:
            scores['feat'] += 3
        elif diff_analysis.removed_function_def:
            scores['refactor'] += 2
        
        if diff_analysis.added_class_def and not diff_analysis.removed_class_def:
            scores['feat'] += 2
        elif diff_analysis.removed_class_def:
            scores['refactor'] += 2
    
    def _score_complexity(self, scores: Dict[str, int], diff_analysis: DiffAnalysis) -> None:
        """Score based on complexity/scale."""
        if diff_analysis.complexity_score > 0.8:
            scores['refactor'] += 2  # Large changes are often refactors
        elif diff_analysis.complexity_score < 0.1:
            scores['style'] += 1  # Small changes are often style
    
    def _determine_type_from_scores(self, scores: Dict[str, int]) -> tuple[str, float]:
        """Determine change type and confidence from scores."""
        max_score = max(scores.values())
        if max_score == 0:
            return 'chore', 0.3
        
        # Get all types with the max score (for tie-breaking)
        max_types = [t for t, s in scores.items() if s == max_score]
        
        # Tie-breaking: prefer more specific types
        priority_order = ['fix', 'feat', 'test', 'ci', 'build', 'docs', 'perf', 'refactor', 'style', 'chore']
        for t in priority_order:
            if t in max_types:
                change_type = t
                break
        else:
            change_type = max_types[0]
        
        # Calculate confidence based on score distribution
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0.3
        
        return change_type, confidence
    
    def _determine_scope(self, directories: Dict[str, int]) -> Optional[str]:
        """Determine scope from affected directories."""
        scope_mappings = {
            'gitaut': 'gitaut',
            'src': 'core',
            'api': 'api',
            'frontend': 'frontend',
            'backend': 'backend',
            'tests': 'tests',
            'config': 'config',
            'docs': 'docs',
            '.github': 'ci',
        }
        
        # Find the most common directory that maps to a scope
        dir_counts = sorted(directories.items(), key=lambda x: x[1], reverse=True)
        
        for directory, count in dir_counts:
            dir_name = directory.split('/')[-1].lower()
            if dir_name in scope_mappings:
                return scope_mappings[dir_name]
        
        # Check parent directories
        for directory, count in dir_counts:
            for scope_name, scope in scope_mappings.items():
                if scope_name in directory.lower():
                    return scope
        
        return None
    
    def _determine_action(self, change_type: str, added_files: List[str], modified_files: List[str], deleted_files: List[str]) -> str:
        """Determine action verb based on change type and file operations."""
        type_to_action = {
            'feat': 'add',
            'fix': 'fix',
            'refactor': 'refactor',
            'perf': 'optimize',
            'style': 'format',
            'test': 'test',
            'docs': 'document',
            'chore': 'update',
            'ci': 'update',
            'build': 'build',
        }
        
        action = type_to_action.get(change_type, 'update')
        
        # Override based on file operations
        if added_files and not modified_files and not deleted_files:
            action = 'add'
        elif deleted_files and not added_files and not modified_files:
            action = 'remove'
        
        return action
    
    def _determine_target(self, added_files: List[str], modified_files: List[str], directories: Dict[str, int], diff_lower: str) -> str:
        """Determine what was changed (target)."""
        all_files = added_files + modified_files
        
        # Extract target from file names (prioritize semantic terms)
        target_keywords = [
            'branch-naming', 'branch-name', 'branch',
            'change-analysis', 'change', 'analysis',
            'commit-generator', 'commit', 'generator',
            'logger', 'logging',
            'error-handler', 'error', 'handler',
            'git-operations', 'git', 'operations',
            'github-client', 'github', 'client',
            'config-loader', 'config', 'loader',
            'dependency-installer', 'dependency', 'installer',
            'input-validator', 'input', 'validator',
            'pre-commit', 'precommit', 'hooks',
        ]
        
        for file_path in all_files:
            file_name = file_path.split('/')[-1].lower()
            for keyword in target_keywords:
                if keyword in file_name:
                    return keyword.replace('-', ' ')
        
        # Extract from directories
        for directory in directories.keys():
            dir_name = directory.split('/')[-1].lower()
            for keyword in target_keywords:
                if keyword in dir_name:
                    return keyword.replace('-', ' ')
        
        # Fallback to generic
        if 'gitaut' in str(directories).lower():
            return 'gitaut'
        
        return 'code'
    
    def _determine_components(self, added_files: List[str], modified_files: List[str], directories: Dict[str, int]) -> tuple[str, List[str]]:
        """
        Determine primary and secondary components from files.
        
        Args:
            added_files: List of added files.
            modified_files: List of modified files.
            directories: Dictionary of directories.
            
        Returns:
            Tuple of (primary_component, secondary_components).
        """
        all_files = added_files + modified_files
        
        # GitAut-specific component mappings
        component_mappings = {
            'change-classifier': 'change-classifier',
            'change_classifier': 'change-classifier',
            'classifier': 'change-classifier',
            'commit-generator': 'commit-generator',
            'commit_generator': 'commit-generator',
            'generator': 'commit-generator',
            'branch-namer': 'branch-namer',
            'branch_namer': 'branch-namer',
            'namer': 'branch-namer',
            'description-builder': 'description-builder',
            'description_builder': 'description-builder',
            'builder': 'description-builder',
            'orchestrator': 'orchestrator',
            'git-operations': 'git-operations',
            'git_operations': 'git-operations',
            'github-client': 'github-client',
            'github_client': 'github-client',
            'config-loader': 'config-loader',
            'config_loader': 'config-loader',
            'dependency-installer': 'dependency-installer',
            'dependency_installer': 'dependency-installer',
            'input-validator': 'input-validator',
            'input_validator': 'input-validator',
            'error-handler': 'error-handler',
            'error_handler': 'error-handler',
            'logger': 'logger',
            'pre-commit': 'pre-commit',
            'pre_commit': 'pre-commit',
        }
        
        # Count component occurrences
        component_counts = {}
        for file_path in all_files:
            file_name = file_path.split('/')[-1].lower()
            for pattern, component in component_mappings.items():
                if pattern in file_name:
                    component_counts[component] = component_counts.get(component, 0) + 1
        
        # Also check directories
        for directory in directories.keys():
            dir_name = directory.split('/')[-1].lower()
            for pattern, component in component_mappings.items():
                if pattern in dir_name:
                    component_counts[component] = component_counts.get(component, 0) + 1
        
        # Sort by count
        sorted_components = sorted(component_counts.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_components:
            primary_component = sorted_components[0][0]
            secondary_components = [comp for comp, _ in sorted_components[1:]]
            return primary_component, secondary_components
        
        # Fallback
        return 'gitaut', []
