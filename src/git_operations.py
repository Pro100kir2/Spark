#!/usr/bin/env python3
"""
Git operations module for Git automation script.
Handles all Git repository operations.
"""

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .logger import Logger
from .error_handler import (
    GitOperationError,
    NotAGitRepositoryError,
    MergeConflictError,
    UnfinishedGitOperationError,
    RemoteNotFoundError,
    CheckoutError,
    BranchDeletionError
)


@dataclass
class GitStatus:
    """Represents Git repository status."""
    is_repo: bool
    current_branch: str
    has_changes: bool
    staged_files: List[str]
    unstaged_files: List[str]
    untracked_files: List[str]
    has_conflicts: bool
    unfinished_operation: Optional[str]


@dataclass
class FileChange:
    """Represents a file change."""
    path: str
    status: str  # 'added', 'modified', 'deleted', 'renamed'


class GitOperations:
    """Handles all Git repository operations."""
    
    def __init__(self, logger: Logger, dry_run: bool = False):
        """
        Initialize Git operations handler.
        
        Args:
            logger: Logger instance.
            dry_run: If True, don't execute actual Git commands.
        """
        self.logger = logger
        self.dry_run = dry_run
    
    def _run_git_command(self, command: List[str], check: bool = True, return_result: bool = False, ignore_dry_run: bool = False) -> str | subprocess.CompletedProcess:
        """
        Run a Git command and return output or result object.
        
        Args:
            command: Git command as list of arguments.
            check: If True, raise exception on non-zero exit code.
            return_result: If True, return the full CompletedProcess object instead of just stdout.
            ignore_dry_run: If True, execute command even in dry-run mode (for read-only operations).
            
        Returns:
            Command output as string, or CompletedProcess object if return_result=True.
            
        Raises:
            GitOperationError: If command fails and check=True.
        """
        cmd_str = ' '.join(command)
        self.logger.git_command(cmd_str)
        
        if self.dry_run and not ignore_dry_run:
            self.logger.debug(f"[DRY RUN] Would execute: {cmd_str}")
            if return_result:
                # Return a mock result object for dry-run
                class MockResult:
                    returncode = 0
                    stdout = ""
                    stderr = ""
                return MockResult()
            return ""
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check
            )
            if return_result:
                return result
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {cmd_str}\nError: {e.stderr.strip()}"
            raise GitOperationError(error_msg)
    
    def is_git_repository(self) -> bool:
        """
        Check if current directory is a Git repository.
        
        Returns:
            True if Git repository, False otherwise.
        """
        try:
            self._run_git_command(['git', 'rev-parse', '--git-dir'], check=True)
            return True
        except GitOperationError:
            return False
    
    def get_current_branch(self) -> str:
        """
        Get current branch name.
        
        Returns:
            Current branch name.
            
        Raises:
            GitOperationError: If command fails.
        """
        return self._run_git_command(['git', 'branch', '--show-current'])
    
    def check_for_unfinished_operations(self) -> Optional[str]:
        """
        Check for unfinished Git operations (merge, rebase, cherry-pick).
        
        Returns:
            Name of unfinished operation if found, None otherwise.
        """
        # Check for MERGE_HEAD
        try:
            merge_head = self._run_git_command(['git', 'rev-parse', '--verify', 'MERGE_HEAD'], check=False)
            if merge_head:
                return "merge"
        except GitOperationError:
            pass
        
        # Check for .git/REBASE_HEAD
        git_dir = Path('.git')
        if git_dir.exists():
            if (git_dir / 'REBASE_HEAD').exists():
                return "rebase"
            if (git_dir / 'CHERRY_PICK_HEAD').exists():
                return "cherry-pick"
            if (git_dir / 'MERGE_MSG').exists():
                return "merge"
        
        return None
    
    def get_status(self) -> GitStatus:
        """
        Get comprehensive Git repository status.
        
        Returns:
            GitStatus object with repository state.
            
        Raises:
            NotAGitRepositoryError: If not a Git repository.
        """
        if not self.is_git_repository():
            raise NotAGitRepositoryError()
        
        current_branch = self.get_current_branch()
        unfinished_operation = self.check_for_unfinished_operations()
        
        # Get porcelain status
        status_output = self._run_git_command(['git', 'status', '--porcelain'])
        
        staged_files = []
        unstaged_files = []
        untracked_files = []
        has_changes = False
        has_conflicts = False
        
        for line in status_output.split('\n'):
            if not line:
                continue
            
            status_code = line[:2]
            # File path starts after the 2-char status code
            # Handle renamed files which have format: R100\told_file\tnew_file
            if '\t' in line:
                parts = line.split('\t')
                file_path = parts[-1]  # Get the last part (new file for renames)
            else:
                # Standard format: XY filename (where XY is 2-char status code)
                # Strip the status code and any leading whitespace
                file_path = line[2:].lstrip() if len(line) > 2 else ''
            
            if not file_path:
                continue
            
            self.logger.debug(f"Status line: '{line}' -> status_code: '{status_code}', file_path: '{file_path}'")
            
            if status_code == '??':
                untracked_files.append(file_path)
            elif status_code[0] in 'MADRC':
                staged_files.append(file_path)
                has_changes = True
            elif status_code[1] in 'MADRC':
                unstaged_files.append(file_path)
                has_changes = True
            
            # Check for conflicts (both sides modified)
            if status_code == 'UU':
                has_conflicts = True
        
        return GitStatus(
            is_repo=True,
            current_branch=current_branch,
            has_changes=has_changes or len(untracked_files) > 0,
            staged_files=staged_files,
            unstaged_files=unstaged_files,
            untracked_files=untracked_files,
            has_conflicts=has_conflicts,
            unfinished_operation=unfinished_operation
        )
    
    def get_changed_files(self) -> List[FileChange]:
        """
        Get list of changed files with their status.
        
        Returns:
            List of FileChange objects.
        """
        changes = []
        
        # Get unstaged diff with rename detection (ignore dry-run for read-only operation)
        diff_output = self._run_git_command(['git', 'diff', '--name-status', '--diff-filter=ADMR'], ignore_dry_run=True)
        
        # Get staged diff with rename detection (ignore dry-run for read-only operation)
        staged_output = self._run_git_command(['git', 'diff', '--cached', '--name-status', '--diff-filter=ADMR'], ignore_dry_run=True)
        
        # Combine both outputs
        all_diffs = diff_output + '\n' + staged_output
        
        for line in all_diffs.split('\n'):
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) >= 2:
                status_code = parts[0]
                file_path = parts[1]
                
                # Handle renamed files (format: R100\told\tnew)
                if status_code.startswith('R') and len(parts) >= 3:
                    file_path = parts[2]  # Use the new path
                
                status_map = {
                    'A': 'added',
                    'D': 'deleted',
                    'M': 'modified',
                    'R': 'renamed'
                }
                
                changes.append(FileChange(
                    path=file_path,
                    status=status_map.get(status_code[0], 'modified')
                ))
        
        return changes
    
    def get_diff(self, staged: bool = False) -> str:
        """
        Get git diff output.
        
        Args:
            staged: If True, get staged changes diff. If False, get both staged and unstaged.
            
        Returns:
            Diff output as string.
        """
        if staged:
            return self._run_git_command(['git', 'diff', '--cached'], ignore_dry_run=True)
        # Get both staged and unstaged changes (ignore dry-run for read-only operation)
        unstaged = self._run_git_command(['git', 'diff'], ignore_dry_run=True)
        staged = self._run_git_command(['git', 'diff', '--cached'], ignore_dry_run=True)
        return unstaged + '\n' + staged
    
    def create_branch(self, branch_name: str) -> None:
        """
        Create a new branch.
        
        Args:
            branch_name: Name of the branch to create.
            
        Raises:
            GitOperationError: If branch creation fails.
        """
        self._run_git_command(['git', 'branch', branch_name])
        self.logger.success(f"Branch created: {branch_name}")
    
    def checkout_branch(self, branch_name: str) -> None:
        """
        Checkout a branch.
        
        Args:
            branch_name: Name of the branch to checkout.
            
        Raises:
            CheckoutError: If checkout fails.
        """
        try:
            self._run_git_command(['git', 'checkout', branch_name])
            self.logger.success(f"Switched to branch: {branch_name}")
        except GitOperationError as e:
            raise CheckoutError(f"Failed to checkout branch {branch_name}: {str(e)}")
    
    def create_and_checkout_branch(self, branch_name: str) -> None:
        """
        Create and checkout a new branch in one command.
        If branch already exists, just checkout to it.
        
        Args:
            branch_name: Name of the branch to create and checkout.
        """
        try:
            self._run_git_command(['git', 'checkout', '-b', branch_name])
            self.logger.success(f"Created and switched to branch: {branch_name}")
        except GitOperationError as e:
            if "already exists" in str(e):
                # Branch already exists, just checkout to it
                self._run_git_command(['git', 'checkout', branch_name])
                self.logger.success(f"Switched to existing branch: {branch_name}")
            else:
                raise
    
    def add_files(self, file_paths: List[str]) -> None:
        """
        Add files to staging area or remove deleted files.
        
        Args:
            file_paths: List of file paths to add or remove.
        """
        added_count = 0
        for file_path in file_paths:
            # Check if file exists
            if Path(file_path).exists():
                self._run_git_command(['git', 'add', file_path])
                added_count += 1
            else:
                # File was deleted, use git rm
                try:
                    self._run_git_command(['git', 'rm', file_path])
                    added_count += 1
                except GitOperationError:
                    # File might not be tracked, ignore deletion completely
                    self.logger.debug(f"File {file_path} not tracked, skipping deletion")
        if added_count > 0:
            self.logger.success(f"Added {added_count} file(s) to staging area")
        else:
            self.logger.info("No files were added to staging area")
    
    def add_all_changes(self) -> None:
        """Add all changes to staging area."""
        self._run_git_command(['git', 'add', '.'])
        self.logger.success("Added all changes to staging area")
    
    def commit(self, message: str, amend: bool = False) -> None:
        """
        Create a commit with the given message.
        
        Args:
            message: Commit message.
            amend: If True, amend the last commit instead of creating a new one (DANGEROUS if pushed).
            
        Raises:
            GitOperationError: If commit fails.
        """
        if amend and not self.dry_run:
            # Check if commit is already pushed
            try:
                result = self._run_git_command(['git', 'rev-parse', '@{u}'], check=False)
                if result.returncode == 0:
                    # Upstream exists, check if HEAD is ahead
                    ahead_result = self._run_git_command(['git', 'rev-list', '--count', '@{u}..HEAD'], check=False)
                    if ahead_result.returncode == 0:
                        ahead_count = int(ahead_result.stdout.strip())
                        if ahead_count == 0:
                            # HEAD is not ahead, meaning commit is already pushed
                            self.logger.warning("DANGEROUS: Amending a commit that is already pushed")
                            self.logger.warning("This will require force push and may affect other developers")
                            
                            if not self._confirm_dangerous_operation("git commit --amend on pushed commit"):
                                raise GitOperationError("Отменено пользователем (safety check)")
            except (GitOperationError, AttributeError, subprocess.SubprocessError):
                # If we can't check, still warn but proceed
                self.logger.warning("Could not verify if commit is pushed. Proceeding with caution.")
        
        if amend:
            self._run_git_command(['git', 'commit', '--amend', '-m', message])
            self.logger.success(f"Commit amended: {message[:50]}...")
        else:
            self._run_git_command(['git', 'commit', '-m', message])
            self.logger.success(f"Commit created: {message[:50]}...")
    
    def push(self, branch_name: str, set_upstream: bool = True, force: bool = False) -> None:
        """
        Push branch to remote.
        
        Args:
            branch_name: Branch name to push.
            set_upstream: If True, set upstream branch.
            force: If True, force push (DANGEROUS).
            
        Raises:
            GitOperationError: If push fails.
        """
        if force and not self.dry_run:
            self.logger.warning("DANGEROUS OPERATION: git push --force")
            self.logger.warning("This will overwrite remote history")
            
            if not self._confirm_dangerous_operation("git push --force"):
                raise GitOperationError("Отменено пользователем (safety check)")
        
        if set_upstream:
            self._run_git_command(['git', 'push', '-u', 'origin', branch_name])
        else:
            if force:
                self._run_git_command(['git', 'push', '--force', 'origin', branch_name])
            else:
                self._run_git_command(['git', 'push', 'origin', branch_name])
        self.logger.success(f"Pushed branch: {branch_name}")
    
    def pull(self, branch: str = '') -> None:
        """
        Pull latest changes from remote.
        
        Args:
            branch: Branch to pull (empty for current branch).
        """
        if branch:
            self._run_git_command(['git', 'pull', 'origin', branch])
        else:
            self._run_git_command(['git', 'pull'])
        self.logger.success("Pulled latest changes")
    
    def reset_hard(self, ref: str, force: bool = False) -> None:
        """
        Hard reset to a reference (DANGEROUS OPERATION).
        
        Args:
            ref: Reference to reset to (e.g., 'origin/main').
            force: If True, skip safety check.
            
        Raises:
            GitOperationError: If safety check fails.
        """
        if not force and not self.dry_run:
            self.logger.warning("DANGEROUS OPERATION: git reset --hard")
            self.logger.warning("This will discard all uncommitted changes")
            
            if not self._confirm_dangerous_operation("git reset --hard"):
                raise GitOperationError("Отменено пользователем (safety check)")
        
        self._run_git_command(['git', 'reset', '--hard', ref])
        self.logger.success(f"Reset to {ref}")
    
    def delete_local_branch(self, branch_name: str, force: bool = False) -> None:
        """
        Delete a local branch.
        
        Args:
            branch_name: Branch name to delete.
            force: If True, force delete.
            
        Raises:
            BranchDeletionError: If deletion fails.
        """
        try:
            if force:
                self._run_git_command(['git', 'branch', '-D', branch_name])
            else:
                self._run_git_command(['git', 'branch', '-d', branch_name])
            self.logger.success(f"Deleted local branch: {branch_name}")
        except GitOperationError as e:
            raise BranchDeletionError(f"Failed to delete local branch {branch_name}: {str(e)}")
    
    def delete_remote_branch(self, branch_name: str) -> None:
        """
        Delete a remote branch.
        
        Args:
            branch_name: Branch name to delete.
            
        Raises:
            BranchDeletionError: If deletion fails.
        """
        try:
            self._run_git_command(['git', 'push', 'origin', '--delete', branch_name])
            self.logger.success(f"Deleted remote branch: {branch_name}")
        except GitOperationError as e:
            raise BranchDeletionError(f"Failed to delete remote branch {branch_name}: {str(e)}")
    
    def get_remote_url(self) -> Optional[str]:
        """
        Get remote repository URL.
        
        Returns:
            Remote URL or None if not configured.
        """
        self.logger.debug("Attempting to get remote URL")
        
        try:
            # Try git remote get-url first (more reliable)
            # Use ignore_dry_run=True because this is a read-only operation
            url = self._run_git_command(['git', 'remote', 'get-url', 'origin'], ignore_dry_run=True)
            if url:
                self.logger.debug(f"Remote URL found via get-url: {url}")
                return url
        except GitOperationError as e:
            self.logger.debug(f"git remote get-url failed: {e}")
        
        try:
            # Fallback to git config
            url = self._run_git_command(['git', 'config', '--get', 'remote.origin.url'], ignore_dry_run=True)
            if url:
                self.logger.debug(f"Remote URL found via config: {url}")
                return url
        except GitOperationError as e:
            self.logger.debug(f"git config failed: {e}")
        
        # Try listing all remotes as a last resort
        try:
            remotes = self._run_git_command(['git', 'remote', '-v'], ignore_dry_run=True)
            self.logger.debug(f"All remotes: {remotes}")
            if remotes and 'origin' in remotes:
                # Parse the output to extract origin URL
                for line in remotes.split('\n'):
                    if line.startswith('origin'):
                        parts = line.split()
                        if len(parts) >= 2:
                            url = parts[1]
                            self.logger.debug(f"Remote URL found via remote -v: {url}")
                            return url
        except GitOperationError as e:
            self.logger.debug(f"git remote -v failed: {e}")
        
        self.logger.warning("No remote URL found")
        return None
    
    def _confirm_dangerous_operation(self, operation: str) -> bool:
        """
        Ask user for confirmation before dangerous operation.
        
        Args:
            operation: Description of the operation.
            
        Returns:
            True if user confirms, False otherwise.
        """
        print(f"\n⚠️  DANGEROUS OPERATION: {operation}")
        print("This operation may cause data loss or history corruption.")
        print("Are you sure you want to proceed? (yes/no): ", end='')
        response = input().strip().lower()
        return response == 'yes'
    
    def branch_exists(self, branch_name: str) -> bool:
        """
        Check if a branch exists locally.
        
        Args:
            branch_name: Branch name to check.
            
        Returns:
            True if branch exists, False otherwise.
        """
        try:
            self._run_git_command(['git', 'rev-parse', '--verify', branch_name], check=True)
            return True
        except GitOperationError:
            return False
    
    def get_all_branches(self) -> List[str]:
        """
        Get list of all local branches.
        
        Returns:
            List of branch names.
        """
        output = self._run_git_command(['git', 'branch', '--format=%(refname:short)'])
        return [b for b in output.split('\n') if b]
    
    def is_detached_head(self) -> bool:
        """
        Check if HEAD is detached.
        
        Returns:
            True if detached, False otherwise.
        """
        try:
            self._run_git_command(['git', 'symbolic-ref', '-q', 'HEAD'], check=True)
            return False
        except GitOperationError:
            return True
