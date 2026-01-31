# Руководство по безопасности Code Agent

## Обзор безопасности

Code Agent реализует многоуровневую систему безопасности для защиты от различных типов угроз:

- **Аутентификация** пользователей с хэшированными паролями
- **Авторизация** доступа на основе ролей (RBAC)
- **Валидация** всех входных данных
- **Rate limiting** для защиты от DDoS атак
- **Аудит** всех операций системы

## Архитектура безопасности

### Компоненты

```
Security Layer
├── Authentication (JWT + Password Hashing)
├── Authorization (RBAC)
├── Input Validation
├── Rate Limiting
├── Audit Logging
└── Encryption (опционально)
```

## Аутентификация

### Хранение паролей

Пароли пользователей хранятся в хэшированном виде с использованием:

- **Алгоритм:** SHA-256
- **Соль:** Уникальная для каждого пользователя
- **Формат:** `hash = SHA256(salt + password)`

**Файл:** `config/users.yaml`
```yaml
users:
  admin:
    password_hash: "3a7464ca98e4909b91ba76100eadcdf51f8f07a503eb8239519256c9c1d6758d"
    salt: "daf0e64bdf2956868dca7c85a762a173"
    role: "admin"
    permissions: ["read", "write", "delete", "admin"]
    active: true
```

### JWT Токены

- **Алгоритм:** HS256
- **Срок действия:** 24 часа (настраивается)
- **Payload:** user_id, role, permissions, timestamps

### Генерация токенов

```python
from src.security_utils import PasswordUtils

# Генерация хэша для нового пользователя
salt = PasswordUtils.generate_salt()
hashed = PasswordUtils.hash_password("new_password", salt)

# Сохранение в config/users.yaml
```

## Авторизация (RBAC)

### Роли системы

#### Admin
- **Полный доступ** ко всем ресурсам
- **Управление пользователями**
- **Системное администрирование**

```yaml
admin:
  permissions:
    - "resources:read:*"
    - "resources:write:*"
    - "resources:delete:*"
    - "users:manage"
    - "system:admin"
```

#### Developer
- **Чтение** всех ресурсов
- **Запись** в src/, docs/, config/
- **Разработка** и тестирование

```yaml
developer:
  permissions:
    - "resources:read:*"
    - "resources:write:src/**"
    - "resources:write:docs/**"
    - "resources:write:config/**"
```

#### Viewer
- **Только чтение** всех ресурсов
- **Мониторинг** без возможности изменения

```yaml
viewer:
  permissions:
    - "resources:read:*"
```

### Правила доступа к ресурсам

```yaml
resource_policies:
  - resource: "docs/**"
    allow_roles: ["admin", "developer", "viewer"]
    deny_roles: []

  - resource: "src/**"
    allow_roles: ["admin", "developer"]
    deny_roles: []

  - resource: "logs/**"
    allow_roles: ["admin"]
    deny_roles: []
```

## Валидация входных данных

### Security Validator

```python
from src.security_utils import SecurityValidator

# Проверка длины и опасных символов
if not SecurityValidator.validate_input(username, max_length=50):
    raise ValueError("Invalid username format")

# Санитизация имен файлов
safe_name = SecurityValidator.sanitize_filename(user_filename)

# Проверка path traversal
if not SecurityValidator.validate_path_traversal(path, base_dir):
    raise PermissionError("Path traversal detected")
```

### Защищенные паттерны

- **SQL injection:** Параметризованные запросы
- **XSS:** Санитизация HTML контента
- **Path traversal:** Валидация путей относительно корня
- **Command injection:** Белый список разрешенных команд

## Rate Limiting

### Глобальные лимиты

```yaml
rate_limiting:
  enabled: true
  global:
    requests_per_minute: 60
    burst_limit: 10
```

### Лимиты по эндпоинтам

```yaml
endpoints:
  "/health":
    requests_per_minute: 120
    burst_limit: 20

  "/mcp":
    requests_per_minute: 30
    burst_limit: 5
```

### Лимиты по ролям

```yaml
user_limits:
  admin:
    requests_per_minute: 120
    burst_limit: 20

  developer:
    requests_per_minute: 60
    burst_limit: 10

  viewer:
    requests_per_minute: 30
    burst_limit: 5
```

## Аудит и мониторинг

### Audit Logging

Все операции логируются в `logs/mcp_audit.log`:

```json
{
  "timestamp": "2024-01-23T12:00:00Z",
  "user_id": "admin",
  "action": "resource_access",
  "resource": "file://src/main.py",
  "ip": "192.168.1.100",
  "user_agent": "Cursor/1.0.0"
}
```

