# Быстрый старт: Гибридный интерфейс Cursor

**Решение проблем интеграции с Cursor CLI**

---

## 🎯 Что это?

Гибридный интерфейс автоматически выбирает оптимальный метод выполнения задач:
- **CLI** для простых задач (быстро)
- **Файловый интерфейс** для сложных задач (надежно)
- **Автоматический fallback** при неудаче

---

## ⚡ Быстрый старт

### 1. Простое использование

```python
from src.hybrid_cursor_interface import create_hybrid_cursor_interface

# Создание интерфейса
hybrid = create_hybrid_cursor_interface(
    cli_path="docker-compose-agent",  # или None для автопоиска
    project_dir="d:/Space/your-project"
)

# Выполнение задачи
result = hybrid.execute_task(
    instruction="Создай файл test.txt с текстом Hello",
    task_id="task_001"
)

# Проверка результата
if result.success:
    print(f"✅ Задача выполнена через: {result.method_used}")
else:
    print(f"❌ Ошибка: {result.error_message}")
```

### 2. С проверкой side-effects

```python
result = hybrid.execute_task(
    instruction="Создай файл report.md с анализом проекта",
    task_id="task_002",
    expected_files=["report.md"],  # Проверить наличие файла
    control_phrase="Отчет готов!"
)

if result.success and result.side_effects_verified:
    print("✅ Задача выполнена и файл создан")
```

### 3. Явное указание сложности

```python
from src.hybrid_cursor_interface import TaskComplexity

# Простая задача - через CLI
result = hybrid.execute_task(
    instruction="Что находится в README.md?",
    task_id="task_003",
    complexity=TaskComplexity.SIMPLE
)

# Сложная задача - через файловый интерфейс
result = hybrid.execute_task(
    instruction="Реализуй новую функцию парсинга",
    task_id="task_004",
    complexity=TaskComplexity.COMPLEX
)
```

---

## 🔧 Интеграция в CodeAgentServer

### Обновить `src/server.py`:

```python
from src.hybrid_cursor_interface import create_hybrid_cursor_interface

class CodeAgentServer:
    def __init__(self):
        # ... существующий код ...
        
        # Заменить cursor_cli и cursor_file на гибридный интерфейс
        self.cursor = create_hybrid_cursor_interface(
            cli_path=self.config.get("cursor.cli.cli_path"),
            project_dir=str(self.project_dir),
            prefer_cli=False,  # Не предпочитать CLI для сложных задач
            verify_side_effects=True  # Проверять side-effects
        )
        
        logger.info(f"Гибридный интерфейс Cursor инициализирован")
    
    def _execute_task_via_cursor(self, todo_item):
        """Выполнение задачи через гибридный интерфейс"""
        # Форматируем инструкцию
        instruction = self._format_instruction(todo_item)
        
        # Определяем ожидаемые файлы
        expected_files = self._get_expected_files(todo_item)
        
        # Выполняем через гибридный интерфейс
        result = self.cursor.execute_task(
            instruction=instruction,
            task_id=todo_item.id,
            expected_files=expected_files,
            control_phrase="Задача выполнена!",
            timeout=600
        )
        
        # Логируем результат
        if result.success:
            logger.info(f"Задача {todo_item.id} выполнена через {result.method_used}")
        else:
            logger.error(f"Ошибка выполнения задачи {todo_item.id}: {result.error_message}")
        
        return result.success
```

---

## 🧪 Тестирование

```bash
# Запуск тестов
cd d:/Space/codeAgent
python test/test_hybrid_interface.py
```

**Тесты проверяют:**
- ✅ Определение сложности задач
- ✅ Выполнение простых задач
- ✅ Выполнение сложных задач
- ✅ Fallback механизм

---

## 📊 Методы выполнения

| Метод | Когда используется | Скорость | Надежность |
|-------|-------------------|----------|------------|
| `cli` | Простые задачи (вопросы, анализ) | ⚡⚡⚡ | ⚠️ |
| `file` | Сложные задачи (создание, изменение) | ⚡ | ✅✅✅ |
| `cli_with_fallback` | CLI не выполнил → fallback на файловый | ⚡⚡ | ✅✅✅ |

