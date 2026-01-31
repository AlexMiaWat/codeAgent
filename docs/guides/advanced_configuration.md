# Расширенная настройка Code Agent

## Настройка API ключей

### Безопасность
**ВАЖНО:** API ключи никогда не должны храниться в файлах конфигурации, которые попадают в Git! Храните их только в переменных окружения или в файле `.env` (который должен быть в `.gitignore`).

### Google Gemini API
1. Получите ключ в [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Добавьте в `.env`: `GOOGLE_API_KEY=AIzaSy...`

### OpenRouter API (Рекомендуется)
1. Получите ключ на [OpenRouter](https://openrouter.ai/keys).
2. Добавьте в `.env`: `OPENROUTER_API_KEY=sk-or-v1-...`
3. Проверьте настройку: `python test/verify_api_key.py`

---

## Конфигурация сервера

Основные настройки находятся в `config/config.yaml`.

### Основные параметры
- `server.check_interval`: Интервал проверки новых задач (в секундах).
- `server.http_port`: Порт для мониторинга (по умолчанию 3456).
- `server.auto_reload`: Автоматический перезапуск сервера при изменении кода.
- `project.todo_format`: Формат файла задач (`md`, `txt`, `yaml`).

### Переключение CLI интерфейсов
Вы можете выбрать, какой интерфейс использовать для взаимодействия с AI:
- **Cursor CLI** (`cursor`): Официальный агент Cursor (рекомендуется).
- **Gemini CLI** (`gemini`): Кастомная реализация через Gemini API.
- **Hybrid** (`hybrid`): Автоматическое переключение.

Настройка в `config/llm_settings.yaml`:
```yaml
llm:
  cli_interface: cursor  # или "gemini", "hybrid"
```

---

## Настройка Git аутентификации

Для автоматической отправки коммитов (push) агенту требуется настроенная аутентификация.

### Вариант 1: SSH-ключ (Рекомендуется)
SSH-ключи позволяют работать без ввода пароля.
1. **Генерация**: `ssh-keygen -t ed25519 -C "your_email@example.com"`
2. **Добавление**: Скопируйте содержимое `~/.ssh/id_ed25519.pub` и добавьте его в настройки GitHub (SSH and GPG keys).
3. **Проверка**: `ssh -T git@github.com`

### Автоматическая настройка (Windows/Linux)
Используйте встроенные скрипты:
- **Windows**: `scripts\setup_git_ssh.bat`
- **Linux/Mac**: `scripts/setup_git_ssh.sh`

---

## HTTP API мониторинг
Сервер предоставляет REST API на порту 3456:
- `GET /health`: Проверка работоспособности.
- `GET /status`: Детальная информация о текущих задачах.
- `POST /restart`: Безопасный перезапуск.
