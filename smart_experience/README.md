# Smart Experience Directory

Эта директория содержит данные опыта выполнения задач smartAgent.

## Структура файлов

- `experience.json` - основной файл с данными опыта выполнения задач
- `README.md` - эта документация

## Формат данных опыта

Файл `experience.json` содержит информацию о выполненных задачах:

```json
{
  "version": "1.0",
  "tasks": [
    {
      "task_id": "task_123",
      "description": "Описание задачи",
      "success": true,
      "execution_time": 45.2,
      "timestamp": "/workspace",
      "notes": "Дополнительные заметки",
      "patterns": ["pattern1", "pattern2"]
    }
  ],
  "patterns": {
    "pattern1": ["task_123", "task_456"],
    "pattern2": ["task_789"]
  },
  "statistics": {
    "total_tasks": 150,
    "successful_tasks": 120,
    "failed_tasks": 30,
    "average_execution_time": 42.5
  }
}
```

## Использование

SmartAgent автоматически использует данные из этой директории для:

- Поиска похожих задач в истории
- Получения рекомендаций по выполнению
- Анализа паттернов успешного выполнения

## Очистка данных

При необходимости можно очистить историю, удалив файл `experience.json`.
SmartAgent автоматически создаст новый файл при следующем запуске.