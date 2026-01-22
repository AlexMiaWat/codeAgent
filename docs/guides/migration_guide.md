# Руководство по миграции Code Agent

## Обзор

Это руководство поможет вам обновить Code Agent с предыдущих версий до версии 2026-01-22 и исправить проблемы, выявленные аудитом.

## 🚨 Критические изменения (версия 2026-01-22)

### 1. Валидация конфигурации Smart Agent

**Что изменилось:**
- Добавлена автоматическая валидация параметров Smart Agent при запуске
- Проверка существования директории `experience_dir`
- Валидация разумных пределов для `max_iter`, `memory`, `max_experience_tasks`

**Что делать:**
1. Убедитесь, что директория опыта существует или может быть создана:
   ```bash
   mkdir -p smart_experience
   ```

2. Проверьте параметры в `config/config.yaml`:
   ```yaml
   smart_agent:
     max_iter: 25        # Не больше 50
     memory: 100         # Не больше 1000
     max_experience_tasks: 1000  # Не больше 10000
   ```

3. При ошибке валидации сервер не запустится с подробным сообщением об исправлениях.

### 2. Исправление кеширования LearningTool

**Что изменилось:**
- Исправлена архитектура кеширования поиска похожих задач
- Теперь кеширование работает по нормализованному тексту запроса
- Добавлена очистка LRU кэша при изменении данных

**Что делать:**
- Никаких действий не требуется - изменения backward compatible
- Кэш автоматически очищается при сохранении нового опыта

### 3. Новые интеграционные тесты

**Что добавлено:**
- Интеграционные тесты для Smart Agent
- Тесты fallback режимов
- Тесты best_of_two стратегии

**Что делать:**
- Запустите тесты для проверки работоспособности:
  ```bash
  python test/integration/test_smart_agent_advanced_integration.py
  ```

### 4. Расширенный справочник конфигурации

**Что добавлено:**
- Полное описание всех конфигурационных файлов
- Примеры конфигурации для разных сценариев
- Детальное описание переменных окружения

**Что делать:**
- Ознакомьтесь с новыми разделами в `docs/core/configuration_reference.md`

## 📋 Изменения в конфигурации

### config/config.yaml

#### Новые параметры Smart Agent
```yaml
smart_agent:
  enabled: true
  experience_dir: "smart_experience"  # Новая директория опыта
  max_experience_tasks: 1000          # Максимум задач в опыте
  max_iter: 25                        # Максимум итераций
  memory: 100                         # Память для контекста
  verbose: true                       # Подробный вывод
  llm_strategy: 'best_of_two'         # Стратегия LLM
  cache_enabled: true                 # Кеширование включено
  cache_ttl_seconds: 3600             # TTL кэша
  learning_tool:                      # Настройки LearningTool
    enable_indexing: true
    cache_size: 1000
    cache_ttl_seconds: 3600
    max_experience_tasks: 1000
  context_analyzer_tool:              # Настройки ContextAnalyzerTool
    max_file_size: 1000000
    supported_extensions: ['.md', '.txt', '.rst', '.py', '.js', '.ts', '.json', '.yaml', '.yml']
    supported_languages: ['python', 'javascript', 'typescript']
    max_dependency_depth: 5
```

#### Удаленные параметры
- Убрана секция `logging` - теперь используется `config/logging.yaml`

### config/llm_settings.yaml

#### Изменения в структуре
```yaml
llm:
  default_provider: openrouter      # OpenRouter стал основным
  default_model: meta-llama/llama-3.2-1b-instruct  # Новая модель по умолчанию
  timeout: 200                      # Увеличен таймаут
  strategy: best_of_two            # Новая стратегия по умолчанию

  # Новые провайдеры
  model_roles:
    primary: []                     # Автоматический выбор (нуждается в уточнении)
    duplicate: []                   # Автоматический выбор
    reserve:                        # Резервные модели
      - kwaipilot/kat-coder-pro:free
    fallback:                       # Fallback модели
      - undi95/remm-slerp-l2-13b
      - microsoft/wizardlm-2-8x22b

  # Новая секция параллельной обработки
  parallel:
    enabled: true
    models: ["microsoft/wizardlm-2-8x22b", "microsoft/phi-3-mini-128k-instruct"]
    evaluator_model: microsoft/wizardlm-2-8x22b
    selection_criteria: [quality, relevance, completeness, efficiency]
```

