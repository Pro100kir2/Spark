#!/usr/bin/env python3
"""
CLI entry point for Git automation script.
Automates Git workflow including branch creation, commit, push, PR creation, and monitoring.
"""

import argparse
import sys
from pathlib import Path

from gitaut.logger import Logger
from gitaut.orchestrator import Orchestrator


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description='Автоматизация Git workflow: создание ветки, коммит, push, PR и мониторинг',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Запуск в автоматическом режиме
  gitaut
  
  # Dry-run режим (показать действия без выполнения)
  gitaut --dry-run
  
  # Интерактивный режим с подтверждениями
  gitaut --interactive
  
  # Кастомное название ветки
  gitaut --branch-name feat/my-custom-feature
  
  # Кастомное сообщение коммита
  gitaut --commit-message "feat: добавить новую функцию"
  
  # Подробное логирование
  gitaut --verbose
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Показать действия без выполнения (dry-run режим)'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Интерактивный режим с подтверждениями'
    )
    
    parser.add_argument(
        '--branch-name',
        type=str,
        help='Кастомное название ветки'
    )
    
    parser.add_argument(
        '--commit-message',
        type=str,
        help='Кастомное сообщение коммита'
    )
    
    parser.add_argument(
        '--create-pr',
        action='store_true',
        help='Автоматически создать Pull Request после push'
    )
    
    parser.add_argument(
        '--amend',
        action='store_true',
        help='Amend последний коммит вместо создания нового'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробное логирование (DEBUG уровень)'
    )
    
    parser.add_argument(
        '--log-dir',
        type=str,
        default=None,
        help='Директория для лог файлов (по умолчанию: только консоль)'
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main entry point.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Parse arguments
    args = parse_arguments()
    
    # Initialize logger
    log_dir = Path(args.log_dir) if args.log_dir else None
    logger = Logger(log_dir=log_dir, verbose=args.verbose)
    
    logger.step("Запуск Git Automation Script")
    
    # Log configuration
    logger.debug(f"Dry-run: {args.dry_run}")
    logger.debug(f"Interactive: {args.interactive}")
    logger.debug(f"Custom branch name: {args.branch_name}")
    logger.debug(f"Custom commit message: {args.commit_message}")
    
    # Initialize orchestrator
    orchestrator = Orchestrator(
        logger=logger,
        dry_run=args.dry_run,
        interactive=args.interactive,
        create_pr=args.create_pr,
        amend=args.amend,
        custom_branch_name=args.branch_name,
        custom_commit_message=args.commit_message
    )
    
    # Run workflow
    try:
        success = orchestrator.run()
        
        if success:
            logger.success("Workflow успешно завершен")
            return 0
        else:
            logger.failure("Workflow завершен с ошибкой")
            return 1
            
    except KeyboardInterrupt:
        logger.warning("Прервано пользователем")
        return 130
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
