#!/usr/bin/env python3
"""
Commit message generator module for Git automation script.
Generates high-quality Conventional Commits messages with scope.
"""

import re
from typing import Optional, List, Dict, Tuple

from .logger import Logger
from .change_analyzer import ChangeAnalysis
from .change_classifier import ChangeIntent


class CommitMessageGenerator:
    """Generates high-quality Conventional Commits messages with scope."""
    
    # Conventional Commits types
    CONVENTIONAL_TYPES = [
        'feat', 'fix', 'docs', 'style', 'refactor', 'perf', 
        'test', 'build', 'ci', 'chore', 'revert'
    ]
    
    # Scope mappings from directories/files to conventional scopes
    SCOPE_MAPPINGS = {
        # CI/CD
        '.github': 'ci',
        'github': 'ci',
        'workflows': 'ci',
        'actions': 'ci',
        'ci': 'ci',
        'jenkins': 'ci',
        'gitlab': 'ci',
        
        # Build
        'build': 'build',
        'docker': 'build',
        'dockerfile': 'build',
        'docker-compose': 'build',
        'makefile': 'build',
        'gradle': 'build',
        'maven': 'build',
        'webpack': 'build',
        'vite': 'build',
        
        # Auth
        'auth': 'auth',
        'authentication': 'auth',
        'login': 'auth',
        'signup': 'auth',
        'jwt': 'auth',
        'token': 'auth',
        'session': 'auth',
        'password': 'auth',
        'oauth': 'auth',
        'sso': 'auth',
        
        # API
        'api': 'api',
        'endpoint': 'api',
        'route': 'api',
        'controller': 'api',
        'handler': 'api',
        'middleware': 'api',
        'rest': 'api',
        'graphql': 'api',
        
        # Database
        'database': 'db',
        'db': 'db',
        'migration': 'db',
        'schema': 'db',
        'model': 'db',
        'query': 'db',
        'sql': 'db',
        'orm': 'db',
        'prisma': 'db',
        'sequelize': 'db',
        
        # Catalog/Search
        'catalog': 'catalog',
        'search': 'catalog',
        'filter': 'catalog',
        'pagination': 'catalog',
        'sorting': 'catalog',
        'index': 'catalog',
        'elasticsearch': 'catalog',
        
        # Documentation
        'docs': 'docs',
        'documentation': 'docs',
        'readme': 'readme',
        'changelog': 'docs',
        'guide': 'docs',
        'md': 'docs',
        
        # Tests
        'test': 'test',
        'tests': 'test',
        'spec': 'test',
        'e2e': 'test',
        'integration': 'test',
        'unit': 'test',
        '__test__': 'test',
        '__tests__': 'test',
        
        # Performance
        'perf': 'perf',
        'performance': 'perf',
        'cache': 'perf',
        'redis': 'perf',
        'optimize': 'perf',
        'latency': 'perf',
        
        # Security
        'security': 'security',
        'vulnerability': 'security',
        'cve': 'security',
        'trivy': 'security',
        'sast': 'security',
        
        # Dependencies
        'dependency': 'deps',
        'dependencies': 'deps',
        'requirement': 'deps',
        'requirements': 'deps',
        'package': 'deps',
        'lock': 'deps',
        'yarn': 'deps',
        'npm': 'deps',
        'pip': 'deps',
        
        # Config
        'config': 'config',
        'configuration': 'config',
        'setting': 'config',
        'settings': 'config',
        'env': 'config',
        'environment': 'config',
        '.env': 'config',
        
        # Monitoring
        'monitoring': 'monitoring',
        'metrics': 'monitoring',
        'logging': 'monitoring',
        'logger': 'monitoring',
        'log': 'monitoring',
        'telemetry': 'monitoring',
        
        # UI/Frontend
        'ui': 'ui',
        'frontend': 'ui',
        'component': 'ui',
        'widget': 'ui',
        'view': 'ui',
        'template': 'ui',
        'style': 'ui',
        'css': 'ui',
        'scss': 'ui',
        
        # Backend/Server
        'backend': 'server',
        'server': 'server',
        'service': 'server',
        'worker': 'server',
        'job': 'server',
        'queue': 'server',
        
        # GitAut-specific
        'gitaut': 'gitaut',
        'git-operations': 'gitaut',
        'git_operations': 'gitaut',
        'orchestrator': 'gitaut',
        'change-classifier': 'gitaut',
        'change_classifier': 'gitaut',
        'commit-generator': 'gitaut',
        'commit_generator': 'gitaut',
        'branch-namer': 'gitaut',
        'branch_namer': 'gitaut',
        'description-builder': 'gitaut',
        'description_builder': 'gitaut',
    }
    
    # Action verb templates for different change types
    ACTION_TEMPLATES = {
        'feat': {
            'add': 'add',
            'implement': 'implement',
            'create': 'create',
            'introduce': 'introduce',
            'enable': 'enable',
            'support': 'support',
        },
        'fix': {
            'fix': 'fix',
            'resolve': 'resolve',
            'correct': 'correct',
            'patch': 'patch',
            'address': 'address',
            'handle': 'handle',
        },
        'refactor': {
            'refactor': 'refactor',
            'simplify': 'simplify',
            'rework': 'rework',
            'restructure': 'restructure',
            'consolidate': 'consolidate',
            'extract': 'extract',
            'remove': 'remove',
        },
        'perf': {
            'optimize': 'optimize',
            'improve': 'improve',
            'accelerate': 'accelerate',
            'cache': 'cache',
            'reduce': 'reduce',
        },
        'docs': {
            'update': 'update',
            'add': 'add',
            'improve': 'improve',
            'clarify': 'clarify',
            'expand': 'expand',
        },
        'test': {
            'add': 'add',
            'improve': 'improve',
            'fix': 'fix',
            'expand': 'expand',
            'update': 'update',
        },
        'build': {
            'update': 'update',
            'add': 'add',
            'configure': 'configure',
            'migrate': 'migrate',
        },
        'ci': {
            'update': 'update',
            'add': 'add',
            'configure': 'configure',
            'automate': 'automate',
            'optimize': 'optimize',
        },
        'chore': {
            'update': 'update',
            'upgrade': 'upgrade',
            'add': 'add',
            'remove': 'remove',
            'cleanup': 'cleanup',
        },
        'style': {
            'format': 'format',
            'lint': 'lint',
            'fix': 'fix',
        },
    }
    
    # Object/entity extraction patterns
    ENTITY_PATTERNS = {
        # Security
        r'\btrivy\b': 'trivy',
        r'\bsast\b': 'sast',
        r'\bscan\b': 'scan',
        r'\bvulnerability\b': 'vulnerability',
        r'\bcritical\b': 'critical',
        r'\bfixable\b': 'fixable',
        r'\bgate\b': 'gate',
        
        # Auth
        r'\bjwt\b': 'jwt',
        r'\bvalidation\b': 'validation',
        r'\bverify\b': 'verify',
        r'\bcheck\b': 'check',
        r'\bempty\b': 'empty',
        r'\brequest\b': 'request',
        
        # Catalog/Search
        r'\bcatalog\b': 'catalog',
        r'\bsearch\b': 'search',
        r'\bservice\b': 'service',
        r'\bsimplify\b': 'simplify',
        r'\bcoverage\b': 'coverage',
        r'\be2e\b': 'e2e',
        r'\bimprove\b': 'improve',
        
        # CI/CD
        r'\bgithub\b': 'github',
        r'\bactions\b': 'actions',
        r'\bworkflow\b': 'workflow',
        r'\bpipeline\b': 'pipeline',
        
        # Documentation
        r'\binstallation\b': 'installation',
        r'\breadme\b': 'readme',
        r'\bsetup\b': 'setup',
        r'\bguide\b': 'guide',
    }
    
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
        Generate a high-quality Conventional Commits message with scope.
        
        Args:
            analysis: ChangeAnalysis object.
            custom_message: Optional custom message override.
            custom_type: Optional custom type override.
            
        Returns:
            Generated commit message in format: type(scope): description
        """
        if custom_message:
            scope = self._determine_scope(analysis)
            return self._format_conventional_commit(
                custom_type or analysis.likely_type,
                custom_message,
                scope
            )
        
        self.logger.step("Генерация сообщения коммита")
        
        # Determine commit type
        if analysis.change_intent:
            commit_type = custom_type if custom_type else analysis.change_intent.type
        else:
            commit_type = custom_type if custom_type else analysis.likely_type
        
        # Determine scope from directories and files
        scope = self._determine_scope(analysis)
        
        # Generate description with concrete details
        description = self._generate_description(analysis, commit_type)
        
        # Format as conventional commit with scope
        message = self._format_conventional_commit(commit_type, description, scope)
        
        self.logger.info(f"Generated commit message: {message}")
        return message
    
    def _determine_scope(self, analysis: ChangeAnalysis) -> Optional[str]:
        """
        Determine scope from directories and files.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            Scope string or None.
        """
        # Check directories first (higher priority)
        for directory in analysis.directories.keys():
            dir_lower = directory.lower()
            for pattern, scope in self.SCOPE_MAPPINGS.items():
                if pattern in dir_lower:
                    return scope
        
        # Check files
        all_files = analysis.added_files + analysis.modified_files + analysis.deleted_files
        for file_path in all_files:
            file_lower = file_path.lower()
            for pattern, scope in self.SCOPE_MAPPINGS.items():
                if pattern in file_lower:
                    return scope
        
        # Check diff summary for scope hints
        diff_lower = analysis.diff_summary.lower()
        for pattern, scope in self.SCOPE_MAPPINGS.items():
            if pattern in diff_lower:
                return scope
        
        return None
    
    def _generate_description(self, analysis: ChangeAnalysis, commit_type: str) -> str:
        """
        Generate a concrete, meaningful description.
        
        Args:
            analysis: ChangeAnalysis object.
            commit_type: Type of commit.
            
        Returns:
            Description string.
        """
        # Extract entities from diff and files
        entities = self._extract_entities(analysis)
        
        # Get action verb for this type
        action = self._get_action_verb(commit_type, analysis)
        
        # Build description with action + entity(s)
        if entities:
            # Use the most relevant entity
            main_entity = entities[0]
            
            # Check if we have multiple entities for compound description
            if len(entities) >= 2:
                secondary_entity = entities[1]
                description = f"{action} {main_entity} {secondary_entity}"
            else:
                description = f"{action} {main_entity}"
        else:
            # Fallback to generic description
            description = self._get_generic_description(commit_type, analysis)
        
        # Truncate to fit within limits
        description = self._smart_truncate(description, max_length=50)
        
        return description
    
    def _extract_entities(self, analysis: ChangeAnalysis) -> List[str]:
        """
        Extract concrete entities from diff and files.
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            List of entity strings.
        """
        entities = []
        
        # Extract from diff using entity patterns
        diff_lower = analysis.diff_summary.lower()
        for pattern, entity in self.ENTITY_PATTERNS.items():
            if re.search(pattern, diff_lower) and entity not in entities:
                entities.append(entity)
        
        # Extract from file names
        all_files = analysis.added_files + analysis.modified_files + analysis.deleted_files
        for file_path in all_files:
            file_lower = file_path.lower()
            for pattern, entity in self.ENTITY_PATTERNS.items():
                if pattern in file_lower and entity not in entities:
                    entities.append(entity)
        
        # Extract from directories
        for directory in analysis.directories.keys():
            dir_lower = directory.lower()
            for pattern, entity in self.ENTITY_PATTERNS.items():
                if pattern in dir_lower and entity not in entities:
                    entities.append(entity)
        
        # If no entities found, try to extract from file names directly
        if not entities:
            for file_path in all_files:
                file_name = file_path.split('/')[-1]
                # Remove extension
                file_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
                # Convert hyphens/underscores to spaces
                clean_name = file_name.replace('-', ' ').replace('_', ' ')
                if len(clean_name) > 3 and clean_name not in entities:
                    entities.append(clean_name)
                    if len(entities) >= 3:
                        break
        
        return entities[:3]  # Limit to top 3 entities
    
    def _get_action_verb(self, commit_type: str, analysis: ChangeAnalysis) -> str:
        """
        Get appropriate action verb for the commit type.
        
        Args:
            commit_type: Type of commit.
            analysis: ChangeAnalysis object.
            
        Returns:
            Action verb string.
        """
        if commit_type in self.ACTION_TEMPLATES:
            templates = self.ACTION_TEMPLATES[commit_type]
            
            # Choose action based on file operations
            if analysis.added_files and not analysis.modified_files and not analysis.deleted_files:
                return templates.get('add', 'add')
            elif analysis.deleted_files and not analysis.added_files:
                return templates.get('remove', 'remove')
            else:
                # Default to first action
                return list(templates.values())[0]
        
        return 'update'
    
    def _get_generic_description(self, commit_type: str, analysis: ChangeAnalysis) -> str:
        """
        Get a generic description when no entities are found.
        
        Args:
            commit_type: Type of commit.
            analysis: ChangeAnalysis object.
            
        Returns:
            Generic description string.
        """
        generic_descriptions = {
            'feat': 'add feature',
            'fix': 'fix bug',
            'refactor': 'refactor code',
            'perf': 'optimize performance',
            'docs': 'update documentation',
            'test': 'add tests',
            'build': 'update build',
            'ci': 'update ci',
            'chore': 'update dependencies',
            'style': 'format code',
        }
        
        return generic_descriptions.get(commit_type, 'update code')
    
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
    
    def _format_conventional_commit(self, commit_type: str, description: str, scope: Optional[str] = None) -> str:
        """
        Format message as Conventional Commit with optional scope.
        
        Args:
            commit_type: Type of commit.
            description: Description of changes.
            scope: Optional scope (e.g., ci, api, auth).
            
        Returns:
            Formatted commit message: type(scope): description or type: description
        """
        # Ensure type is valid
        if commit_type not in self.CONVENTIONAL_TYPES:
            commit_type = 'chore'
        
        # Format: type(scope): description or type: description
        if scope:
            message = f"{commit_type}({scope}): {description}"
        else:
            message = f"{commit_type}: {description}"
        
        # Limit to 72 characters (Git standard)
        if len(message) > 72:
            # Calculate max description length
            if scope:
                max_desc_length = 72 - len(commit_type) - len(scope) - 4  # -4 for "(): "
            else:
                max_desc_length = 72 - len(commit_type) - 2  # -2 for ": "
            
            description = description[:max_desc_length]
            
            if scope:
                message = f"{commit_type}({scope}): {description}"
            else:
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
        # Check for conventional commits format with optional scope
        pattern = r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9-]+\))?: .{1,72}$'
        return bool(re.match(pattern, message))