### Новые конфигурационные файлы

#### config/llm_cost_config.yaml
```yaml
# Конфигурация стоимости API вызовов
openrouter:
  meta-llama/llama-3.2-1b-instruct:
    input_cost_per_1k: 0.00015
    output_cost_per_1k: 0.00015
    context_window: 131072
    max_tokens: 4096

monitoring:
  log_costs: true
  limits:
    daily_limit: 10.0
    monthly_limit: 100.0
  warning_thresholds: [50, 80, 95]
```

## 🔧 Миграционные скрипты

### Автоматическая миграция конфигурации

```python
#!/usr/bin/env python3
"""
Скрипт автоматической миграции конфигурации
"""

import os
import yaml
from pathlib import Path

def migrate_config():
    """Миграция конфигурации с предыдущих версий"""

    config_path = Path("config/config.yaml")
    if not config_path.exists():
        print("Конфигурационный файл не найден")
        return False

    # Загрузка текущей конфигурации
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Миграция Smart Agent настроек
    if 'smart_agent' not in config:
        config['smart_agent'] = {
            'enabled': True,
            'experience_dir': 'smart_experience',
            'max_experience_tasks': 1000,
            'max_iter': 25,
            'memory': 100,
            'verbose': True,
            'llm_strategy': 'best_of_two',
            'cache_enabled': True,
            'cache_ttl_seconds': 3600
        }
        print("✅ Добавлены настройки Smart Agent")

    # Создание директории опыта
    experience_dir = Path(config['smart_agent']['experience_dir'])
    if not experience_dir.exists():
        experience_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Создана директория опыта: {experience_dir}")

    # Удаление старой секции logging если есть
    if 'logging' in config:
        del config['logging']
        print("✅ Удалена устаревшая секция logging из config.yaml")

    # Сохранение обновленной конфигурации
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, indent=2, allow_unicode=True, sort_keys=False)

    print("✅ Конфигурация успешно обновлена")
    return True

if __name__ == "__main__":
    migrate_config()
```

### Миграция LLM настроек

```python
#!/usr/bin/env python3
"""
Миграция настроек LLM
"""

import yaml
from pathlib import Path

def migrate_llm_config():
    """Миграция LLM конфигурации"""

    llm_config_path = Path("config/llm_settings.yaml")
    if not llm_config_path.exists():
        print("LLM конфигурационный файл не найден")
        return False

    with open(llm_config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Обновление провайдера по умолчанию
    if config.get('llm', {}).get('default_provider') != 'openrouter':
        if 'llm' not in config:
            config['llm'] = {}
        config['llm']['default_provider'] = 'openrouter'
        config['llm']['default_model'] = 'meta-llama/llama-3.2-1b-instruct'
        print("✅ Обновлен провайдер LLM по умолчанию")

    # Добавление параллельной обработки
    if 'parallel' not in config.get('llm', {}):
        config['llm']['parallel'] = {
            'enabled': True,
            'models': ['microsoft/wizardlm-2-8x22b', 'microsoft/phi-3-mini-128k-instruct'],
            'evaluator_model': 'microsoft/wizardlm-2-8x22b',
            'selection_criteria': ['quality', 'relevance', 'completeness', 'efficiency']
        }
        print("✅ Добавлены настройки параллельной обработки")

    # Обновление резервных моделей
    model_roles = config.get('llm', {}).get('model_roles', {})
    if 'reserve' not in model_roles:
        model_roles['reserve'] = ['kwaipilot/kat-coder-pro:free']
        print("✅ Добавлены резервные модели")

    if 'fallback' not in model_roles:
        model_roles['fallback'] = ['undi95/remm-slerp-l2-13b', 'microsoft/wizardlm-2-8x22b']
        print("✅ Добавлены fallback модели")

    # Сохранение обновленной конфигурации
    with open(llm_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, indent=2, allow_unicode=True, sort_keys=False)

    print("✅ LLM конфигурация успешно обновлена")
    return True

if __name__ == "__main__":
    migrate_llm_config()
```

