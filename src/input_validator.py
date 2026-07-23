#!/usr/bin/env python3
"""
Input validation module for Git automation script.
Provides safe input validation functions.
"""

import re
from typing import Optional, List


class InputValidator:
    """Validates user input to prevent security issues."""
    
    # Allowed characters for branch names (Git-safe)
    BRANCH_NAME_PATTERN = r'^[a-zA-Z0-9\-_/]+$'
    
    # Allowed characters for commit messages
    COMMIT_MESSAGE_PATTERN = r'^[a-zA-Z0-9\s\-_.,;:!?\'"()]+$'
    
    # Max lengths
    MAX_BRANCH_NAME_LENGTH = 255
    MAX_COMMIT_MESSAGE_LENGTH = 72
    MAX_INPUT_LENGTH = 1000
    
    @staticmethod
    def validate_yes_no(response: str) -> bool:
        """
        Validate yes/no response.
        
        Args:
            response: User input string.
            
        Returns:
            True if yes, False if no.
            
        Raises:
            ValueError: If response is invalid.
        """
        response = response.strip().lower()
        valid_yes = ['', 'y', 'yes', 'да', 'д']
        valid_no = ['n', 'no', 'нет', 'н']
        
        if response in valid_yes:
            return True
        elif response in valid_no:
            return False
        else:
            raise ValueError(f"Invalid response: {response}. Please enter 'y' or 'n'.")
    
    @staticmethod
    def validate_branch_name(name: str) -> str:
        """
        Validate branch name.
        
        Args:
            name: Branch name to validate.
            
        Returns:
            Sanitized branch name.
            
        Raises:
            ValueError: If branch name is invalid.
        """
        if not name:
            raise ValueError("Branch name cannot be empty")
        
        if len(name) > InputValidator.MAX_BRANCH_NAME_LENGTH:
            raise ValueError(f"Branch name too long (max {InputValidator.MAX_BRANCH_NAME_LENGTH} characters)")
        
        # Check for invalid characters
        if not re.match(InputValidator.BRANCH_NAME_PATTERN, name):
            raise ValueError("Branch name contains invalid characters. Only alphanumeric, hyphens, underscores, and slashes allowed.")
        
        # Check for reserved names
        reserved_names = ['head', 'main', 'master', 'develop']
        if name.lower() in reserved_names:
            raise ValueError(f"'{name}' is a reserved branch name")
        
        # Check for consecutive slashes
        if '//' in name:
            raise ValueError("Branch name cannot contain consecutive slashes")
        
        # Check for leading/trailing slashes or hyphens
        if name.startswith(('/', '-')) or name.endswith(('/', '-')):
            raise ValueError("Branch name cannot start or end with slash or hyphen")
        
        return name
    
    @staticmethod
    def validate_commit_message(message: str) -> str:
        """
        Validate commit message.
        
        Args:
            message: Commit message to validate.
            
        Returns:
            Sanitized commit message.
            
        Raises:
            ValueError: If commit message is invalid.
        """
        if not message:
            raise ValueError("Commit message cannot be empty")
        
        if len(message) > InputValidator.MAX_COMMIT_MESSAGE_LENGTH:
            raise ValueError(f"Commit message too long (max {InputValidator.MAX_COMMIT_MESSAGE_LENGTH} characters)")
        
        # Check for potentially dangerous characters
        if not re.match(InputValidator.COMMIT_MESSAGE_PATTERN, message):
            raise ValueError("Commit message contains invalid characters")
        
        return message
    
    @staticmethod
    def validate_menu_choice(choice: str, valid_choices: List[str]) -> str:
        """
        Validate menu choice.
        
        Args:
            choice: User's choice.
            valid_choices: List of valid choices.
            
        Returns:
            Validated choice.
            
        Raises:
            ValueError: If choice is invalid.
        """
        choice = choice.strip()
        if choice not in valid_choices:
            raise ValueError(f"Invalid choice: {choice}. Valid choices: {', '.join(valid_choices)}")
        return choice
    
    @staticmethod
    def sanitize_input(input_str: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize general user input.
        
        Args:
            input_str: Input string to sanitize.
            max_length: Maximum allowed length.
            
        Returns:
            Sanitized string.
        """
        if not input_str:
            return ""
        
        # Strip whitespace
        sanitized = input_str.strip()
        
        # Apply max length
        if max_length:
            max_len = min(max_length, InputValidator.MAX_INPUT_LENGTH)
            sanitized = sanitized[:max_len]
        
        # Remove null bytes and other control characters (except newline)
        sanitized = ''.join(char for char in sanitized if char == '\n' or (ord(char) >= 32 and ord(char) != 127))
        
        return sanitized
