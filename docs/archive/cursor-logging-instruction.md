# Инструкция по логированию для Cursor контейнеров

## Проблема

При создании и запуске Docker контейнеров для Cursor, логи не попадают в `docker logs`, что затрудняет диагностику и мониторинг.

## Причина

Стандартная команда запуска (`/bin/bash -c 'while true; do sleep 3600; done'`) не выводит ничего в stdout/stderr, поэтому Docker не фиксирует логи.

## Рекомендуемое решение

### 1. Dockerfile - добавить скрипт запуска с логированием

```dockerfile
FROM ubuntu:22.04

# ... существующие инструкции ...

# Создать скрипт запуска с логированием
RUN cat > /start.sh << 'EOF'
#!/bin/bash

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Container started"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Container ID: $(hostname)"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Image: cursor-agent:latest"

# Функция для вывода статуса каждый час
while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Container is running..."
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Uptime: $(cat /proc/uptime | awk '{print int($1/3600)" hours"}')"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Memory usage: $(free -h | awk '/^Mem:/ {print $3"/"$2}')"
    
    # Если есть cursor-agent процесс, показать его статус
    if pgrep -f cursor-agent > /dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cursor agent is running (PID: $(pgrep -f cursor-agent | head -1))"
    fi
    
    sleep 3600
done
EOF

RUN chmod +x /start.sh

# Использовать скрипт как точку входа
CMD ["/start.sh"]
```

### 2. Альтернатива - перенаправление логов cursor-agent

Если cursor-agent пишет в свои файлы логов:

```dockerfile
RUN cat > /start.sh << 'EOF'
#!/bin/bash

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting container with log forwarding..."

# Функция для вывода логов cursor-agent в stdout
tail_cursor_logs() {
    # Подождать пока появятся лог-файлы
    sleep 10
    
    CURSOR_LOG_DIR="$HOME/.local/share/cursor-agent/logs"
    
    if [ -d "$CURSOR_LOG_DIR" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Forwarding cursor-agent logs from $CURSOR_LOG_DIR"
        tail -F "$CURSOR_LOG_DIR"/*.log 2>/dev/null
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Cursor log directory not found"
    fi
}

# Запустить перенаправление логов в фоне
tail_cursor_logs &

# Основной цикл с периодическими сообщениями
while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Heartbeat - container is alive"
    sleep 3600
done
EOF

RUN chmod +x /start.sh
CMD ["/start.sh"]
```

### 3. Docker Compose конфигурация

```yaml
version: '3.8'

services:
  cursor-agent:
    image: cursor-agent:latest
    container_name: cursor-agent
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    restart: unless-stopped
    # Команда уже в Dockerfile
```

### 4. Запуск с docker run

```bash
docker run -d \
  --name cursor-agent \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  cursor-agent:latest
```

## Проверка логов

После внедрения изменений:

```bash
# Просмотр логов в реальном времени
docker logs -f cursor-agent

# Последние 100 строк
docker logs --tail 100 cursor-agent

# Логи с временными метками
docker logs -t cursor-agent

# Логи за последний час
docker logs --since 1h cursor-agent
```

## Дополнительные рекомендации

### Структурированное логирование

Для удобного парсинга логов рекомендуется использовать JSON формат:

```bash
#!/bin/bash

log_json() {
    local level=$1
    local message=$2
    echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"level\":\"$level\",\"message\":\"$message\",\"container\":\"$(hostname)\"}"
}

log_json "INFO" "Container started"

while true; do
    log_json "INFO" "Container is running"
    sleep 3600
done
```

### Логирование в syslog (опционально)

```dockerfile
# В Dockerfile
RUN apt-get update && apt-get install -y rsyslog

# В start.sh
#!/bin/bash
service rsyslog start
logger -t cursor-agent "Container started"

while true; do
    logger -t cursor-agent "Heartbeat - $(date)"
    sleep 3600
done
```

### Мониторинг здоровья контейнера

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD pgrep -f cursor-agent || exit 1
```

## Пример полного Dockerfile

```dockerfile
FROM ubuntu:22.04

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Создание скрипта запуска с логированием
COPY <<EOF /start.sh
#!/bin/bash
set -e

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "=== Cursor Agent Container Started ==="
log "Container ID: $(hostname)"
log "Container IP: $(hostname -i 2>/dev/null || echo 'N/A')"

# Основной цикл
while true; do
    log "Status: Running | Uptime: $(awk '{print int(\$1/3600)"h "int((\$1%3600)/60)"m"}' /proc/uptime)"
    
    # Проверка cursor-agent процесса
    if pgrep -f "cursor-agent" > /dev/null 2>&1; then
        AGENT_PID=$(pgrep -f "cursor-agent" | head -1)
        AGENT_MEM=$(ps -p $AGENT_PID -o rss= 2>/dev/null | awk '{print int($1/1024)"MB"}')
        log "Cursor Agent: Active | PID: $AGENT_PID | Memory: $AGENT_MEM"
    else
        log "Cursor Agent: Not detected"
    fi
    
    sleep 3600
done
EOF

RUN chmod +x /start.sh

HEALTHCHECK --interval=1m --timeout=3s \
  CMD ps aux | grep -v grep | grep -q "start.sh" || exit 1

CMD ["/start.sh"]
```

## Тестирование

После пересборки образа:

```bash
# Пересобрать образ
docker build -t cursor-agent:latest .

# Остановить старый контейнер
docker stop cursor-agent
docker rm cursor-agent

# Запустить новый
docker run -d --name cursor-agent cursor-agent:latest

# Проверить логи
docker logs cursor-agent

# Вывод должен быть примерно таким:
# [2026-01-19 15:30:00] === Cursor Agent Container Started ===
# [2026-01-19 15:30:00] Container ID: 8e8927efee92
# [2026-01-19 15:30:00] Container IP: 172.17.0.2
# [2026-01-19 15:30:00] Status: Running | Uptime: 0h 0m
```

---

## Для разработчиков

**Приоритет изменений:**

1. ✅ **Высокий**: Добавить скрипт с базовым логированием (heartbeat каждый час)
2. ✅ **Средний**: Добавить перенаправление cursor-agent логов в stdout
3. ✅ **Низкий**: Внедрить структурированное логирование (JSON)
4. ✅ **Опционально**: Настроить healthcheck

**Совместимость:** Решение работает с любыми базовыми образами Linux.

**Размер образа:** Увеличение минимальное (~1KB для скрипта).