#!/usr/bin/env python3
"""
Orchestrator module for Git automation script.
Coordinates all modules to implement the complete workflow.
"""

from typing import Optional, List
from pathlib import Path

from .logger import Logger
from .error_handler import (
    ErrorHandler,
    GitAutomationError,
    NotAGitRepositoryError,
    NoChangesError,
    MergeConflictError,
    UnfinishedGitOperationError,
    RemoteNotFoundError,
    GitOperationError,
    GitHubError,
    GitHubNotAuthenticatedError
)
from .git_operations import GitOperations
from .github_client import GitHubClient, PRState
from .change_analyzer import ChangeAnalyzer
from .branch_namer import BranchNameGenerator
from .commit_generator import CommitMessageGenerator
from .pre_commit_hooks import PreCommitHooks
from .config_loader import ConfigLoader
from .input_validator import InputValidator


class Orchestrator:
    """Orchestrates the complete Git automation workflow."""
    
    def __init__(
        self,
        logger: Logger,
        dry_run: bool = False,
        interactive: bool = False,
        create_pr: bool = False,
        amend: bool = False,
        custom_branch_name: Optional[str] = None,
        custom_commit_message: Optional[str] = None
    ):
        """
        Initialize orchestrator.
        
        Args:
            logger: Logger instance.
            dry_run: If True, don't execute actual operations.
            interactive: If True, prompt user for confirmations.
            create_pr: If True, create PR automatically after push.
            amend: If True, amend last commit instead of creating new one.
            custom_branch_name: Optional custom branch name.
            custom_commit_message: Optional custom commit message.
        """
        self.logger = logger
        self.dry_run = dry_run
        self.interactive = interactive
        self.create_pr = create_pr
        self.amend = amend
        self.custom_branch_name = custom_branch_name
        self.custom_commit_message = custom_commit_message
        
        # Initialize error handler
        self.error_handler = ErrorHandler(logger)
        
        # Initialize modules (will be initialized in run())
        self.git_ops: Optional[GitOperations] = None
        self.github_client: Optional[GitHubClient] = None
        self.change_analyzer: Optional[ChangeAnalyzer] = None
        self.branch_namer: Optional[BranchNameGenerator] = None
        self.commit_generator: Optional[CommitMessageGenerator] = None
        self.pre_commit_hooks: Optional[PreCommitHooks] = None
        self.config_loader: Optional[ConfigLoader] = None
        self.sensitive_files: List[str] = []
        self.local_mode: bool = False  # Track if we're in local-only mode
    
    def run(self) -> bool:
        """
        Run the complete workflow.
        
        Returns:
            True if workflow completed successfully, False otherwise.
        """
        try:
            # Initialize modules
            self._initialize_modules()
            
            # Step 1: Check repository
            self._check_repository()
            
            # Step 2: Check for existing workflow (idempotency)
            existing_branch = self._check_existing_workflow()
            
            if existing_branch:
                # Continue existing workflow
                return self._continue_existing_workflow(existing_branch)
            else:
                # Start new workflow
                return self._start_new_workflow()
                
        except (GitAutomationError, GitOperationError, GitHubError) as e:
            error_msg = self.error_handler.handle_error(e, "workflow execution")
            self.logger.failure(f"Workflow failed: {error_msg}")
            return False
        except (KeyboardInterrupt, EOFError):
            self.logger.warning("Operation interrupted by user")
            return False
        except Exception as e:
            # Catch-all for truly unexpected errors
            self.logger.critical(f"Unexpected error in workflow: {e}", exc_info=True)
            return False
    
    def _initialize_modules(self) -> None:
        """Initialize all modules."""
        self.git_ops = GitOperations(self.logger, self.dry_run)
        self.github_client = GitHubClient(self.logger, self.dry_run)
        self.change_analyzer = ChangeAnalyzer(self.git_ops, self.logger)
        self.branch_namer = BranchNameGenerator(self.logger)
        self.commit_generator = CommitMessageGenerator(self.logger)
        
        # Load configuration and initialize pre-commit hooks
        try:
            config_loader = ConfigLoader(self.logger)
            self.config_loader = config_loader
            pre_commit_commands = config_loader.get_pre_commit_commands()
            self.sensitive_files = config_loader.get_sensitive_files()
            self.pre_commit_hooks = PreCommitHooks(
                self.logger,
                commands=pre_commit_commands,
                dry_run=self.dry_run
            )
            self.logger.debug(f"Loaded {len(pre_commit_commands)} pre-commit commands from config")
            self.logger.debug(f"Loaded {len(self.sensitive_files)} sensitive file patterns from config")
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}. Using defaults.")
            self.config_loader = None
            self.sensitive_files = ['.env', '.gitignore', '.idea', '.vscode', 'node_modules', 'dist', 'build', 'coverage']
            self.pre_commit_hooks = PreCommitHooks(
                self.logger,
                commands=[],
                dry_run=self.dry_run
            )
    
    def _check_repository(self) -> None:
        """Check repository state and prerequisites."""
        self.logger.step("Проверка репозитория")
        
        # Check if Git repository
        if not self.git_ops.is_git_repository():
            raise NotAGitRepositoryError()
        
        self.logger.success("Git-репозиторий обнаружен")
        
        # Check for remote
        remote_url = self.git_ops.get_remote_url()
        self.logger.debug(f"Remote URL check result: {remote_url}")
        
        if not remote_url:
            if self.interactive or self.dry_run:
                print("\n" + "="*60)
                print("Git remote не настроен")
                print("="*60)
                print("\nGit remote требуется для работы с GitHub (push, PR и т.д.).")
                print("\nВарианты:")
                print("1. Добавить remote сейчас")
                print("2. Продолжить без remote (только локальные операции)")
                print("\nВыберите вариант (1/2): ", end='')
                
                response = InputValidator.sanitize_input(input())
                try:
                    response = InputValidator.validate_menu_choice(response, ['1', '2'])
                except ValueError as e:
                    self.logger.warning(f"Invalid input: {e}")
                    response = '2'  # Default to continue without remote
                
                if response == '1':
                    # Ask for remote URL
                    print("\nВведите URL репозитория GitHub:")
                    print("Пример: https://github.com/username/repo.git")
                    print("Или: git@github.com:username/repo.git")
                    print("URL: ", end='')
                    remote_url = InputValidator.sanitize_input(input(), max_length=500)
                    
                    if remote_url:
                        try:
                            self.git_ops._run_git_command(['git', 'remote', 'add', 'origin', remote_url])
                            self.logger.success(f"Remote добавлен: {remote_url}")
                            print(f"✓ Remote добавлен: {remote_url}")
                        except GitOperationError as e:
                            self.logger.error(f"Не удалось добавить remote: {e}")
                            print(f"\n✗ Не удалось добавить remote: {e}")
                            print("Попробуйте добавить вручную:")
                            print(f"  git remote add origin {remote_url}")
                            raise RemoteNotFoundError()
                    else:
                        self.logger.warning("URL не предоставлен")
                        print("\nURL не предоставлен. Продолжаем без remote.")
                        remote_url = None
                else:
                    # Continue without remote
                    self.logger.info("Продолжаем без remote (локальный режим)")
                    print("\nПродолжаем в локальном режиме (без GitHub интеграции).")
                    remote_url = None
                    self.local_mode = True
            else:
                raise RemoteNotFoundError()
        
        if remote_url:
            self.logger.success(f"Remote настроен: {remote_url}")
            
            # Check GitHub access (only if remote is configured)
            try:
                if not self.github_client.check_repository_access():
                    if self.interactive or self.dry_run:
                        print("\n" + "="*60)
                        print("Нет доступа к GitHub")
                        print("="*60)
                        print("\nВозможные причины:")
                        print("- Репозиторий не существует на GitHub")
                        print("- Нет прав доступа к репозиторию")
                        print("- Проблемы с сетью")
                        print("\nВарианты:")
                        print("1. Попробовать авторизоваться снова")
                        print("2. Продолжить без GitHub (локальный режим)")
                        print("\nВыберите вариант (1/2): ", end='')
                        
                        response = InputValidator.sanitize_input(input())
                        try:
                            response = InputValidator.validate_menu_choice(response, ['1', '2'])
                        except ValueError as e:
                            self.logger.warning(f"Invalid input: {e}")
                            response = '2'  # Default to local mode
                        
                        if response == '1':
                            # Try to re-authenticate by reinitializing GitHub client
                            self.github_client = GitHubClient(self.logger, self.dry_run)
                            if not self.github_client.check_repository_access():
                                raise GitHubError("Нет доступа к репозиторию GitHub")
                            self.logger.success("Доступ к GitHub подтвержден")
                        else:
                            # Continue without GitHub
                            self.logger.info("Продолжаем без GitHub (локальный режим)")
                            print("\nПродолжаем в локальном режиме (без GitHub интеграции).")
                            self.local_mode = True
                    else:
                        raise GitHubError("Нет доступа к репозиторию GitHub")
                else:
                    self.logger.success("Доступ к GitHub подтвержден")
            except GitHubNotAuthenticatedError:
                if self.interactive or self.dry_run:
                    print("\n" + "="*60)
                    print("GitHub CLI не авторизован")
                    print("="*60)
                    print("\nВарианты:")
                    print("1. Авторизоваться сейчас")
                    print("2. Продолжить без GitHub (локальный режим)")
                    print("\nВыберите вариант (1/2): ", end='')
                    
                    response = InputValidator.sanitize_input(input())
                    try:
                        response = InputValidator.validate_menu_choice(response, ['1', '2'])
                    except ValueError as e:
                        self.logger.warning(f"Invalid input: {e}")
                        response = '2'  # Default to local mode
                    
                    if response == '1':
                        # Try to re-authenticate by reinitializing GitHub client
                        self.github_client = GitHubClient(self.logger, self.dry_run)
                        if not self.github_client.check_repository_access():
                            raise GitHubError("Нет доступа к репозиторию GitHub")
                        self.logger.success("Доступ к GitHub подтвержден")
                    else:
                        # Continue without GitHub
                        self.logger.info("Продолжаем без GitHub (локальный режим)")
                        print("\nПродолжаем в локальном режиме (без GitHub интеграции).")
                        self.local_mode = True
                else:
                    raise
        else:
            self.logger.info("Работа в локальном режиме (без GitHub)")
        
        # Check repository cleanliness
        self._check_repository_cleanliness()
    
    def _check_repository_cleanliness(self) -> None:
        """Check if repository has uncommitted changes in sensitive files."""
        self.logger.step("Проверка чистоты репозитория")
        
        status = self.git_ops.get_status()
        
        # Check for uncommitted changes
        if status.has_changes:
            has_sensitive = False
            
            for file in status.untracked_files + status.staged_files + status.unstaged_files:
                if any(sensitive in file for sensitive in self.sensitive_files):
                    has_sensitive = True
                    break
            
            if has_sensitive:
                self.logger.warning(
                    "Обнаружены незакоммиченные изменения в чувствительных файлах.\n"
                    "Убедитесь, что .gitignore, .env и другие конфигурационные файлы в порядке."
                )
                
                if not self.interactive:
                    self.logger.info("Используйте --interactive для подтверждения работы с изменениями.")
                    return
            
            if self.interactive:
                print("\nОбнаружены незакоммиченные изменения. Продолжить? (Y/n): ", end='')
                response = InputValidator.sanitize_input(input())
                try:
                    if not InputValidator.validate_yes_no(response):
                        raise GitOperationError("Отменено пользователем")
                except ValueError as e:
                    self.logger.warning(f"Invalid input: {e}")
                    raise GitOperationError("Отменено пользователем из-за неверного ввода")
    
    def _check_existing_workflow(self) -> Optional[str]:
        """
        Check for existing workflow (idempotency).
        
        Returns:
            Existing branch name if found, None otherwise.
        """
        self.logger.step("Проверка существующего workflow")
        
        # Get current branch
        current_branch = self.git_ops.get_current_branch()
        self.logger.info(f"Текущая ветка: {current_branch}")
        
        # Check if we're on a feature branch (not main/master/develop)
        main_branches = ['main', 'master', 'develop']
        if current_branch not in main_branches:
            # Check if there's a PR for this branch
            pr_state = self.github_client.get_pull_request_state(current_branch)
            
            if pr_state != PRState.NOT_FOUND:
                self.logger.info(f"Обнаружен существующий PR для ветки {current_branch}")
                
                # If PR is merged, delete the branch
                if pr_state == PRState.MERGED:
                    self.logger.info(f"PR для ветки {current_branch} был слит. Удаляем ветку.")
                    try:
                        # Switch to main branch first (cannot delete current branch)
                        self.git_ops.checkout_branch('main')
                        self.logger.info("Переключились на ветку main")
                        
                        # Update main branch
                        try:
                            self.git_ops.pull_rebase()
                            self.logger.info("Ветка main обновлена")
                        except GitOperationError as e:
                            self.logger.warning(f"Не удалось обновить main: {e}")
                        
                        # Delete local branch
                        self.git_ops.delete_local_branch(current_branch, force=False)
                        self.logger.success(f"Ветка {current_branch} удалена локально")
                        
                        # Delete remote branch
                        try:
                            self.git_ops.delete_remote_branch(current_branch)
                            self.logger.success(f"Удалена удалённая ветка origin/{current_branch}")
                        except GitOperationError as e:
                            self.logger.warning(f"Не удалось удалить удалённую ветку: {e}")
                        
                        # Return None to trigger new workflow
                        return None
                    except GitOperationError as e:
                        self.logger.warning(f"Не удалось удалить ветку {current_branch}: {e}")
                        # Still return None to trigger new workflow even if deletion failed
                        return None
                
                return current_branch
        
        return None
    
    def _continue_existing_workflow(self, branch_name: str) -> bool:
        """
        Continue existing workflow.
        
        Args:
            branch_name: Existing branch name.
            
        Returns:
            True if workflow completed successfully, False otherwise.
        """
        self.logger.step("Продолжение существующего workflow")
        
        # Check for changes
        status = self.git_ops.get_status()
        
        if not status.has_changes:
            self.logger.info("Нет новых изменений")
            # No changes to commit, workflow complete
            return True
        
        self.logger.info("Обнаружены новые изменения")
        
        # Analyze changes
        analysis = self.change_analyzer.analyze_changes()
        
        # Generate commit message
        commit_message = self.commit_generator.generate_commit_message(
            analysis,
            custom_message=self.custom_commit_message
        )
        
        # Check if PR exists for this branch
        existing_pr = self.github_client.get_pull_request_by_branch(branch_name)
        
        # Check CI status if PR exists
        if existing_pr:
            ci_status = self.github_client.get_pr_checks(branch_name)
            if ci_status['status'] == 'failure':
                self.logger.warning(f"CI checks failed для PR #{ci_status.get('pr_number', 'unknown')}")
                if self.interactive:
                    print("\nCI checks failed. Продолжить коммит? (Y/n): ", end='')
                    response = InputValidator.sanitize_input(input())
                    try:
                        if not InputValidator.validate_yes_no(response):
                            raise GitOperationError("Отменено пользователем из-за failed CI")
                    except ValueError as e:
                        self.logger.warning(f"Invalid input: {e}")
                        raise GitOperationError("Отменено пользователем из-за неверного ввода")
                else:
                    self.logger.info("Используйте --interactive для подтверждения коммита с failed CI")
            elif ci_status['status'] == 'pending':
                self.logger.info(f"CI checks в прогрессе для PR #{ci_status.get('pr_number', 'unknown')}")
            elif ci_status['status'] == 'success':
                self.logger.success(f"CI checks пройдены для PR #{ci_status.get('pr_number', 'unknown')}")
        
        # Run pre-commit hooks
        self._run_pre_commit_hooks()
        
        # Check if we should amend instead of creating new commit
        if not self.amend and not existing_pr:
            # Only check for existing PR on new workflow
            should_amend = self._check_should_amend()
            if should_amend:
                self.amend = True
        
        # Stage and commit
        self._commit_changes(commit_message, amend=self.amend)
        
        # Push
        self.logger.info("Push изменений...")
        self.git_ops.push(branch_name, set_upstream=False)
        
        # Ask about PR creation if not already exists
        if not existing_pr:
            if self.create_pr or self._ask_create_pr():
                self._create_pull_request(branch_name, commit_message, analysis)
            else:
                self.logger.info("Pull Request не создан. Вы можете создать его позже вручную.")
        
        self.logger.success("Workflow успешно завершен. Ветка готова к работе.")
        return True
    
    def _start_new_workflow(self) -> bool:
        """
        Start new workflow.
        
        Returns:
            True if workflow completed successfully, False otherwise.
        """
        self.logger.step("Запуск нового workflow")
        
        # Check repository state
        self._check_repository_state()
        
        # Sync with remote before creating branch (only if not in local mode)
        if not self.local_mode:
            self._sync_with_remote()
        
        # Analyze changes
        analysis = self.change_analyzer.analyze_changes()
        
        if not analysis.added_files and not analysis.modified_files and not analysis.deleted_files:
            self.logger.info("Нет изменений для коммита. Рабочая директория чиста.")
            print("\nНет изменений для коммита. Рабочая директория чиста.")
            return True  # Not an error, just nothing to do
        
        self.logger.success("Изменения обнаружены")
        
        # Generate branch name
        branch_name = self.branch_namer.generate_branch_name(
            analysis,
            custom_name=self.custom_branch_name
        )
        
        # Generate commit message
        commit_message = self.commit_generator.generate_commit_message(
            analysis,
            custom_message=self.custom_commit_message
        )
        
        # Show dry-run summary if in dry-run mode
        if self.dry_run:
            self._show_dry_run_summary(branch_name, commit_message, analysis)
            return True
        
        # Interactive confirmation if enabled
        if self.interactive:
            if not self._confirm_actions(branch_name, commit_message, analysis):
                self.logger.info("Отменено пользователем")
                return False
        
        # Create and checkout branch
        self._create_and_checkout_branch(branch_name)
        
        # Stage and commit
        self._commit_changes(commit_message)
        
        # Push and PR (only if not in local mode)
        if not self.local_mode:
            # Push
            self.logger.info("Push изменений...")
            self.git_ops.push(branch_name)
            
            # Ask about PR creation
            if self.create_pr or self._ask_create_pr():
                self._create_pull_request(branch_name, commit_message, analysis)
            else:
                self.logger.info("Pull Request не создан. Вы можете создать его позже вручную.")
            
            self.logger.success("Workflow успешно завершен. Ветка готова к работе.")
            self.logger.info("Примечание: Для автоматического удаления веток после мержа используйте GitHub Action (см. .github/workflows/cleanup-branches.yml)")
        else:
            self.logger.success("Workflow успешно завершен в локальном режиме.")
            print(f"\nВетка '{branch_name}' создана и изменения закоммичены локально.")
            print("Для публикации на GitHub:")
            print(f"  git push -u origin {branch_name}")
        
        return True
    
    def _ask_create_pr(self) -> bool:
        """
        Ask user if they want to create a Pull Request.
        
        Returns:
            True if user wants to create PR, False otherwise.
        """
        print("\nСоздать Pull Request? (Y/n): ", end='')
        response = InputValidator.sanitize_input(input())
        try:
            return InputValidator.validate_yes_no(response)
        except ValueError as e:
            self.logger.warning(f"Invalid input: {e}")
            return False
    
    def _check_should_amend(self) -> bool:
        """
        Check if the last commit has not been pushed yet and ask user if they want to amend.
        
        Returns:
            True if user wants to amend, False otherwise.
        """
        try:
            # Check if HEAD is ahead of origin
            result = self.git_ops._run_git_command(['git', 'rev-parse', '@{u}'], check=False, return_result=True)
            
            if result.returncode != 0:
                # No upstream set, meaning HEAD is not pushed
                self.logger.info("Последний коммит еще не опубликован")
                
                if self.interactive:
                    print("\nПоследний коммит еще не опубликован.")
                    print("Использовать git commit --amend вместо нового коммита? (Y/n): ", end='')
                    response = InputValidator.sanitize_input(input())
                    try:
                        return InputValidator.validate_yes_no(response)
                    except ValueError as e:
                        self.logger.warning(f"Invalid input: {e}")
                        return False
                else:
                    self.logger.info("Используйте --interactive для подтверждения amend")
                    return False
            
            # Check if HEAD is ahead of upstream
            ahead_result = self.git_ops._run_git_command(['git', 'rev-list', '--count', '@{u}..HEAD'], check=False, return_result=True)
            
            if ahead_result.returncode == 0:
                ahead_count = int(ahead_result.stdout.strip())
                if ahead_count > 0:
                    self.logger.info(f"Есть {ahead_count} непубликованных коммит(ов)")
                    
                    if self.interactive:
                        print("\nПоследний коммит еще не опубликован.")
                        print("Использовать git commit --amend вместо нового коммита? (Y/n): ", end='')
                        response = InputValidator.sanitize_input(input())
                        try:
                            return InputValidator.validate_yes_no(response)
                        except ValueError as e:
                            self.logger.warning(f"Invalid input: {e}")
                            return False
                    else:
                        self.logger.info("Используйте --interactive для подтверждения amend")
                        return False
            
            return False
            
        except (GitOperationError, ValueError, AttributeError) as e:
            self.logger.warning(f"Не удалось проверить статус публикации: {e}")
            return False
    
    def _check_repository_state(self) -> None:
        """Check repository state for conflicts and unfinished operations."""
        self.logger.step("Проверка состояния репозитория")
        
        status = self.git_ops.get_status()
        
        # Check for conflicts
        if status.has_conflicts:
            raise MergeConflictError()
        
        # Check for unfinished operations
        if status.unfinished_operation:
            raise UnfinishedGitOperationError(status.unfinished_operation)
        
        self.logger.success("Состояние репозитория корректно")
    
    def _sync_with_remote(self) -> None:
        """Sync with remote before creating branch and check if main == origin/main."""
        self.logger.step("Синхронизация с remote")
        
        try:
            self.git_ops._run_git_command(['git', 'fetch', 'origin'])
            self.logger.success("Git fetch выполнен")
            
            # Get current branch
            current_branch = self.git_ops.get_current_branch()
            
            # Check if current branch is in sync with remote
            self._check_branch_sync(current_branch)
            
            # Pull with rebase to avoid merge commits
            self.git_ops._run_git_command(['git', 'pull', '--rebase', 'origin', current_branch])
            self.logger.success("Git pull --rebase выполнен")
            
        except GitOperationError as e:
            self.logger.warning(f"Не удалось синхронизироваться с remote: {e}")
            self.logger.info("Продолжаем без синхронизации. Будьте внимательны при работе.")
    
    def _check_branch_sync(self, branch_name: str) -> None:
        """
        Check if local branch is in sync with remote branch.
        
        Args:
            branch_name: Branch name to check.
        """
        try:
            # Get local HEAD SHA
            local_sha = self.git_ops._run_git_command(['git', 'rev-parse', branch_name])
            
            # Get remote branch SHA
            remote_result = self.git_ops._run_git_command(
                ['git', 'rev-parse', f'origin/{branch_name}'],
                check=False,
                return_result=True
            )
            
            if remote_result.returncode != 0:
                # Remote branch doesn't exist
                self.logger.info(f"Remote branch origin/{branch_name} не существует")
                return
            
            remote_sha = remote_result.stdout.strip()
            
            # Compare SHAs
            if local_sha != remote_sha:
                self.logger.warning(f"Локальная ветка {branch_name} не синхронизирована с origin/{branch_name}")
                
                if self.interactive:
                    print(f"\nЛокальная ветка {branch_name} не синхронизирована с origin/{branch_name}")
                    print("Варианты:")
                    print("1. Продолжить без синхронизации (может привести к конфликтам)")
                    print("2. Выполнить git pull --rebase (рекомендуется)")
                    print("\nВыберите вариант (1/2): ", end='')
                    response = InputValidator.sanitize_input(input())
                    try:
                        response = InputValidator.validate_menu_choice(response, ['1', '2'])
                    except ValueError as e:
                        self.logger.warning(f"Invalid input: {e}")
                        response = '1'  # Default to continue without sync
                    
                    if response == '2':
                        self.logger.info("Выполняем git pull --rebase...")
                        self.git_ops._run_git_command(['git', 'pull', '--rebase', 'origin', branch_name])
                        self.logger.success("Синхронизация выполнена")
                    else:
                        self.logger.warning("Продолжаем без синхронизации")
                else:
                    self.logger.info("Используйте --interactive для выбора варианта синхронизации")
            else:
                self.logger.success(f"Ветка {branch_name} синхронизирована с origin/{branch_name}")
                
        except (GitOperationError, ValueError, AttributeError) as e:
            self.logger.warning(f"Не удалось проверить синхронизацию ветки: {e}")
    
    def _create_and_checkout_branch(self, branch_name: str) -> None:
        """
        Create and checkout new branch.
        
        Args:
            branch_name: Branch name to create.
        """
        self.logger.step("Создание ветки")
        
        # Save current branch
        original_branch = self.git_ops.get_current_branch()
        self.logger.info(f"Исходная ветка: {original_branch}")
        
        # Create and checkout branch
        self.git_ops.create_and_checkout_branch(branch_name)
    
    def _run_pre_commit_hooks(self) -> None:
        """Run pre-commit hooks before commit."""
        if not self.pre_commit_hooks.commands:
            self.logger.info("No pre-commit hooks configured")
            return
        
        self.logger.step("Running pre-commit hooks")
        
        all_passed, results = self.pre_commit_hooks.run_all()
        
        if not all_passed:
            self.logger.failure("Pre-commit hooks failed")
            
            # Show failed hooks
            for result in results:
                if not result.success:
                    self.logger.error(f"Failed: {result.command}")
                    if result.error:
                        self.logger.error(f"Error: {result.error}")
            
            if self.interactive:
                print("\nPre-commit hooks failed. Продолжить коммит? (Y/n): ", end='')
                response = InputValidator.sanitize_input(input())
                try:
                    if not InputValidator.validate_yes_no(response):
                        raise GitOperationError("Отменено пользователем из-за failed pre-commit hooks")
                except ValueError as e:
                    self.logger.warning(f"Invalid input: {e}")
                    raise GitOperationError("Отменено пользователем из-за неверного ввода")
            else:
                self.logger.info("Используйте --interactive для подтверждения коммита с failed hooks")
        else:
            self.logger.success("All pre-commit hooks passed")
    
    def _commit_changes(self, commit_message: str, amend: bool = False) -> None:
        """
        Stage and commit changes.
        Only adds tracked files, asks confirmation for new files.
        
        Args:
            commit_message: Commit message to use.
            amend: If True, amend last commit instead of creating new one.
        """
        self.logger.step("Индексация и коммит изменений")
        
        # Get status to check for new files
        status = self.git_ops.get_status()
        
        # Add only tracked files (modified) - combine staged and unstaged
        modified_files = status.staged_files + status.unstaged_files
        if modified_files:
            self.logger.debug(f"Attempting to add files: {modified_files}")
            self.logger.debug(f"Staged files: {status.staged_files}")
            self.logger.debug(f"Unstaged files: {status.unstaged_files}")
            self.git_ops.add_files(modified_files)
            self.logger.info(f"Added {len(modified_files)} modified file(s)")
        
        # Ask about new files
        if status.untracked_files:
            self.logger.info(f"Found {len(status.untracked_files)} untracked file(s)")
            
            # Filter out sensitive files
            safe_new_files = [f for f in status.untracked_files 
                            if not any(sensitive in f for sensitive in self.sensitive_files)]
            
            if safe_new_files:
                if self.interactive:
                    print(f"\nНовые файлы для добавления:")
                    for f in safe_new_files:
                        print(f"  - {f}")
                    print("\nДобавить эти файлы? (Y/n): ", end='')
                    response = InputValidator.sanitize_input(input())
                    try:
                        if InputValidator.validate_yes_no(response):
                            self.git_ops.add_files(safe_new_files)
                            self.logger.info(f"Added {len(safe_new_files)} new file(s)")
                        else:
                            self.logger.info("Новые файлы не добавлены")
                    except ValueError as e:
                        self.logger.warning(f"Invalid input: {e}")
                        self.logger.info("Новые файлы не добавлены")
                else:
                    self.logger.info("Новые файлы не добавлены (используйте --interactive для подтверждения)")
        
        # Check if there are any staged changes before committing
        status_after = self.git_ops.get_status()
        if not status_after.staged_files and not status_after.has_changes:
            self.logger.info("Нет изменений для коммита. Пропускаем коммит.")
            return
        
        # Commit
        self.git_ops.commit(commit_message, amend=amend)
    
    def _create_pull_request(
        self,
        branch_name: str,
        commit_message: str,
        analysis
    ) -> None:
        """
        Create Pull Request.
        
        Args:
            branch_name: Branch name for PR.
            commit_message: Commit message (used as base for PR title).
            analysis: Change analysis for PR body.
        """
        self.logger.step("Создание Pull Request")
        
        # Check if PR already exists
        existing_pr = self.github_client.get_pull_request_by_branch(branch_name)
        if existing_pr:
            self.logger.info(f"PR уже существует: #{existing_pr.number}")
            return
        
        # Generate PR title and body
        pr_title = commit_message.split(': ', 1)[1] if ': ' in commit_message else commit_message
        pr_body = self._generate_pr_body(analysis)
        
        # Get default branch
        base_branch = self.github_client.get_default_branch()
        
        # Create PR
        self.github_client.create_pull_request(
            title=pr_title,
            body=pr_body,
            head_branch=branch_name,
            base_branch=base_branch
        )
    
    def _generate_pr_body(self, analysis) -> str:
        """
        Generate PR body from change analysis using standard template.
        
        Template:
        - Summary
        - Changes
        - Testing
        - Checklist
        
        Args:
            analysis: ChangeAnalysis object.
            
        Returns:
            PR body string.
        """
        lines = []
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"This PR implements changes of type `{analysis.likely_type}`.")
        lines.append("")
        
        # Changes
        lines.append("## Changes")
        lines.append("")
        
        if analysis.added_files:
            lines.append("### Added Files")
            for f in analysis.added_files:
                lines.append(f"- {f}")
            lines.append("")
        
        if analysis.modified_files:
            lines.append("### Modified Files")
            for f in analysis.modified_files:
                lines.append(f"- {f}")
            lines.append("")
        
        if analysis.deleted_files:
            lines.append("### Deleted Files")
            for f in analysis.deleted_files:
                lines.append(f"- {f}")
            lines.append("")
        
        # Testing
        lines.append("## Testing")
        lines.append("")
        lines.append("- [ ] Manual testing completed")
        lines.append("- [ ] Automated tests passed")
        lines.append("")
        
        # Checklist
        lines.append("## Checklist")
        lines.append("")
        lines.append("- [ ] Tests passed")
        lines.append("- [ ] Linter passed")
        lines.append("- [ ] Documentation updated")
        lines.append("")
        
        return "\n".join(lines)
    
    def _show_dry_run_summary(
        self,
        branch_name: str,
        commit_message: str,
        analysis
    ) -> None:
        """
        Show dry-run summary.
        
        Args:
            branch_name: Proposed branch name.
            commit_message: Proposed commit message.
            analysis: Change analysis.
        """
        self.logger.step("DRY RUN - Сводка действий")
        
        print("\n" + "="*60)
        print("DRY RUN MODE - Никаких изменений не будет выполнено")
        print("="*60 + "\n")
        
        print(f"Предлагаемое название ветки: {branch_name}")
        print(f"Предлагаемое сообщение коммита: {commit_message}")
        print(f"\nТип изменений: {analysis.likely_type}")
        print(f"Сводка diff: {analysis.diff_summary}")
        
        print("\nФайлы:")
        if analysis.added_files:
            print(f"  Добавлено ({len(analysis.added_files)}):")
            for f in analysis.added_files:
                print(f"    + {f}")
        if analysis.modified_files:
            print(f"  Изменено ({len(analysis.modified_files)}):")
            for f in analysis.modified_files:
                print(f"    ~ {f}")
        if analysis.deleted_files:
            print(f"  Удалено ({len(analysis.deleted_files)}):")
            for f in analysis.deleted_files:
                print(f"    - {f}")
        
        print("\nДействия, которые будут выполнены:")
        print("  1. Создание ветки: " + branch_name)
        print("  2. Переключение на ветку")
        print("  3. Индексация всех изменений")
        print("  4. Создание коммита: " + commit_message)
        print("  5. Push ветки в remote")
        print("  6. Создание Pull Request")
        print("  7. Мониторинг Pull Request до завершения")
        print("\n" + "="*60 + "\n")
    
    def _confirm_actions(
        self,
        branch_name: str,
        commit_message: str,
        analysis
    ) -> bool:
        """
        Prompt user for confirmation.
        
        Args:
            branch_name: Proposed branch name.
            commit_message: Proposed commit message.
            analysis: Change analysis.
            
        Returns:
            True if user confirms, False otherwise.
        """
        print("\n" + "="*60)
        print("Подтверждение действий")
        print("="*60 + "\n")
        
        print(f"Название ветки: {branch_name}")
        print(f"Сообщение коммита: {commit_message}")
        print(f"\nТип изменений: {analysis.likely_type}")
        print(f"Изменено файлов: {len(analysis.added_files) + len(analysis.modified_files) + len(analysis.deleted_files)}")
        
        print("\nПродолжить? (y/n): ", end='')
        
        response = InputValidator.sanitize_input(input())
        try:
            return InputValidator.validate_yes_no(response)
        except ValueError as e:
            self.logger.warning(f"Invalid input: {e}")
            return False
