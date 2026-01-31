# Тестирование Cursor CLI моделей

Эта директория содержит инструменты для систематического тестирования Cursor CLI с различными моделями.

## Структура

```
test_cursor_cli/
├── test_runner.py          # Python скрипт автоматизации тестирования
├── test_all_models.sh      # Bash скрипт для быстрого тестирования моделей
├── results/                 # Результаты тестирования (CSV, JSON)
├── logs/                   # Логи тестирования
└── README.md              # Этот файл
```

## Быстрый старт

### 1. Проверка текущего состояния

Перед началом тестирования выполните проверки из Этапа 1.1 плана:

```bash
# Проверка версии Cursor CLI
docker exec cursor-agent /root/.local/bin/agent --version

# Список доступных моделей
docker exec cursor-agent bash -c 'cd /workspace && /root/.local/bin/agent --list-models'

# Проверка ключа (первые 20 символов)
docker exec cursor-agent bash -c 'echo $CURSOR_API_KEY | head -c 20'
```

### 2. Быстрое тестирование всех моделей

```bash
cd test_cursor_cli
./test_all_models.sh > results/quick_test.log 2>&1
```

### 3. Полное автоматизированное тестирование

```bash
cd test_cursor_cli
python test_runner.py
```

Результаты будут сохранены в:
- `results/models_simple.csv` - результаты тестирования моделей
- `results/flags_test.csv` - результаты тестирования флагов
- `results/summary.json` - сводка результатов

## Ручное тестирование отдельных моделей

### Тест с Auto (без флага -m)
```bash
docker exec cursor-agent bash -c 'cd /workspace && /root/.local/bin/agent -p "Создай файл test.txt" --force --approve-mcps'
```

### Тест с дешевой моделью
```bash
docker exec cursor-agent bash -c 'cd /workspace && /root/.local/bin/agent -m claude-haiku -p "Создай файл test2.txt" --force --approve-mcps'
```

### Тест с другой дешевой моделью
```bash
docker exec cursor-agent bash -c 'cd /workspace && /root/.local/bin/agent -m gpt-4o-mini -p "Создай файл test3.txt" --force --approve-mcps'
```

## Анализ результатов

После выполнения тестов:

1. Откройте `results/summary.json` для общей сводки
2. Проверьте CSV файлы для детальных результатов
3. Заполните таблицы результатов в `docs/testing/CURSOR_CLI_MODEL_TESTING_PLAN.md`:
   - Таблица результатов тестирования `-m` (раздел 2.0.1)
   - Таблица результатов комбинаций (раздел 2.0.2)
   - Таблица рабочих вариантов (раздел 4.5.2)

## Критерии оценки

- ✅ Успешно - код возврата 0, нет billing errors
- ❌ Ошибка - код возврата != 0 или ошибка выполнения
- ⚠️ Billing Error - обнаружена ошибка "unpaid invoice" или "pay your invoice"
- ⏳ Таймаут - команда не завершилась в течение таймаута

## Следующие шаги

После завершения тестирования:

1. Проанализируйте результаты
2. Определите P0 варианты (рабочие, без billing errors)
3. Выберите оптимальную модель для внедрения
4. Обновите `config/config.yaml` с выбранной моделью

Подробный план тестирования: `docs/testing/CURSOR_CLI_MODEL_TESTING_PLAN.md`
