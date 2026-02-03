# Module: `git_utils`

## Class: `GitError`

```python
Исключение для ошибок Git
```

## Function: `execute_git_command`

```python
Выполнить git команду

Args:
    command: Список аргументов команды (первый элемент - 'git')
    working_dir: Рабочая директория (если None - текущая)
    timeout: Таймаут выполнения (секунды)

Returns:
    Кортеж (success, stdout, stderr)
```

## Function: `get_current_branch`

```python
Получить текущую ветку

Args:
    working_dir: Рабочая директория

Returns:
    Название текущей ветки или None при ошибке
```

## Function: `is_branch_allowed_for_auto_push`

```python
Проверить, разрешена ли автоматическая отправка для текущей ветки

Args:
    branch: Название ветки (если None - получить текущую)
    allowed_branches: Список разрешенных веток (если None - только 'smart')
    working_dir: Рабочая директория

Returns:
    True если push разрешен для данной ветки
```

## Function: `get_last_commit_info`

```python
Получить информацию о последнем коммите

Args:
    working_dir: Рабочая директория

Returns:
    Словарь с информацией о коммите или None при ошибке
```

## Function: `check_commit_exists`

```python
Проверить существование коммита

Args:
    commit_hash: Hash коммита (полный или короткий)
    working_dir: Рабочая директория

Returns:
    True если коммит существует
```

## Function: `check_uncommitted_changes`

```python
Проверить наличие незакоммиченных изменений

Args:
    working_dir: Рабочая директория

Returns:
    True если есть незакоммиченные изменения
```

## Function: `check_unpushed_commits`

```python
Проверить наличие неотправленных коммитов

Args:
    working_dir: Рабочая директория
    branch: Название ветки (если None - текущая)

Returns:
    True если есть неотправленные коммиты
```

## Function: `push_to_remote`

```python
Отправить коммиты в удаленный репозиторий

Args:
    branch: Название ветки (если None - текущая)
    remote: Название remote (по умолчанию 'origin')
    working_dir: Рабочая директория
    timeout: Таймаут выполнения (секунды)

Returns:
    Кортеж (success, stdout, stderr)
```

## Function: `auto_push_after_commit`

```python
Автоматически отправить коммиты после успешного коммита

Проверяет:
1. Разрешение push для текущей ветки
2. Существование последнего коммита
3. Наличие неотправленных коммитов
4. Выполняет push

Args:
    working_dir: Рабочая директория
    remote: Название remote
    timeout: Таймаут выполнения push
    allowed_branches: Список разрешенных веток для push (если None - только 'smart')

Returns:
    Словарь с результатом операции
```
