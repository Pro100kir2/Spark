#!/usr/bin/env python3
"""
Dependency installer module for Git automation script.
Handles automatic installation of external dependencies like GitHub CLI.
"""

import subprocess
import platform
import sys
import threading
import time
import itertools
from typing import Optional, Tuple

from .logger import Logger
from .input_validator import InputValidator


class DependencyInstaller:
    """Handles installation of external dependencies."""
    
    def __init__(self, logger: Logger):
        """
        Initialize dependency installer.
        
        Args:
            logger: Logger instance.
        """
        self.logger = logger
        self.validator = InputValidator
        self._stop_progress = False
    
    def _show_progress(self, message: str, duration: Optional[float] = None) -> None:
        """
        Show an animated progress bar.
        
        Args:
            message: Message to display with progress bar.
            duration: If provided, stop after this many seconds.
        """
        animation = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        
        def animate():
            while not self._stop_progress:
                print(f"\r{message} {next(animation)}", end='', flush=True)
                time.sleep(0.1)
        
        self._stop_progress = False
        progress_thread = threading.Thread(target=animate)
        progress_thread.daemon = True
        progress_thread.start()
        
        if duration:
            time.sleep(duration)
            self._stop_progress = True
            progress_thread.join()
            print(f"\r{message} ✓", flush=True)
    
    def _stop_progress_bar(self) -> None:
        """Stop the progress bar."""
        self._stop_progress = True
        time.sleep(0.2)  # Allow thread to finish
        print("\r" + " " * 80 + "\r", end='', flush=True)  # Clear the line
    
    def detect_os(self) -> str:
        """
        Detect the current operating system.
        
        Returns:
            OS name: 'macos', 'linux', or 'windows'.
        """
        system = platform.system().lower()
        
        if system == 'darwin':
            return 'macos'
        elif system == 'linux':
            return 'linux'
        elif system == 'windows':
            return 'windows'
        else:
            return 'unknown'
    
    def check_gh_cli_installed(self) -> bool:
        """
        Check if GitHub CLI is installed.
        
        Returns:
            True if installed, False otherwise.
        """
        try:
            result = subprocess.run(
                ['gh', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def ask_install_gh_cli(self) -> bool:
        """
        Ask user if they want to install GitHub CLI.
        
        Returns:
            True if user wants to install, False otherwise.
        """
        print("\n" + "="*60)
        print("GitHub CLI (gh) не установлен")
        print("="*60)
        print("\nGitHub CLI требуется для работы с Pull Request и другими функциями GitHub.")
        print("\nУстановить GitHub CLI автоматически? (Y/n): ", end='')
        
        try:
            response = self.validator.sanitize_input(input())
            return self.validator.validate_yes_no(response)
        except (ValueError, EOFError, KeyboardInterrupt):
            return False
    
    def install_gh_cli(self) -> bool:
        """
        Install GitHub CLI based on detected OS.
        
        Returns:
            True if installation successful, False otherwise.
        """
        os_type = self.detect_os()
        
        self.logger.info(f"Обнаружена ОС: {os_type}")
        
        if os_type == 'macos':
            return self._install_gh_cli_macos()
        elif os_type == 'linux':
            return self._install_gh_cli_linux()
        elif os_type == 'windows':
            return self._install_gh_cli_windows()
        else:
            self.logger.error(f"Автоматическая установка не поддерживается для ОС: {os_type}")
            print(f"\nАвтоматическая установка не поддерживается для {os_type}.")
            print("Пожалуйста, установите GitHub CLI вручную:")
            print("  macOS: brew install gh")
            print("  Linux: Скачайте с https://cli.github.com/")
            print("  Windows: Скачайте с https://cli.github.com/")
            return False
    
    def _install_gh_cli_macos(self) -> bool:
        """
        Install GitHub CLI on macOS using Homebrew.
        
        Returns:
            True if successful, False otherwise.
        """
        self.logger.info("Проверка Homebrew...")
        
        # Check if Homebrew is installed
        try:
            brew_result = subprocess.run(
                ['brew', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if brew_result.returncode != 0:
                self.logger.error("Homebrew не установлен")
                print("\nHomebrew не установлен.")
                print("Установите Homebrew:")
                print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
                print("\nЗатем установите GitHub CLI:")
                print("  brew install gh")
                return False
        except FileNotFoundError:
            self.logger.error("Homebrew не найден")
            print("\nHomebrew не установлен.")
            print("Установите Homebrew:")
            print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            print("\nЗатем установите GitHub CLI:")
            print("  brew install gh")
            return False
        
        self.logger.success("Homebrew найден")
        print("\nУстановка GitHub CLI через Homebrew...")
        
        # Start progress bar
        self._show_progress("Установка GitHub CLI")
        
        try:
            # Install gh
            result = subprocess.run(
                ['brew', 'install', 'gh'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            # Stop progress bar
            self._stop_progress_bar()
            
            if result.returncode == 0:
                self.logger.success("GitHub CLI установлен успешно")
                print("✓ GitHub CLI установлен успешно")
                
                # Verify installation
                if self.check_gh_cli_installed():
                    print("\nТеперь нужно авторизоваться в GitHub:")
                    print("  gh auth login")
                    return True
                else:
                    print("\n⚠ GitHub CLI установлен, но не найден в PATH.")
                    print("Возможно, нужно перезапустить терминал или добавить в PATH.")
                    return False
            else:
                self.logger.error(f"Ошибка установки: {result.stderr}")
                print(f"\n✗ Ошибка установки: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self._stop_progress_bar()
            self.logger.error("Таймаут установки")
            print("\n✗ Установка заняла слишком много времени")
            return False
        except Exception as e:
            self._stop_progress_bar()
            self.logger.error(f"Неожиданная ошибка: {e}")
            print(f"\n✗ Неожиданная ошибка: {e}")
            return False
    
    def _install_gh_cli_linux(self) -> bool:
        """
        Install GitHub CLI on Linux.
        
        Returns:
            True if successful, False otherwise.
        """
        self.logger.info("Определение пакетного менеджера...")
        
        # Check for common package managers
        package_managers = [
            ('apt', ['sudo', 'apt', 'install', 'gh']),
            ('dnf', ['sudo', 'dnf', 'install', 'gh']),
            ('yum', ['sudo', 'yum', 'install', 'gh']),
            ('pacman', ['sudo', 'pacman', '-S', 'gh']),
            ('zypper', ['sudo', 'zypper', 'install', 'gh']),
        ]
        
        for pm_name, install_cmd in package_managers:
            try:
                result = subprocess.run(
                    [pm_name, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.logger.success(f"Найден пакетный менеджер: {pm_name}")
                    print(f"\nУстановка GitHub CLI через {pm_name}...")
                    print(f"Команда: {' '.join(install_cmd)}")
                    
                    # Start progress bar
                    self._show_progress("Установка GitHub CLI")
                    
                    try:
                        result = subprocess.run(
                            install_cmd,
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        
                        # Stop progress bar
                        self._stop_progress_bar()
                        
                        if result.returncode == 0:
                            self.logger.success("GitHub CLI установлен успешно")
                            print("✓ GitHub CLI установлен успешно")
                            
                            if self.check_gh_cli_installed():
                                print("\nТеперь нужно авторизоваться в GitHub:")
                                print("  gh auth login")
                                return True
                            else:
                                print("\n⚠ GitHub CLI установлен, но не найден в PATH.")
                                return False
                        else:
                            self.logger.error(f"Ошибка установки: {result.stderr}")
                            print(f"\n✗ Ошибка установки: {result.stderr}")
                            return False
                            
                    except subprocess.TimeoutExpired:
                        self._stop_progress_bar()
                        self.logger.error("Таймаут установки")
                        print("\n✗ Установка заняла слишком много времени")
                        return False
                    except Exception as e:
                        self._stop_progress_bar()
                        self.logger.error(f"Неожиданная ошибка: {e}")
                        print(f"\n✗ Неожиданная ошибка: {e}")
                        return False
                        
            except FileNotFoundError:
                continue
        
        # No package manager found
        self.logger.error("Пакетный менеджер не найден")
        print("\nНе найден поддерживаемый пакетный менеджер (apt, dnf, yum, pacman, zypper).")
        print("Установите GitHub CLI вручную:")
        print("  curl -fsSL https://cli.github.com/pkg/gnubin_keyring.pub | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg")
        print("  echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null")
        print("  sudo apt update")
        print("  sudo apt install gh")
        return False
    
    def _install_gh_cli_windows(self) -> bool:
        """
        Install GitHub CLI on Windows.
        
        Returns:
            True if successful, False otherwise.
        """
        self.logger.info("Установка на Windows")
        
        print("\nАвтоматическая установка на Windows не реализована.")
        print("Пожалуйста, установите GitHub CLI вручную:")
        print("  1. Скачайте установщик с https://cli.github.com/")
        print("  2. Запустите установщик")
        print("  3. После установки авторизуйтесь: gh auth login")
        return False
    
    def install_python_dependencies(self) -> bool:
        """
        Install Python dependencies from requirements.txt.
        
        Returns:
            True if successful, False otherwise.
        """
        self.logger.info("Проверка Python зависимостей...")
        print("\nУстановка Python зависимостей...")
        
        # Start progress bar
        self._show_progress("Установка Python зависимостей")
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Stop progress bar
            self._stop_progress_bar()
            
            if result.returncode == 0:
                self.logger.success("Python зависимости установлены")
                print("✓ Python зависимости установлены")
                return True
            else:
                self.logger.error(f"Ошибка установки: {result.stderr}")
                print(f"\n✗ Ошибка установки: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self._stop_progress_bar()
            self.logger.error("Таймаут установки")
            print("\n✗ Установка заняла слишком много времени")
            return False
        except Exception as e:
            self._stop_progress_bar()
            self.logger.error(f"Неожиданная ошибка: {e}")
            print(f"\n✗ Неожиданная ошибка: {e}")
            return False