## 🧪 Проверка после миграции

### 1. Валидация конфигурации
```bash
# Проверка YAML синтаксиса
python -c "import yaml; print('Config OK' if yaml.safe_load(open('config/config.yaml')) else 'Config ERROR')"
python -c "import yaml; print('LLM OK' if yaml.safe_load(open('config/llm_settings.yaml')) else 'LLM ERROR')"

# Запуск валидации Smart Agent
python -c "from src.config_loader import ConfigLoader; loader = ConfigLoader(); print('Smart Agent validation passed')"
```

### 2. Тестирование функциональности
```bash
# Запуск интеграционных тестов
python test/integration/test_smart_agent_integration.py
python test/integration/test_smart_agent_advanced_integration.py

# Проверка LearningTool
python -c "
from src.tools.learning_tool import LearningTool
tool = LearningTool()
result = tool._run('save_experience', task_id='test_migration', task_description='Тест миграции', success=True, execution_time=1.0)
print('LearningTool OK' if 'сохранен' in result.lower() else 'LearningTool ERROR')
"

# Проверка ContextAnalyzerTool
python -c "
from src.tools.context_analyzer_tool import ContextAnalyzerTool
tool = ContextAnalyzerTool(project_dir='.')
result = tool._run('analyze_project')
print('ContextAnalyzerTool OK' if len(result) > 0 else 'ContextAnalyzerTool ERROR')
"
```

### 3. Проверка LLM подключения
```bash
# Тест LLM (если есть API ключ)
python -c "
try:
    from src.llm.llm_manager import LLMManager
    manager = LLMManager()
    print('LLM Manager OK')
except Exception as e:
    print(f'LLM Manager ERROR: {e}')
"
```

## 🚨 Возможные проблемы и решения

### Проблема: "experience_dir не существует"
**Решение:**
```bash
mkdir -p smart_experience
chmod 755 smart_experience
```

### Проблема: "max_iter слишком большой"
**Решение:** Уменьшите значение в конфигурации:
```yaml
smart_agent:
  max_iter: 25  # Вместо 50+
```

### Проблема: "API ключ не найден"
**Решение:** Добавьте в `.env` файл:
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Проблема: "Модель не найдена"
**Решение:** Проверьте доступность модели в OpenRouter или замените на доступную:
```yaml
llm:
  model_roles:
    primary: ["meta-llama/llama-3.2-1b-instruct"]  # Доступная модель
```

### Проблема: "Параллельная обработка падает"
**Решение:** Отключите параллельную обработку:
```yaml
llm:
  strategy: single
  parallel:
    enabled: false
```

## 📋 Контрольный список миграции

- [ ] Сделан backup всех конфигурационных файлов
- [ ] Запущен скрипт миграции конфигурации
- [ ] Создана директория `smart_experience/`
- [ ] Добавлен OPENROUTER_API_KEY в переменные окружения
- [ ] Проверена валидация конфигурации
- [ ] Запущены интеграционные тесты
- [ ] Протестирована базовая функциональность Smart Agent
- [ ] Проведено тестирование LLM (если применимо)

## 🔄 Rollback план

При проблемах с новой версией:

1. **Восстановление конфигурации:**
   ```bash
   cp config/config.yaml.backup config/config.yaml
   cp config/llm_settings.yaml.backup config/llm_settings.yaml
   ```

2. **Отключение Smart Agent:**
   ```yaml
   smart_agent:
     enabled: false
   ```

3. **Возврат к single стратегии:**
   ```yaml
   llm:
     strategy: single
     parallel:
       enabled: false
   ```

4. **Перезапуск сервера**

## 📞 Поддержка

При проблемах с миграцией:
1. Проверьте логи в `logs/codeagent.log`
2. Запустите тесты с подробным выводом
3. Ознакомьтесь с документацией в `docs/core/configuration_reference.md`
4. Создайте issue в репозитории с описанием проблемы

---

**Дата создания:** 2026-01-23
**Версия миграции:** 2026-01-22
**Автор:** Code Agent Team