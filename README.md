# Git Automation Script

Production-ready скрипт автоматизации работы с Git и GitHub, который упрощает процесс подготовки изменений к ревью.

## Возможности

- **Автоматический анализ изменений**: Определяет тип изменений (feat, fix, refactor, chore, docs и т.д.)
- **Генерация названия ветки**: Создает осмысленные названия веток по Git Flow конвенции (до 40 символов)
- **Conventional Commits**: Автоматическая генерация сообщений коммитов по стандарту (на английском)
- **Создание Pull Request**: Опциональное создание PR с описанием изменений
- **Проверка CI статуса**: Проверка CI/CD перед коммитом на существующей ветке
- **Идемпотентность**: Возможность повторного запуска на существующей ветке
- **Dry-run режим**: Предпросмотр действий без выполнения
- **Интерактивный режим**: Подтверждение действий пользователем
- **Подробное логирование**: Полное логирование всех операций
- **Проверка чистоты репозитория**: Проверка незакоммиченных изменений в чувствительных файлах
- **Синхронизация с remote**: Автоматический fetch и pull --rebase перед созданием ветки
- **Автоматическое удаление веток**: Через GitHub Action после мержа

## Требования

- Python 3.8+
- Git
- GitHub CLI (gh)
- Доступ к GitHub репозиторию

## Установка

### 1. Клонирование или установка скрипта

Скрипт находится в директории `scripts/git-automation/`.

### 2. Установка GitHub CLI

**macOS:**
```bash
brew install gh
```

**Linux:**
```bash
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

**Windows:**
Скачайте установщик с [https://cli.github.com/](https://cli.github.com/)

### 3. Авторизация в GitHub

```bash
gh auth login
```

Следуйте инструкциям для авторизации.

### 4. Зависимости Python

Скрипт использует только стандартную библиотеку Python. Дополнительные зависимости не требуются.

## Использование

### Базовый запуск

Автоматический режим без подтверждений:

```bash
cd /path/to/your/repository
python /path/to/scripts/git-automation/main.py
```

### Dry-run режим

Показать действия без выполнения:

```bash
python /path/to/scripts/git-automation/main.py --dry-run
```

### Интерактивный режим

С подтверждениями перед каждым действием:

```bash
python /path/to/scripts/git-automation/main.py --interactive
```

### Кастомное название ветки

```bash
python /path/to/scripts/git-automation/main.py --branch-name feat/my-custom-feature
```

### Кастомное сообщение коммита

```bash
python /path/to/scripts/git-automation/main.py --commit-message "feat: add new feature"
```

### Автоматическое создание PR

```bash
python /path/to/scripts/git-automation/main.py --create-pr
```

### Amend последнего коммита

```bash
python /path/to/scripts/git-automation/main.py --amend
```

### Cleanup после мержа

```bash
python /path/to/scripts/git-automation/cleanup.py
```

### Подробное логирование

```bash
python /path/to/scripts/git-automation/main.py --verbose
```

### Сохранение логов в файл

```bash
python /path/to/scripts/git-automation/main.py --log-dir ./logs
```

## Workflow

Скрипт выполняет следующие шаги:

1. **Проверка репозитория**
   - Проверка, что директория является Git-репозиторием
   - Проверка наличия remote
   - Проверка доступа к GitHub
   - Проверка чистоты репозитория (незакоммиченные изменения в чувствительных файлах)

2. **Синхронизация с remote**
   - Git fetch
   - Git pull --rebase (для избежания merge commits)

3. **Анализ изменений**
   - Определение измененных, новых, удаленных файлов
   - Анализ diff для определения типа изменений (включая контент изменений)

4. **Проверка существующего workflow** (идемпотентность)
   - Если на feature-ветке с существующим PR — продолжить работу
   - Проверка CI статуса перед коммитом
   - Если на основной ветке — создать новый workflow

5. **Генерация названия ветки**
   - Автоматическая генерация на основе анализа изменений
   - Следование Git Flow конвенции (до 40 символов)
   - Формат: `тип/описание` (например, `feat/catalog-search`)

6. **Создание ветки**
   - Создание новой ветки
   - Переключение на нее

7. **Индексация и коммит**
   - Добавление изменений в индекс
   - Создание коммита с Conventional Commits сообщением (на английском)

8. **Push изменений**
   - Push ветки в remote
   - Установка upstream

9. **Создание Pull Request** (опционально)
   - Запрос подтверждения у пользователя
   - Автоматическое создание PR с описанием изменений
   - Или `--create-pr` для автоматического создания

10. **Завершение**
    - Скрипт завершает работу после push
    - GitHub Action автоматически удаляет ветку после мержа

## Обработка ошибок

Скрипт обрабатывает следующие ситуации:

- Текущая папка не является Git-репозиторием
- Отсутствует remote или origin
- GitHub CLI не установлен
- Пользователь не авторизован в GitHub
- Отсутствует доступ к репозиторию
- Ошибки сети
- Merge-конфликты
- Незавершенные операции Git (merge, rebase, cherry-pick)
- Отсутствие изменений для коммита
- Ошибки при push
- Невозможность удалить ветку
- Невозможность переключиться на основную ветку

Во всех случаях выводятся понятные сообщения с рекомендациями по устранению.

## Автоматическое удаление веток

Для автоматического удаления веток после мержа используется GitHub Action `.github/workflows/cleanup-branches.yml`.

Этот Action:
- Запускается при закрытии Pull Request
- Проверяет, что PR был объединен (merged)
- Удаляет соответствующую ветку в remote
- Не требует запущенного скрипта или фоновых процессов

## Статусы Pull Request

### Open
PR открыт. Разработчик может продолжать добавлять коммиты и выполнять push. Скрипт проверяет CI статус перед новым коммитом.

### Merged
PR успешно объединен. GitHub Action автоматически удаляет ветку в remote.

### Closed
PR закрыт без мержа. Ветка не удаляется автоматически. Разработчик может:
- Оставить ветку для дальнейшей работы
- Удалить локальную ветку вручную
- Удалить локальную и удаленную ветки вручную

## Архитектура

Скрипт построен по принципам SOLID и Clean Code:

```
git-automation/
├── src/
│   ├── __init__.py           # Пакет
│   ├── logger.py             # Централизованное логирование
│   ├── error_handler.py      # Обработка ошибок
│   ├── git_operations.py     # Операции Git
│   ├── github_client.py      # GitHub CLI wrapper
│   ├── change_analyzer.py   # Анализ изменений
│   ├── branch_namer.py       # Генерация названий веток
│   ├── commit_generator.py   # Генерация сообщений коммитов
│   ├── pr_monitor.py         # Мониторинг PR
│   └── orchestrator.py       # Координация workflow
├── config/
│   └── default_config.yaml   # Конфигурация
├── main.py                   # Точка входа
└── README.md                 # Документация
```

## Конфигурация

Конфигурация находится в `config/default_config.yaml`:

```yaml
github:
  pr_poll_interval: 60  # Интервал опроса PR (секунды)
  draft_prs: false      # Создавать черновики PR

