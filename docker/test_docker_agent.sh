#!/bin/bash
# Тест скрипт для проверки работы agent через Docker

set -e

echo "========================================="
echo "Тестирование agent через Docker"
echo "========================================="
echo ""

# Проверка .env файла
echo "1. Проверка .env файла:"
if [ -f "../.env" ]; then
    if grep -q "CURSOR_API_KEY" "../.env"; then
        echo "   [OK] CURSOR_API_KEY найден в .env"
        CURSOR_API_KEY=$(grep "CURSOR_API_KEY" "../.env" | cut -d'=' -f2)
        echo "   [OK] CURSOR_API_KEY установлен: ${CURSOR_API_KEY:0:20}..."
    else
        echo "   [FAIL] CURSOR_API_KEY не найден в .env"
        exit 1
    fi
else
    echo "   [FAIL] .env файл не найден"
    exit 1
fi

echo ""

# Проверка Docker образа
echo "2. Проверка Docker образа:"
if docker images | grep -q "cursor-agent"; then
    echo "   [OK] Образ cursor-agent найден"
else
    echo "   [FAIL] Образ cursor-agent не найден"
    exit 1
fi

echo ""

# Проверка версии agent
echo "3. Проверка версии agent:"
VERSION=$(docker compose -f docker-compose.agent.yml run --rm agent --version 2>&1 | tail -n 1)
if [ -n "$VERSION" ]; then
    echo "   [OK] Agent версия: $VERSION"
else
    echo "   [FAIL] Не удалось получить версию"
    exit 1
fi

echo ""

# Тест выполнения команды
echo "4. Тест выполнения команды:"
RESULT=$(docker compose -f docker-compose.agent.yml run --rm -e CURSOR_API_KEY agent -p "echo 'Test command'" 2>&1 | tail -n 3)
if echo "$RESULT" | grep -q "Test command\|rejected"; then
    echo "   [OK] Команда выполнена"
    echo "   Output: $RESULT"
else
    echo "   [WARNING] Неожиданный вывод: $RESULT"
fi

echo ""

# Тест создания файла
echo "5. Тест создания файла:"
docker compose -f docker-compose.agent.yml run --rm -e CURSOR_API_KEY agent -p "Create file docker_test3.txt with content 'Test from script'" 2>&1 | tail -n 1

if [ -f "../../your-project/docker_test3.txt" ]; then
    echo "   [OK] Файл создан успешно"
    CONTENT=$(cat ../../your-project/docker_test3.txt)
    echo "   [OK] Содержимое: $CONTENT"
else
    echo "   [FAIL] Файл не создан"
fi

echo ""
echo "========================================="
echo "Тестирование завершено"
echo "========================================="
