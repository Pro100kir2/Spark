#!/usr/bin/env python3
"""
GitHub client module for Git automation script.
Wraps GitHub CLI (gh) for GitHub operations.
"""

import subprocess
import json
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

from .logger import Logger
from .error_handler import (
    GitHubError,
    GitHubCLINotFoundError,
    GitHubNotAuthenticatedError,
    NetworkError
)
from .dependency_installer import DependencyInstaller


class PRState(Enum):
    """Pull Request state."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"
    NOT_FOUND = "NOT_FOUND"


@dataclass
class PullRequest:
    """Represents a Pull Request."""
    number: int
    title: str
    state: PRState
    head_branch: str
    base_branch: str
    url: str
    body: str


class GitHubClient:
    """Wraps GitHub CLI for GitHub operations."""
    
    def __init__(self, logger: Logger, dry_run: bool = False):
        """
        Initialize GitHub client.
        
        Args:
            logger: Logger instance.
            dry_run: If True, don't execute actual gh commands.
        """
        self.logger = logger
        self.dry_run = dry_run
        self.installer = DependencyInstaller(logger)
        self._check_gh_cli()
    
    def _check_gh_cli(self) -> None:
        """Check if GitHub CLI is installed and authenticated."""
        try:
            # Check if gh is installed
            result = subprocess.run(
                ['gh', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.debug(f"GitHub CLI version: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # GitHub CLI not found, ask user if they want to install
            if self.installer.ask_install_gh_cli():
                if self.installer.install_gh_cli():
                    # Installation successful, verify
                    if self.installer.check_gh_cli_installed():
                        self.logger.success("GitHub CLI установлен и доступен")
                        return
                    else:
                        self.logger.error("GitHub CLI установлен, но не доступен")
                        raise GitHubCLINotFoundError()
                else:
                    # Installation failed
                    self.logger.error("Не удалось установить GitHub CLI")
                    raise GitHubCLINotFoundError()
            else:
                # User declined installation
                raise GitHubCLINotFoundError()
        
        # Check if authenticated
        try:
            auth_status = subprocess.run(
                ['gh', 'auth', 'status'],
                capture_output=True,
                text=True,
                check=True
            )
            if "not logged in" in auth_status.stdout.lower() or "not authenticated" in auth_status.stdout.lower():
                raise GitHubNotAuthenticatedError()
        except subprocess.CalledProcessError:
            # Not authenticated, ask user if they want to authenticate
            print("\n" + "="*60)
            print("GitHub CLI не авторизован")
            print("="*60)
            print("\nАвторизация в GitHub требуется для работы с Pull Request и другими функциями.")
            print("\nАвторизоваться сейчас? (Y/n): ", end='')
            
            try:
                response = self.installer.validator.sanitize_input(input())
                if self.installer.validator.validate_yes_no(response):
                    print("\nЗапуск gh auth login...")
                    print("Следуйте инструкциям в терминале для авторизации.")
                    
                    try:
                        # Run gh auth login interactively
                        subprocess.run(['gh', 'auth', 'login'])
                        
                        # Verify authentication after login
                        if self.installer.check_gh_cli_installed():
                            auth_check = subprocess.run(
                                ['gh', 'auth', 'status'],
                                capture_output=True,
                                text=True,
                                check=False
                            )
                            if auth_check.returncode == 0:
                                self.logger.success("Авторизация в GitHub успешна")
                                print("✓ Авторизация в GitHub успешна")
                                return
                            else:
                                self.logger.error("Авторизация не удалась")
                                print("✗ Авторизация не удалась")
                                raise GitHubNotAuthenticatedError()
                        else:
                            raise GitHubNotAuthenticatedError()
                    except Exception as e:
                        self.logger.error(f"Ошибка авторизации: {e}")
                        print(f"\n✗ Ошибка авторизации: {e}")
                        raise GitHubNotAuthenticatedError()
                else:
                    # User declined authentication
                    self.logger.info("Авторизация пропущена")
                    print("\nАвторизация пропущена.")
                    raise GitHubNotAuthenticatedError()
            except (ValueError, EOFError, KeyboardInterrupt):
                raise GitHubNotAuthenticatedError()
    
    def _run_gh_command(self, command: list, check: bool = True, ignore_dry_run: bool = False) -> str:
        """
        Run a GitHub CLI command and return output.
        
        Args:
            command: gh command as list of arguments.
            check: If True, raise exception on non-zero exit code.
            ignore_dry_run: If True, execute command even in dry-run mode (for read-only operations).
            
        Returns:
            Command output as string.
            
        Raises:
            GitHubError: If command fails.
            NetworkError: If network error occurs.
        """
        cmd_str = ' '.join(command)
        self.logger.github_api(cmd_str)
        
        if self.dry_run and not ignore_dry_run:
            self.logger.debug(f"[DRY RUN] Would execute: {cmd_str}")
            return ""
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if "network" in str(e).lower() or "connection" in str(e).lower():
                raise NetworkError(f"Network error: {e.stderr.strip()}")
            raise GitHubError(f"GitHub CLI command failed: {cmd_str}\nError: {e.stderr.strip()}")
    
    def get_repository_info(self) -> Dict[str, str]:
        """
        Get current repository information.
        
        Returns:
            Dictionary with owner and repo name.
            
        Raises:
            GitHubError: If repository doesn't exist or cannot be accessed.
        """
        try:
            # Use ignore_dry_run=True because this is a read-only operation
            output = self._run_gh_command(['gh', 'repo', 'view', '--json', 'owner,name'], ignore_dry_run=True)
            if not output or not output.strip():
                raise GitHubError("Repository not found on GitHub or no access")
            data = json.loads(output)
            return {
                'owner': data['owner']['login'],
                'name': data['name']
            }
        except json.JSONDecodeError as e:
            raise GitHubError(f"Failed to parse repository info: {e}")
    
    def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        draft: bool = False
    ) -> PullRequest:
        """
        Create a Pull Request.
        
        Args:
            title: PR title.
            body: PR description.
            head_branch: Source branch.
            base_branch: Target branch.
            draft: If True, create as draft PR.
            
        Returns:
            PullRequest object.
        """
        cmd = [
            'gh', 'pr', 'create',
            '--title', title,
            '--body', body,
            '--head', head_branch,
            '--base', base_branch
        ]
        
        if draft:
            cmd.append('--draft')
        
        output = self._run_gh_command(cmd)
        
        # Parse PR number from output or fetch it
        pr_data = self.get_pull_request_by_branch(head_branch)
        
        self.logger.success(f"Pull Request created: #{pr_data.number}")
        return pr_data
    
    def get_pull_request_by_branch(self, branch_name: str) -> Optional[PullRequest]:
        """
        Get Pull Request for a specific branch.
        
        Args:
            branch_name: Branch name to search for.
            
        Returns:
            PullRequest object if found, None otherwise.
        """
        try:
            output = self._run_gh_command([
                'gh', 'pr', 'list',
                '--head', branch_name,
                '--json', 'number,title,state,headRefName,baseRefName,url,body',
                '--limit', '1'
            ], check=True)
            
            if not output:
                return None
            
            data = json.loads(output)
            if not data:
                return None
            
            pr_data = data[0]
            
            # Map state
            state_map = {
                'OPEN': PRState.OPEN,
                'CLOSED': PRState.CLOSED,
                'MERGED': PRState.MERGED
            }
            
            return PullRequest(
                number=pr_data['number'],
                title=pr_data['title'],
                state=state_map.get(pr_data['state'], PRState.NOT_FOUND),
                head_branch=pr_data['headRefName'],
                base_branch=pr_data['baseRefName'],
                url=pr_data['url'],
                body=pr_data.get('body', '')
            )
        except GitHubError:
            return None
    
    def get_pull_request_state(self, branch_name: str) -> PRState:
        """
        Get state of Pull Request for a branch.
        
        Args:
            branch_name: Branch name to check.
            
        Returns:
            PRState enum value.
        """
        pr = self.get_pull_request_by_branch(branch_name)
        if pr:
            return pr.state
        return PRState.NOT_FOUND
    
    def update_pull_request(
        self,
        branch_name: str,
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> None:
        """
        Update an existing Pull Request.
        
        Args:
            branch_name: Branch name of the PR.
            title: New title (optional).
            body: New body (optional).
        """
        cmd = ['gh', 'pr', 'edit']
        
        if title:
            cmd.extend(['--title', title])
        if body:
            cmd.extend(['--body', body])
        
        self._run_gh_command(cmd)
        self.logger.success("Pull Request updated")
    
    def add_pull_request_comment(self, branch_name: str, comment: str) -> None:
        """
        Add a comment to a Pull Request.
        
        Args:
            branch_name: Branch name of the PR.
            comment: Comment text.
        """
        pr = self.get_pull_request_by_branch(branch_name)
        if not pr:
            raise GitHubError(f"No Pull Request found for branch: {branch_name}")
        
        self._run_gh_command([
            'gh', 'pr', 'comment',
            str(pr.number),
            '--body', comment
        ])
        self.logger.success("Comment added to Pull Request")
    
    def get_default_branch(self) -> str:
        """
        Get repository's default branch.
        
        Returns:
            Default branch name.
        """
        output = self._run_gh_command(['gh', 'repo', 'view', '--json', 'defaultBranchRef'])
        data = json.loads(output)
        return data['defaultBranchRef']['name']
    
    def check_repository_access(self) -> bool:
        """
        Check if user has access to the repository.
        
        Returns:
            True if has access, False otherwise.
        """
        try:
            self.get_repository_info()
            return True
        except GitHubError:
            return False
    
    def get_pr_checks(self, branch_name: str) -> Dict[str, str]:
        """
        Get CI/CD check status for a PR.
        
        Args:
            branch_name: Branch name to check.
            
        Returns:
            Dictionary with check status information.
        """
        pr = self.get_pull_request_by_branch(branch_name)
        if not pr:
            return {'status': 'not_found'}
        
        try:
            output = self._run_gh_command([
                'gh', 'pr', 'checks',
                str(pr.number),
                '--json', 'name,conclusion,status'
            ], check=True)
            
            checks = json.loads(output)
            
            if not checks:
                return {'status': 'no_checks'}
            
            # Determine overall status
            all_completed = all(check['status'] == 'completed' for check in checks)
            all_success = all(check['conclusion'] == 'success' for check in checks if check['conclusion'])
            any_failure = any(check['conclusion'] == 'failure' for check in checks if check['conclusion'])
            any_pending = any(check['status'] == 'in_progress' or check['status'] == 'queued' for check in checks)
            
            if any_failure:
                overall_status = 'failure'
            elif any_pending:
                overall_status = 'pending'
            elif all_success and all_completed:
                overall_status = 'success'
            else:
                overall_status = 'unknown'
            
            return {
                'status': overall_status,
                'checks': checks,
                'pr_number': pr.number
            }
            
        except GitHubError:
            return {'status': 'error'}