### События аудита

- `auth_login` - Успешный вход
- `auth_logout` - Выход из системы
- `auth_failed` - Неудачная попытка входа
- `resource_access` - Доступ к ресурсу
- `resource_modify` - Изменение ресурса
- `permission_denied` - Отказ в доступе

### Метрики

Prometheus метрики доступны на `/metrics`:

```
mcp_requests_total{endpoint="/mcp", method="initialize"} 150
mcp_auth_success_total 145
mcp_auth_failure_total 5
mcp_rate_limit_exceeded_total 2
```

## Шифрование

### Настройки шифрования

```yaml
encryption:
  enabled: false  # Включить для чувствительных данных
  algorithm: "AES-256-GCM"
  key_rotation_days: 30
```

### Защищаемые данные

- JWT секретные ключи
- Чувствительные конфигурационные данные
- Аудит логи (опционально)

## Сетевая безопасность

### Firewall

Рекомендуемые правила iptables:

```bash
# Разрешить только localhost для разработки
iptables -A INPUT -p tcp -s localhost --dport 3000 -j ACCEPT
iptables -A INPUT -p tcp --dport 3000 -j DROP

# Для продакшена - ограничить IP
iptables -A INPUT -p tcp -s 192.168.1.0/24 --dport 3000 -j ACCEPT
```

### SSL/TLS

```yaml
ssl:
  enabled: true
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/key.pem"
  ca_file: "/path/to/ca.pem"
```

### CORS

```yaml
server:
  allowed_origins:
    - "https://cursor.sh"
    - "https://your-domain.com"
```

## Тестирование безопасности

### Unit тесты

```bash
pytest test/test_security.py -v
```

Проверяет:
- Хэширование паролей
- Валидацию входных данных
- Защиту от path traversal
- Санитизацию имен файлов

### Интеграционные тесты

```bash
pytest test/test_mcp_integration.py -v
```

Проверяет:
- Аутентификацию пользователей
- Авторизацию доступа
- Обработку ошибок
- Rate limiting

### Сканирование уязвимостей

```bash
# Сканирование зависимостей
safety check

# Сканирование кода
bandit -r src/
```

## Лучшие практики

### Для разработчиков

1. **Никогда не логируйте пароли или токены**
2. **Всегда валидируйте входные данные**
3. **Используйте параметризованные запросы**
4. **Регулярно обновляйте зависимости**
5. **Проводите code review на безопасность**

### Для администраторов

1. **Включайте SSL/TLS в продакшене**
2. **Регулярно меняйте пароли**
3. **Мониторьте логи аудита**
4. **Ограничивайте сетевой доступ**
5. **Делайте бэкапы конфигураций**

### Для пользователей

1. **Используйте сложные пароли**
2. **Не делитесь токенами доступа**
3. **Сообщайте о подозрительной активности**
4. **Регулярно меняйте пароли**

## Аварийные ситуации

### Подозрительная активность

1. **Проверить логи аудита**
   ```bash
   tail -f logs/mcp_audit.log | grep auth_failed
   ```

2. **Заблокировать IP адрес**
   ```bash
   iptables -A INPUT -s SUSPICIOUS_IP -j DROP
   ```

3. **Отозвать токены пользователя**
   ```bash
   # Через API или вручную в коде
   auth_manager.revoke_user_tokens(user_id)
   ```

### Утечка учетных данных

1. **Сменить все пароли**
2. **Отозвать все активные токены**
3. **Включить дополнительный мониторинг**
4. **Сообщить пользователям**

### DDoS атака

1. **Включить rate limiting**
2. **Ограничить по IP**
3. **Использовать CDN/WAF**
4. **Масштабировать инфраструктуру**

## Мониторинг безопасности

### Dashboards

Рекомендуется настроить Grafana dashboards для:

- Количества неудачных попыток входа
- Rate limiting превышений
- Доступа к чувствительным ресурсам
- Активных сессий пользователей

### Алерты

Настроить алерты на:

- Много неудачных попыток входа
- Доступ к заблокированным ресурсам
- Превышение rate limits
- Изменения в системных файлах

## Заключение

Безопасность - это непрерывный процесс. Регулярно:

- Обновляйте зависимости
- Проводите аудиты кода
- Мониторьте систему
- Обучайте команду
- Тестируйте на проникновение

**Помните:** Лучшая защита - это многоуровневая защита с defense in depth подходом.