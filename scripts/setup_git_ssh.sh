#!/bin/bash
# Скрипт для автоматической настройки SSH-ключа для GitHub
# Использование: ./scripts/setup_git_ssh.sh [email]

set -e

EMAIL="${1:-codeagent@github.com}"
SSH_DIR="$HOME/.ssh"
KEY_FILE="$SSH_DIR/id_ed25519"
PUB_KEY_FILE="$SSH_DIR/id_ed25519.pub"
KNOWN_HOSTS="$SSH_DIR/known_hosts"

echo "=========================================="
echo "Настройка SSH-ключа для GitHub"
echo "=========================================="
echo ""

# Шаг 1: Проверка существующего ключа
echo "Шаг 1: Проверка существующего SSH-ключа..."
if [ -f "$KEY_FILE" ] && [ -f "$PUB_KEY_FILE" ]; then
    echo "✓ SSH-ключ уже существует: $KEY_FILE"
    echo ""
    echo "Ваш публичный ключ:"
    cat "$PUB_KEY_FILE"
    echo ""
    read -p "Использовать существующий ключ? (y/n): " use_existing
    if [ "$use_existing" != "y" ]; then
        echo "Создание нового ключа..."
        rm -f "$KEY_FILE" "$PUB_KEY_FILE"
    else
        EXISTING_KEY=true
    fi
else
    echo "SSH-ключ не найден, создаем новый..."
    EXISTING_KEY=false
fi

# Шаг 2: Создание нового ключа (если нужно)
if [ "$EXISTING_KEY" != "true" ]; then
    echo ""
    echo "Шаг 2: Создание нового SSH-ключа..."
    mkdir -p "$SSH_DIR"
    chmod 700 "$SSH_DIR"
    
    ssh-keygen -t ed25519 -C "$EMAIL" -f "$KEY_FILE" -N "" -q
    
    echo "✓ SSH-ключ создан: $KEY_FILE"
fi

# Шаг 3: Добавление GitHub в known_hosts
echo ""
echo "Шаг 3: Добавление GitHub в known_hosts..."
if ! grep -q "github.com" "$KNOWN_HOSTS" 2>/dev/null; then
    ssh-keyscan github.com >> "$KNOWN_HOSTS" 2>/dev/null
    echo "✓ GitHub добавлен в known_hosts"
else
    echo "✓ GitHub уже в known_hosts"
fi

# Шаг 4: Отображение публичного ключа
echo ""
echo "=========================================="
echo "Шаг 4: Ваш публичный ключ для GitHub:"
echo "=========================================="
echo ""
cat "$PUB_KEY_FILE"
echo ""
echo "=========================================="
echo "Инструкция:"
echo "=========================================="
echo "1. Скопируйте ключ выше (весь блок, начиная с ssh-ed25519)"
echo "2. Откройте: https://github.com/settings/keys"
echo "3. Нажмите 'New SSH key'"
echo "4. Вставьте ключ и сохраните"
echo ""
read -p "Нажмите Enter после добавления ключа в GitHub..."

# Шаг 5: Проверка подключения
echo ""
echo "Шаг 5: Проверка подключения к GitHub..."
if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "✓ Подключение к GitHub успешно!"
    GITHUB_USER=$(ssh -T git@github.com 2>&1 | grep -oP 'Hi \K[^!]+')
    echo "✓ Аутентифицирован как: $GITHUB_USER"
else
    echo "✗ Ошибка подключения. Проверьте:"
    echo "  - Ключ добавлен в GitHub"
    echo "  - Правильность скопированного ключа"
    exit 1
fi

# Шаг 6: Настройка remote URL (если нужно)
echo ""
echo "Шаг 6: Проверка remote URL..."
CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")

if [ -n "$CURRENT_REMOTE" ]; then
    if [[ "$CURRENT_REMOTE" == https://* ]]; then
        echo "Обнаружен HTTPS remote: $CURRENT_REMOTE"
        # Извлекаем username и repo из HTTPS URL
        if [[ "$CURRENT_REMOTE" =~ https://github.com/([^/]+)/([^/]+)\.git ]]; then
            USERNAME="${BASH_REMATCH[1]}"
            REPO="${BASH_REMATCH[2]}"
            SSH_URL="git@github.com:$USERNAME/$REPO.git"
            
            echo ""
            read -p "Переключить remote на SSH? (y/n): " switch_remote
            if [ "$switch_remote" == "y" ]; then
                git remote set-url origin "$SSH_URL"
                echo "✓ Remote переключен на SSH: $SSH_URL"
            else
                echo "Remote оставлен как HTTPS"
            fi
        else
            echo "⚠ Не удалось определить username/repo из URL"
        fi
    elif [[ "$CURRENT_REMOTE" == git@github.com:* ]]; then
        echo "✓ Remote уже использует SSH: $CURRENT_REMOTE"
    else
        echo "⚠ Неизвестный формат remote: $CURRENT_REMOTE"
    fi
else
    echo "⚠ Git remote не настроен"
fi

# Шаг 7: Финальная проверка
echo ""
echo "=========================================="
echo "Шаг 7: Финальная проверка"
echo "=========================================="
echo ""
echo "Проверка git push (dry-run)..."
if git push --dry-run origin HEAD 2>&1 | grep -q "Everything up-to-date\|would be pushed"; then
    echo "✓ Git push настроен корректно!"
else
    echo "⚠ Проверьте настройки репозитория"
fi

echo ""
echo "=========================================="
echo "✓ Настройка завершена!"
echo "=========================================="
echo ""
echo "Теперь git push будет работать автоматически без запросов пароля."
