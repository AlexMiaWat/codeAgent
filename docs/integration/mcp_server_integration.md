# Интеграция MCP Server в Code Agent

## Обзор

Code Agent включает полноценный **Model Context Protocol (MCP) Server**, который предоставляет доступ к ресурсам проекта через стандартизированный протокол MCP.

## Архитектура MCP Server

### Компоненты

```
MCP Server
├── Auth Manager          # Аутентификация и авторизация
├── Resource Manager      # Управление ресурсами проекта
├── Tools Manager         # Инструменты для работы с проектом
├── Prompts Manager       # Готовые промпты для задач
├── Cache Manager         # Кэширование для производительности
└── Metrics Manager      # Мониторинг и метрики
```

### Безопасность

- **Хэшированные пароли** с солью (SHA-256)
- **JWT токены** для аутентификации
- **RBAC (Role-Based Access Control)** для авторизации
- **Rate limiting** для защиты от DDoS
- **Валидация входных данных** для предотвращения инъекций

## API Endpoints

### Health Check
```http
GET /health
```

Проверяет состояние сервера.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-23T12:00:00",
  "server": "Code Agent MCP Server"
}
```

### Authentication

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "admin",
    "username": "admin",
    "role": "admin",
    "permissions": ["read", "write", "delete", "admin"]
  },
  "expires_in": 86400
}
```

#### Logout
```http
POST /auth/logout
Authorization: Bearer <token>
Content-Type: application/json

{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## MCP Protocol

### WebSocket Endpoint
```
ws://localhost:3000/mcp
```

### Инициализация соединения

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "init-1",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "resources": {"subscribe": true},
      "tools": {"listChanged": true},
      "prompts": {"listChanged": true}
    },
    "clientInfo": {
      "name": "Cursor",
      "version": "1.0.0"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "init-1",
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "resources": {"subscribe": true, "listChanged": true},
      "tools": {"listChanged": true},
      "prompts": {"listChanged": true},
      "logging": {}
    },
    "serverInfo": {
      "name": "Code Agent MCP Server",
      "version": "0.1.0"
    }
  }
}
```

## Доступные ресурсы

MCP Server предоставляет доступ к следующим ресурсам проекта:

### Структурированные ресурсы
- `docs/` - Документация проекта
- `src/` - Исходный код
- `config/` - Конфигурационные файлы
- `examples/` - Примеры использования
- `logs/` - Логи (только чтение)

### Формат URI
```
file://docs/README.md
file://src/main.py
file://config/config.yaml
```

## Инструменты (Tools)

### run_tests
Запуск автоматических тестов проекта.

**Параметры:**
```json
{
  "test_pattern": "test_*.py",
  "verbose": false
}
```

### code_check
Проверка качества кода (линтинг, типизация).

**Параметры:**
```json
{
  "file_path": "src/main.py",
  "check_type": "all"  // "lint", "type_check", "security", "all"
}
```

### build_project
Сборка проекта.

**Параметры:**
```json
{
  "build_type": "development",  // "development", "production", "test"
  "clean": false
}
```

## Промпты (Prompts)

### code_analysis
Анализ кода на наличие ошибок и улучшений.

**Аргументы:**
- `code` (обязательно) - Код для анализа
- `language` (опционально) - Язык программирования

### generate_tests
Генерация unit тестов для кода.

**Аргументы:**
- `code` (обязательно) - Код для тестирования
- `language` (опционально) - Язык программирования
- `framework` (опционально) - Тестовый фреймворк

### generate_docs
Генерация документации для кода.

**Аргументы:**
- `code` (обязательно) - Код для документирования
- `language` (опционально) - Язык программирования
- `doc_format` (опционально) - Формат документации

### debug_help
Помощь в отладке кода.

**Аргументы:**
- `error_message` (обязательно) - Сообщение об ошибке
- `code_context` (опционально) - Контекст кода
- `language` (опционально) - Язык программирования

## Конфигурация

### config/mcp_server.yaml
```yaml
server:
  host: "localhost"
  port: 3000
  log_level: "INFO"
  enable_cors: true

security:
  enabled: true
  auth_required: false  # Включить для продакшена

mcp:
  protocol_version: "2024-11-05"
  server_info:
    name: "Code Agent MCP Server"
    version: "0.1.0"
```

### config/users.yaml
```yaml
users:
  admin:
    password_hash: "..."  # Хэшированный пароль
    salt: "..."           # Соль для хэширования
    role: "admin"
    permissions: ["read", "write", "delete", "admin"]
    active: true
```

## Запуск

MCP Server запускается автоматически вместе с основным сервером Code Agent:

```bash
python main.py
```

Или отдельно:
```bash
python -c "from src.mcp.server import MCPServer; from src.config_loader import ConfigLoader; server = MCPServer(ConfigLoader()); server.run_server()"
```

## Мониторинг

### Метрики
- `/metrics` - Prometheus метрики
- Логи в `logs/mcp_server.log`

### Аудит
- Все действия логируются в `logs/mcp_audit.log`
- Отслеживаются: аутентификация, доступ к ресурсам, вызовы инструментов

## Безопасность

### Защита
- **HTTPS** в продакшене (настраивается в конфигурации)
- **Rate limiting** по IP и пользователям
- **CORS** ограничение origins
- **Input validation** для всех входных данных

### Аутентификация
- Поддержка нескольких пользователей с ролями
- JWT токены с истечением срока
- Автоматическая очистка истекших токенов

### Авторизация
- RBAC с детальными разрешениями
- Проверка доступа к ресурсам по ролям
- Аудит всех операций доступа

## Тестирование

### Интеграционные тесты
```bash
pytest test/test_mcp_integration.py -v
```

### Тесты безопасности
```bash
pytest test/test_security.py -v
```

## Разработка

### Добавление нового инструмента
1. Реализовать класс инструмента в `src/mcp/tools.py`
2. Зарегистрировать в `ToolsManager._initialize_tools()`
3. Добавить тесты в `test/test_mcp_integration.py`

### Добавление нового промпта
1. Добавить шаблон в `PromptsManager._initialize_prompts()`
2. Реализовать логику обработки аргументов
3. Добавить тесты

## Troubleshooting

### Проблемы с подключением
1. Проверить, запущен ли MCP сервер (порт 3000)
2. Проверить CORS настройки
3. Проверить логи в `logs/mcp_server.log`

### Проблемы с аутентификацией
1. Проверить правильность учетных данных
2. Проверить срок действия токена
3. Проверить роли и разрешения пользователя

### Проблемы с производительностью
1. Проверить настройки кэширования
2. Мониторить метрики в `/metrics`
3. Проверить нагрузку на систему