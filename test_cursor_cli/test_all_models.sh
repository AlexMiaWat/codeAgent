#!/bin/bash
# test_all_models.sh
# Скрипт для быстрого тестирования всех моделей

MODELS=("" "auto" "claude-haiku" "gpt-4o-mini" "gemini-flash" "sonnet-3.5")
PROMPT="Создай файл test.txt с текстом 'Hello'"
CONTAINER="cursor-agent-life"
WORKSPACE="/workspace"

echo "=========================================="
echo "Тестирование моделей Cursor CLI"
echo "=========================================="
echo ""

for model in "${MODELS[@]}"; do
    echo "=== Тестирование модели: ${model:-auto} ==="
    
    if [ -z "$model" ]; then
        # Auto (без флага --model)
        cmd="docker exec $CONTAINER bash -c 'cd $WORKSPACE && /root/.local/bin/agent -p \"$PROMPT\" --force --approve-mcps'"
    else
        cmd="docker exec $CONTAINER bash -c 'cd $WORKSPACE && /root/.local/bin/agent --model $model -p \"$PROMPT\" --force --approve-mcps'"
    fi
    
    start_time=$(date +%s)
    eval $cmd
    return_code=$?
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    if [ $return_code -eq 0 ]; then
        status="✅ УСПЕХ"
    else
        status="❌ ОШИБКА"
    fi
    
    echo "Результат: $status"
    echo "Код возврата: $return_code"
    echo "Время выполнения: ${duration}s"
    echo "---"
    sleep 2
done

echo ""
echo "=========================================="
echo "Тестирование завершено"
echo "=========================================="
