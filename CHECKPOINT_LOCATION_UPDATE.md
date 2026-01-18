# Обновление расположения Checkpoint файлов

**Дата:** 2026-01-18  
**Версия:** 1.1

## Изменение

Checkpoint файлы теперь создаются в каталоге `codeAgent`, а не в целевом проекте.

### До изменения:

```
D:\Space\life\.codeagent_checkpoint.json
D:\Space\life\.codeagent_sessions.json
```

### После изменения:

```
d:\Space\codeAgent\.codeagent_checkpoint.json
d:\Space\codeAgent\.codeagent_sessions.json
```

## Причина изменения

Checkpoint файлы содержат служебную информацию о работе Code Agent Server и не должны загрязнять целевой проект. Они относятся к инфраструктуре `codeAgent`, а не к проекту `life`.

## Что изменено

### 1. `src/server.py`

**CheckpointManager:**
```python
# Было:
self.checkpoint_manager = CheckpointManager(self.project_dir, checkpoint_file)

# Стало:
codeagent_dir = Path(__file__).parent.parent  # Директория codeAgent
self.checkpoint_manager = CheckpointManager(codeagent_dir, checkpoint_file)
```

**SessionTracker:**
```python
# Было:
self.session_tracker = SessionTracker(self.project_dir, tracker_file)

# Стало:
codeagent_dir = Path(__file__).parent.parent  # Директория codeAgent
self.session_tracker = SessionTracker(codeagent_dir, tracker_file)
```

### 2. `scripts/monitor_server.py`

```python
# Было:
project_dir = Path("D:/Space/life")
checkpoint_file = project_dir / ".codeagent_checkpoint.json"

# Стало:
codeagent_dir = Path(__file__).parent.parent  # d:\Space\codeAgent
checkpoint_file = codeagent_dir / ".codeagent_checkpoint.json"
```

## Преимущества

1. **Чистота целевого проекта** - служебные файлы не попадают в репозиторий проекта
2. **Централизованное хранение** - вся информация о работе агента в одном месте
3. **Упрощенное управление** - легче найти и управлять checkpoint файлами
4. **Изоляция** - checkpoint файлы не зависят от структуры целевого проекта

## Структура файлов

```
d:\Space\codeAgent\
├── .codeagent_checkpoint.json        # Основной checkpoint файл
├── .codeagent_checkpoint.json.backup # Резервная копия
├── .codeagent_sessions.json          # Информация о сессиях
├── logs/
│   └── code_agent.log                # Логи сервера
├── src/
│   └── ...
└── scripts/
    └── monitor_server.py             # Скрипт мониторинга
```

## Миграция

Если у вас есть старые checkpoint файлы в целевом проекте, их можно безопасно удалить:

```bash
rm D:/Space/life/.codeagent_checkpoint.json
rm D:/Space/life/.codeagent_checkpoint.json.backup
rm D:/Space/life/.codeagent_sessions.json
```

Или переместить в `codeAgent` (если хотите сохранить историю):

```bash
mv D:/Space/life/.codeagent_checkpoint.json d:/Space/codeAgent/
mv D:/Space/life/.codeagent_sessions.json d:/Space/codeAgent/
```

## Проверка

После обновления проверьте, что checkpoint файлы создаются в правильном месте:

```bash
# Проверка расположения checkpoint файла
ls -la d:/Space/codeAgent/.codeagent*

# Вывод:
# -rw-r--r-- 1 user group 761 янв 18 23:20 .codeagent_checkpoint.json
# -rw-r--r-- 1 user group 720 янв 18 23:20 .codeagent_checkpoint.json.backup
```

Или через скрипт мониторинга:

```bash
python scripts/monitor_server.py
```

В выводе должно быть:
```
Session: 20260118_232006
Iteration: 1
Status: [RUNNING]
```

## Обратная совместимость

Изменение не влияет на:
- Работу с целевым проектом
- Выполнение задач
- Логирование
- Cursor интерфейсы

Все функции работают как прежде, только checkpoint файлы теперь хранятся в правильном месте.

---

**Автор:** Code Agent Team  
**Статус:** Реализовано ✅
