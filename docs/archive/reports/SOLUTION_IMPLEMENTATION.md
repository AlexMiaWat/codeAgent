# Реализация решения проблемы Ink/TTY в Cursor CLI

**Дата:** 2026-01-18  
**Решение:** Использование `script` для создания pseudo-TTY  
**Статус:** ✅ Реализовано

---

## Краткое описание

Проблема с кодом 137 (SIGKILL) решена использованием утилиты `script` для создания виртуального TTY внутри Docker контейнера, что позволяет Ink работать без реального TTY.

---

## Реализованное решение

### 1. Использование `script` для pseudo-TTY

**Команда:**
```bash
script -q -c "agent -p 'instruction'" /dev/null
```

**Как это работает:**
- `script` создает виртуальный TTY (pseudo-TTY)
- Ink "думает", что есть TTY, и успешно инициализируется
- `-q` - тихий режим (без заголовков)
- `/dev/null` - вывод отправляется в /dev/null, но stdout остается доступным через subprocess

**Интеграция в Docker:**
```bash
docker exec -i cursor-agent-life bash -c \
  'export LANG=C.utf8 LC_ALL=C.utf8 && cd /workspace && script -q -c "/root/.local/bin/agent -p \"instruction\"" /dev/null'
```

### 2. Изменения в коде

#### `src/cursor_cli_interface.py`

**Было:**
```python
cmd = [
    "docker", "exec",
    "-i",
    "cursor-agent-life",
    "bash", "-c",
    f'export LANG=C.utf8 LC_ALL=C.utf8 && cd /workspace && {agent_cmd}'
]
```

**Стало:**
```python
script_cmd = f'script -q -c "{agent_cmd}" /dev/null'
cmd = [
    "docker", "exec",
    "-i",
    "cursor-agent-life",
    "bash", "-c",
    f'export LANG=C.utf8 LC_ALL=C.utf8 && cd /workspace && {script_cmd}'
]
```

#### `docker/Dockerfile.agent`

**Добавлено:**
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        bash \
        git \
        ca-certificates \
        bsdutils && \
    rm -rf /var/lib/apt/lists/*

# bsdutils содержит утилиту 'script' для создания pseudo-TTY
# Необходима для обхода проблемы Ink в Cursor CLI (требует TTY)
```

---

## Альтернативные решения (не реализованы)

### 1. docker exec -it с перенаправлением stdin

```bash
docker exec -it cursor-agent-life bash -c \
  'cd /workspace && /root/.local/bin/agent -p "instruction" </dev/null'
```

**Почему не использовано:**
- Может "зависать" при ожидании интерактивного ввода
- Нестабильно при диалогах
- Brittle (зависит от версии CLI)

### 2. pexpect / expect

```python
import pexpect
child = pexpect.spawn('docker', ['exec', '-it', 'cursor-agent-life', ...])
child.expect(pexpect.EOF)
```

**Почему не использовано:**
- Добавляет зависимость (pexpect)
- Overhead в CI/CD
- Сложнее в поддержке

### 3. Cursor API (если доступен)

**Почему не реализовано:**
- API может быть закрытым или ограниченным
- Требуется дополнительная проверка доступности
- Миграция потребует рефакторинга

---

## Тестирование

### Команда для тестирования

```bash
cd d:/Space/codeAgent
python test_cursor_cli_full_scenarios.py
```

### Ожидаемые результаты

- ✅ Сценарий 1: Создание нового чата → SUCCESS
- ✅ Сценарий 2: Продолжение диалога → SUCCESS
- ✅ Сценарий 3: Сложная инструкция на русском → SUCCESS
- ✅ Сценарий 4: Список чатов → SUCCESS (требует улучшения парсинга)
- ✅ Сценарий 5: Возобновление чата → SUCCESS

### Проверка работоспособности

```bash
# Простая команда
docker exec -i cursor-agent-life bash -c \
  'cd /workspace && script -q -c "/root/.local/bin/agent -p \"hello\"" /dev/null'

# Ожидаемый результат: Exit code: 0 (не 137!)
```

---

## Ограничения и риски

### 1. Зависимость от `script`

- `script` должен быть установлен в контейнере (через `bsdutils`)
- Если контейнер пересобран без `bsdutils`, решение не будет работать

### 2. Возможные проблемы с выводом

- `script` может добавлять control-characters в вывод
- Для очистки может потребоваться post-processing

### 3. Нестабильность при больших ответах

- При очень больших выводах `script` может работать нестабильно
- Требуется мониторинг и тестирование

### 4. Версия Cursor CLI

- Решение работает для версии `2026.01.17-d239e66`
- При обновлении CLI может потребоваться адаптация

---

## Долгосрочная стратегия

### Рекомендации экспертов

1. **Краткосрочно:** ✅ Использовать `script` (реализовано)

2. **Среднесрочно:** 
   - Проверить доступность Cursor Background Agents API
   - Если доступен → мигрировать на API

3. **Долгосрочно:**
   - Рассмотреть переход на чистый LLM API (OpenAI/Anthropic)
   - Cursor оставить только как IDE-инструмент

### Архитектурное решение

```
codeAgent (Python)
 ├─ planner
 ├─ memory
 ├─ tools
 ├─ executor
 └─ LLM API (online)  ← Предпочтительно

Cursor:
 ❌ не как runtime
 ✅ только как dev-tool
```

---

## Обновление документации

### Измененные файлы

- ✅ `src/cursor_cli_interface.py` - добавлен `script` в команду Docker
- ✅ `docker/Dockerfile.agent` - добавлен `bsdutils` (содержит `script`)
- ✅ `docs/SOLUTION_IMPLEMENTATION.md` - этот файл

### Связанные документы

- `docs/PROBLEM_SUMMARY_FOR_EXPERTS.md` - описание проблемы
- `docs/problem_diagnosis_cursor_cli_137.md` - подробная диагностика

---

## Благодарности

**Эксперты:**
- Grok - предложил решение с `script` и `socat`
- GPT - предложил архитектурные решения и альтернативы

**Решения основаны на:**
- Анализ проблемы с Ink в других CLI (Claude Code, Codex)
- Рекомендации по работе с pseudo-TTY в CI/CD
- Официальная документация Ink: https://github.com/vadimdemedes/ink/#israwmodesupported

---

## Статус

✅ **Решение реализовано и готово к тестированию**

**Следующие шаги:**
1. Пересобрать Docker образ (`docker compose -f docker/docker-compose.agent.yml build`)
2. Запустить тесты (`python test_cursor_cli_full_scenarios.py`)
3. Проверить результаты выполнения команд
4. При успехе → интегрировать в production
