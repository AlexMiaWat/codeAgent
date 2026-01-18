@echo off
REM Wrapper скрипт для запуска agent через Docker
REM Использование: agent.bat -p "instruction"

REM Получаем путь к docker-compose.agent.yml
set SCRIPT_DIR=%~dp0
set COMPOSE_FILE=%SCRIPT_DIR%..\docker\docker-compose.agent.yml

REM Запускаем agent через docker compose
docker compose -f "%COMPOSE_FILE%" run --rm agent %*
