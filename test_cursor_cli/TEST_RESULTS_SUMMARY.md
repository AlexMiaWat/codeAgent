# Сводка результатов тестирования Cursor CLI

**Дата тестирования:** 2026-01-19  
**Версия CLI:** agent (проверено через --list-models)  
**Окружение:** Docker (cursor-agent)

## Ключевые находки

### ✅ Рабочие модели

1. **`auto` (явный)** - ✅ Работает
   - Команда: `agent --model auto -p "..." --force --approve-mcps`
   - Код возврата: 0
   - Время: ~19 секунд
   - Billing error: Нет

2. **`grok`** - ✅ Работает
   - Команда: `agent --model grok -p "..." --force --approve-mcps`
   - Код возврата: 0
   - Время: ~16 секунд
   - Billing error: Нет

### ⚠️ Модели с billing errors

Все остальные модели возвращают ошибку:
```
NonRetriableError: You have an unpaid invoice
Visit [cursor.com/dashboard](https://cursor.com/dashboard) and pay your invoice in Stripe to resume requests.
```

Затронутые модели:
- `""` (Auto без флага) - billing error
- `gemini-3-flash` - billing error
- `gemini-3-pro` - billing error
- `sonnet-4.5` - billing error
- `opus-4.5` - billing error
- `gpt-5.2` - billing error
- `gpt-5.2-codex` - billing error

## Исправления в коде

### ✅ Исправлено использование флага модели

**Проблема:** В коде использовался флаг `-m`, но Cursor CLI требует `--model`

**Исправление:**
- `src/cursor_cli_interface.py` - изменено с `-m` на `--model`
- `test_cursor_cli/test_runner.py` - изменено с `-m` на `--model`

## Рекомендации

### P0 (Критический приоритет - внедрить немедленно)

1. **Использовать `--model auto`** вместо пустой строки
   - Пустая строка вызывает billing error
   - Явный `auto` работает стабильно

2. **Использовать `grok` как fallback**
   - Работает без billing errors
   - Быстрее чем `auto` (~16 сек vs ~19 сек)

### P1 (Высокий приоритет)

1. **Оплатить invoice в Cursor dashboard**
   - После оплаты другие модели могут заработать
   - Проверить: https://cursor.com/dashboard

2. **Реализовать fallback стратегию**
   - При billing error автоматически переключаться на `grok` или `auto`

### P2 (Средний приоритет)

1. **Протестировать после оплаты invoice**
   - Проверить работу дешевых моделей (gemini-3-flash, gemini-3-pro)
   - Проверить работу премиальных моделей (sonnet-4.5, opus-4.5, gpt-5.2)

## Статистика тестирования

- **Всего тестов:** 13
- **Успешных:** 2 (15%)
- **Неудачных:** 11 (85%)
- **Billing errors:** 10 (77%)
- **Таймаутов:** 0 (0%)

## Следующие шаги

1. ✅ Исправлен флаг модели (`-m` → `--model`)
2. ✅ Определены рабочие модели (`auto`, `grok`)
3. ⏳ Оплатить invoice в dashboard
4. ⏳ Протестировать модели после оплаты
5. ⏳ Реализовать fallback стратегию
6. ⏳ Обновить config.yaml с выбранной моделью

## Файлы результатов

- `results/models_simple.csv` - детальные результаты тестирования моделей
- `results/flags_test.csv` - результаты тестирования комбинаций флагов
- `results/summary.json` - JSON сводка результатов