---

## ⚙️ Настройки

### Предпочитать CLI (с fallback)

```python
hybrid = create_hybrid_cursor_interface(
    prefer_cli=True,  # Пробовать CLI даже для сложных задач
    verify_side_effects=True  # Проверять результат
)
```

**Результат:** CLI → если не выполнилось → fallback на файловый

### Только файловый интерфейс

```python
hybrid = create_hybrid_cursor_interface(
    prefer_cli=False,  # Не использовать CLI для сложных задач
    verify_side_effects=True
)
```

**Результат:** Простые → CLI, Сложные → файловый

---

## 🎓 Примеры

### Пример 1: Вопрос (простая задача)

```python
result = hybrid.execute_task(
    instruction="Какие файлы находятся в директории src/?",
    task_id="question_1"
)
# Метод: "cli" (быстро)
```

### Пример 2: Создание файла (сложная задача)

```python
result = hybrid.execute_task(
    instruction="Создай файл docs/report.md с анализом архитектуры",
    task_id="create_1",
    expected_files=["docs/report.md"],
    control_phrase="Отчет готов!"
)
# Метод: "file" (надежно)
```

### Пример 3: Рефакторинг (сложная задача с fallback)

```python
hybrid = create_hybrid_cursor_interface(prefer_cli=True)

result = hybrid.execute_task(
    instruction="Рефактор функции parse_config() для улучшения читаемости",
    task_id="refactor_1",
    expected_files=["src/config_loader.py"]
)
# Метод: "cli_with_fallback" (попытка CLI → fallback на файловый)
```

---

## 📝 Дополнительно

### Улучшенный формат инструкций

```python
from src.prompt_formatter import PromptFormatter

# Явное указание выполнения
instruction = PromptFormatter.format_task_with_execution_guarantee(
    task_name="Создание отчета",
    task_description="Создай файл report.md с анализом проекта",
    output_file="report.md",
    control_phrase="Отчет готов!"
)

result = hybrid.execute_task(instruction=instruction, task_id="task_001")
```

### Обработка результатов

```python
result = hybrid.execute_task(...)

if result.success:
    print(f"✅ Успех!")
    print(f"  Метод: {result.method_used}")
    print(f"  Вывод: {result.output[:200]}...")
    
    if result.side_effects_verified:
        print(f"  Side-effects проверены: ✅")
else:
    print(f"❌ Ошибка: {result.error_message}")
    
    # Доступ к деталям
    if result.cli_result:
        print(f"  CLI код: {result.cli_result.return_code}")
    if result.file_result:
        print(f"  Файловый результат: {result.file_result}")
```

---

## 🔍 Отладка

### Включить подробное логирование

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

hybrid = create_hybrid_cursor_interface(...)
```

### Проверить доступность интерфейсов

```python
print(f"CLI доступен: {hybrid.cli.is_available()}")
print(f"CLI команда: {hybrid.cli.cli_command}")
print(f"Файловый интерфейс: готов")
```

---

## 📚 Документация

- **Подробное описание:** `docs/CURSOR_INTEGRATION_SOLUTIONS.md`
- **Резюме:** `docs/INTEGRATION_FIX_SUMMARY.md`
- **Исходный код:** `src/hybrid_cursor_interface.py`
- **Тесты:** `test/test_hybrid_interface.py`

---

## ❓ FAQ

**Q: Когда использовать `prefer_cli=True`?**  
A: Когда хотите максимальную скорость с fallback на надежность.

**Q: Что делать если задача не выполняется?**  
A: Проверьте логи, убедитесь что `verify_side_effects=True` и `expected_files` указаны корректно.

**Q: Можно ли использовать только файловый интерфейс?**  
A: Да, установите `prefer_cli=False` и все сложные задачи пойдут через файловый интерфейс.

---

**Статус:** ✅ Готово к использованию
