#!/usr/bin/env python3
"""
Error handling system for Git automation script.
Provides custom exceptions and error handling with user-friendly messages.
"""

from typing import Optional
from .logger import Logger


class GitAutomationError(Exception):
    """Base exception for Git automation errors."""
    pass


class NotAGitRepositoryError(GitAutomationError):
    """Raised when current directory is not a Git repository."""
    pass


class GitOperationError(GitAutomationError):
    """Raised when a Git operation fails."""
    pass


class GitHubError(GitAutomationError):
    """Raised when GitHub API/CLI operation fails."""
    pass


class NoChangesError(GitAutomationError):
    """Raised when there are no changes to commit."""
    pass


class MergeConflictError(GitAutomationError):
    """Raised when merge conflicts are detected."""
    pass


class UnfinishedGitOperationError(GitAutomationError):
    """Raised when unfinished Git operation (merge/rebase/cherry-pick) is detected."""
    pass


class RemoteNotFoundError(GitAutomationError):
    """Raised when Git remote is not found."""
    pass


class GitHubCLINotFoundError(GitAutomationError):
    """Raised when GitHub CLI (gh) is not installed."""
    pass


class GitHubNotAuthenticatedError(GitAutomationError):
    """Raised when user is not authenticated with GitHub."""
    pass


class NetworkError(GitAutomationError):
    """Raised when network operation fails."""
    pass


class BranchDeletionError(GitAutomationError):
    """Raised when branch deletion fails."""
    pass


class CheckoutError(GitAutomationError):
    """Raised when git checkout fails."""
    pass


class ErrorHandler:
    """Centralized error handler with user-friendly messages."""
    
    def __init__(self, logger: Logger):
        """
        Initialize error handler.
        
        Args:
            logger: Logger instance for error logging.
        """
        self.logger = logger
    
    def handle_error(self, error: Exception, context: str = "") -> str:
        """
        Handle error and return user-friendly message.
        
        Args:
            error: The exception to handle.
            context: Additional context about where error occurred.
            
        Returns:
            User-friendly error message.
        """
        self.logger.error(f"Error in {context}: {str(error)}", exc_info=True)
        
        if isinstance(error, NotAGitRepositoryError):
            return self._handle_not_git_repo()
        elif isinstance(error, GitOperationError):
            return self._handle_git_operation(error)
        elif isinstance(error, GitHubError):
            return self._handle_github_error(error)
        elif isinstance(error, NoChangesError):
            return self._handle_no_changes()
        elif isinstance(error, MergeConflictError):
            return self._handle_merge_conflict()
        elif isinstance(error, UnfinishedGitOperationError):
            return self._handle_unfinished_operation(error)
        elif isinstance(error, RemoteNotFoundError):
            return self._handle_remote_not_found()
        elif isinstance(error, GitHubCLINotFoundError):
            return self._handle_gh_cli_not_found()
        elif isinstance(error, GitHubNotAuthenticatedError):
            return self._handle_github_not_authenticated()
        elif isinstance(error, NetworkError):
            return self._handle_network_error(error)
        elif isinstance(error, BranchDeletionError):
            return self._handle_branch_deletion(error)
        elif isinstance(error, CheckoutError):
            return self._handle_checkout_error(error)
        else:
            return self._handle_generic_error(error)
    
    def _handle_not_git_repo(self) -> str:
        """Handle not a Git repository error."""
        msg = (
            "Текущая директория не является Git-репозиторием.\n"
            "Убедитесь, что вы находитесь в директории с .git папкой."
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_git_operation(self, error: GitOperationError) -> str:
        """Handle Git operation error."""
        msg = (
            f"Ошибка операции Git: {str(error)}\n"
            "Проверьте состояние репозитория с помощью: git status"
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_github_error(self, error: GitHubError) -> str:
        """Handle GitHub error."""
        msg = (
            f"Ошибка GitHub: {str(error)}\n"
            "Проверьте доступ к репозиторию и права доступа."
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_no_changes(self) -> str:
        """Handle no changes error."""
        msg = "Нет изменений для коммита. Рабочая директория чиста."
        self.logger.failure(msg)
        return msg
    
    def _handle_merge_conflict(self) -> str:
        """Handle merge conflict error."""
        msg = (
            "Обнаружены merge-конфликты.\n"
            "Разрешите конфликты вручную перед продолжением.\n"
            "Используйте: git status для просмотра конфликтов."
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_unfinished_operation(self, error: UnfinishedGitOperationError) -> str:
        """Handle unfinished Git operation error."""
        msg = (
            f"Обнаружена незавершенная операция Git: {str(error)}\n"
            "Завершите или прервите операцию перед продолжением:\n"
            "  - Для merge: git merge --abort или git merge --continue\n"
            "  - Для rebase: git rebase --abort или git rebase --continue\n"
            "  - Для cherry-pick: git cherry-pick --abort"
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_remote_not_found(self) -> str:
        """Handle remote not found error."""
        msg = (
            "Git remote не найден.\n"
            "Убедитесь, что репозиторий имеет remote configured:\n"
            "  git remote -v\n"
            "Для добавления remote:\n"
            "  git remote add origin <repository-url>"
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_gh_cli_not_found(self) -> str:
        """Handle GitHub CLI not found error."""
        msg = (
            "GitHub CLI (gh) не установлен.\n"
            "Установите его с помощью:\n"
            "  brew install gh  (macOS)\n"
            "  или скачайте с https://cli.github.com/\n"
            "После установки авторизуйтесь: gh auth login"
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_github_not_authenticated(self) -> str:
        """Handle GitHub not authenticated error."""
        msg = (
            "Вы не авторизованы в GitHub.\n"
            "Авторизуйтесь с помощью: gh auth login"
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_network_error(self, error: NetworkError) -> str:
        """Handle network error."""
        msg = (
            f"Ошибка сети: {str(error)}\n"
            "Проверьте подключение к интернету и повторите попытку."
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_branch_deletion(self, error: BranchDeletionError) -> str:
        """Handle branch deletion error."""
        msg = (
            f"Не удалось удалить ветку: {str(error)}\n"
            "Возможно, ветка защищена или используется в другом процессе.\n"
            "Проверьте: git branch -D <branch-name>"
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_checkout_error(self, error: CheckoutError) -> str:
        """Handle checkout error."""
        msg = (
            f"Не удалось переключить ветку: {str(error)}\n"
            "Убедитесь, что нет незакоммиченных изменений или завершите их.\n"
            "Используйте: git status для проверки."
        )
        self.logger.failure(msg)
        return msg
    
    def _handle_generic_error(self, error: Exception) -> str:
        """Handle generic error."""
        msg = f"Неожиданная ошибка: {str(error)}\n{type(error).__name__}"
        self.logger.failure(msg)
        return msg
