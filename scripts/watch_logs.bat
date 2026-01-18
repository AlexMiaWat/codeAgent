@echo off
REM Скрипт для просмотра логов Code Agent Server в реальном времени

echo ========================================
echo CODE AGENT SERVER - LOG VIEWER
echo ========================================
echo.
echo Press Ctrl+C to stop
echo.

:loop
cls
echo ========================================
echo CODE AGENT SERVER - LOG VIEWER
echo Updated: %date% %time%
echo ========================================
echo.

REM Показываем последние 30 строк лога
powershell -Command "Get-Content logs\code_agent.log -Tail 30 -Encoding UTF8"

echo.
echo ========================================
echo Refreshing in 5 seconds...
echo ========================================

timeout /t 5 /nobreak > nul
goto loop