git:
  main_branches:        # Основные ветки для обнаружения
    - main
    - master
    - develop

branch_naming:
  max_length: 100       # Максимальная длина названия ветки
  reserved_names:       # Зарезервированные названия
    - head
    - main
    - master
    - develop

commit:
  max_description_length: 50  # Макс. длина описания
  language: ru               # Язык сообщений

logging:
  level: INFO          # Уровень логирования
  format: "..."        # Формат логов
```

## Примеры

### Пример 1: Добавление новой функции

```bash
# Вносим изменения
echo "print('Hello')" > new_feature.py

# Запускаем скрипт
python /path/to/scripts/git-automation/main.py

# Результат:
# - Ветка: feat/add-feature
# - Коммит: feat: add feature
# - Запрос на создание PR
```

### Пример 2: Исправление ошибки

```bash
# Вносим исправление
sed -i 's/bug/fix' file.py

# Запускаем скрипт
python /path/to/scripts/git-automation/main.py

# Результат:
# - Ветка: fix/file-fix
# - Коммит: fix: fix bug
# - Запрос на создание PR
```

### Пример 3: Продолжение работы на существующей ветке

```bash
# На ветке feat/add-feature с открытым PR
# Вносим дополнительные изменения
echo "more code" >> file.py

# Запускаем скрипт
python /path/to/scripts/git-automation/main.py

# Результат:
# - Новая ветка не создается
# - Проверка CI статуса
# - Изменения коммитятся в существующую ветку
# - Push выполняется
```

## Troubleshooting

### GitHub CLI не найден

```
Ошибка: GitHub CLI (gh) не установлен.
Решение: brew install gh (macOS) или скачайте с https://cli.github.com/
```

### Не авторизован в GitHub

```
Ошибка: Вы не авторизованы в GitHub.
Решение: gh auth login
```

### Нет изменений

```
Ошибка: Нет изменений для коммита.
Решение: Внесите изменения в файлы перед запуском скрипта.
```

### Merge конфликты

```
Ошибка: Обнаружены merge-конфликты.
Решение: Разрешите конфликты вручную: git status
```

## Безопасность

- **Dry-run режим**: Всегда используйте `--dry-run` перед первым запуском
- **Интерактивный режим**: Используйте `--interactive` для подтверждения действий
- **Логирование**: Все действия логируются для аудита
- **Безопасное удаление**: Ветки не удаляются при закрытии PR без мержа

## Лицензия

Скрипт является частью проекта Hyperline и используется внутри организации.

## Поддержка

При возникновении проблем:
1. Проверьте логи (используйте `--verbose` и `--log-dir`)
2. Убедитесь, что GitHub CLI установлен и авторизован
3. Проверьте доступ к репозиторию GitHub
4. Используйте `--dry-run` для диагностики
