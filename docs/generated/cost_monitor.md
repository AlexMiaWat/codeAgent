# Module: `cost_monitor`

## Class: `APICallRecord`

```python
Запись о API вызове для мониторинга стоимости
```

### Method: `APICallRecord.to_dict`

## Class: `CostSummary`

```python
Сводка стоимости за период
```

## Class: `CostMonitor`

```python
Монитор стоимости API вызовов
```

### Method: `CostMonitor.__init__`

### Method: `CostMonitor._load_config`

```python
Загрузка конфигурации стоимости
```

### Method: `CostMonitor._load_existing_records`

```python
Загрузка существующих записей о вызовах
```

### Method: `CostMonitor._save_records`

```python
Сохранение записей в файл
```

### Method: `CostMonitor.get_model_cost_info`

```python
Получение информации о стоимости модели
```

### Method: `CostMonitor.calculate_cost`

```python
Расчет стоимости API вызова

Args:
    model_name: Название модели
    input_tokens: Количество входных токенов
    output_tokens: Количество выходных токенов

Returns:
    Стоимость в USD
```

### Method: `CostMonitor.record_api_call`

```python
Запись информации о API вызове

Args:
    model_name: Название модели
    input_tokens: Количество входных токенов
    output_tokens: Количество выходных токенов
    provider: Провайдер модели
    task_id: ID задачи (опционально)
    success: Успешность вызова
    error_message: Сообщение об ошибке (опционально)
```

### Method: `CostMonitor._check_limits_and_warn`

```python
Проверка лимитов расходов и отправка предупреждений
```

### Method: `CostMonitor.get_cost_summary`

```python
Получение сводки стоимости за период

Args:
    period: Период агрегации ('hourly', 'daily', 'weekly', 'monthly')

Returns:
    CostSummary объект с агрегированными данными
```

### Method: `CostMonitor._generate_recommendations`

```python
Генерация рекомендаций по оптимизации расходов
```

### Method: `CostMonitor.get_model_efficiency_report`

```python
Отчет об эффективности использования моделей
```

### Method: `CostMonitor.reset_records`

```python
Очистка старых записей, оставляя только указанное количество дней

Args:
    days_to_keep: Количество дней для сохранения записей
```
