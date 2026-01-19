@echo off
REM Установка UTF-8 кодировки для корректного отображения русских символов
chcp 65001 >nul 2>&1
REM Скрипт для автоматической настройки SSH-ключа для GitHub (Windows)
REM Использование: scripts\setup_git_ssh.bat [email]

setlocal enabledelayedexpansion

set EMAIL=%~1
if "%EMAIL%"=="" set EMAIL=codeagent@github.com

set SSH_DIR=%USERPROFILE%\.ssh
set KEY_FILE=%SSH_DIR%\id_ed25519
set PUB_KEY_FILE=%SSH_DIR%\id_ed25519.pub
set KNOWN_HOSTS=%SSH_DIR%\known_hosts

echo ==========================================
echo Настройка SSH-ключа для GitHub
echo ==========================================
echo.

REM Шаг 1: Проверка существующего ключа
echo Шаг 1: Проверка существующего SSH-ключа...
if exist "%KEY_FILE%" if exist "%PUB_KEY_FILE%" (
    echo ✓ SSH-ключ уже существует: %KEY_FILE%
    echo.
    echo Ваш публичный ключ:
    type "%PUB_KEY_FILE%"
    echo.
    echo Отпечаток ключа:
    ssh-keygen -lf "%PUB_KEY_FILE%" 2>nul
    echo.
    echo ⚠ ВАЖНО: Если этот ключ уже добавлен в GitHub, используйте его!
    echo.
    set /p USE_EXISTING="Использовать существующий ключ? (Y/n): "
    if "!USE_EXISTING!"=="" set USE_EXISTING=Y
    if /i not "!USE_EXISTING!"=="y" (
        echo.
        echo ⚠ ВНИМАНИЕ: Вы выбрали создание нового ключа.
        echo    Старый ключ будет удален. Убедитесь, что новый ключ добавлен в GitHub!
        echo.
        pause
        echo Создание нового ключа...
        del /f /q "%KEY_FILE%" "%PUB_KEY_FILE%" 2>nul
        set EXISTING_KEY=false
    ) else (
        set EXISTING_KEY=true
        echo ✓ Используем существующий ключ
    )
) else (
    echo SSH-ключ не найден, создаем новый...
    set EXISTING_KEY=false
)

REM Шаг 2: Создание нового ключа (если нужно)
if "%EXISTING_KEY%"=="false" (
    echo.
    echo Шаг 2: Создание нового SSH-ключа...
    if not exist "%SSH_DIR%" mkdir "%SSH_DIR%"
    
    REM Используем ssh-keygen из Git for Windows
    where ssh-keygen >nul 2>&1
    if errorlevel 1 (
        echo ✗ ssh-keygen не найден. Установите Git for Windows.
        exit /b 1
    )
    
    ssh-keygen -t ed25519 -C "%EMAIL%" -f "%KEY_FILE%" -N "" -q
    
    if exist "%KEY_FILE%" (
        echo ✓ SSH-ключ создан: %KEY_FILE%
    ) else (
        echo ✗ Ошибка создания ключа
        exit /b 1
    )
)

REM Шаг 3: Добавление GitHub в known_hosts
echo.
echo Шаг 3: Добавление GitHub в known_hosts...
findstr /c:"github.com" "%KNOWN_HOSTS%" >nul 2>&1
if errorlevel 1 (
    ssh-keyscan github.com >> "%KNOWN_HOSTS%" 2>nul
    echo ✓ GitHub добавлен в known_hosts
) else (
    echo ✓ GitHub уже в known_hosts
)

REM Шаг 4: Отображение публичного ключа
echo.
echo ==========================================
echo Шаг 4: Ваш публичный ключ для GitHub:
echo ==========================================
echo.
type "%PUB_KEY_FILE%"
echo.
echo ==========================================
echo Инструкция:
echo ==========================================
echo 1. Скопируйте ключ выше (весь блок, начиная с ssh-ed25519)
echo 2. Откройте: https://github.com/settings/keys
echo 3. Нажмите 'New SSH key'
echo 4. Вставьте ключ и сохраните
echo.
pause

REM Шаг 5: Проверка подключения
echo.
echo Шаг 5: Проверка подключения к GitHub...
ssh -T git@github.com 2>&1 | findstr /i "successfully authenticated" >nul
if errorlevel 1 (
    echo ✗ Ошибка подключения. Проверьте:
    echo   - Ключ добавлен в GitHub
    echo   - Правильность скопированного ключа
    pause
    exit /b 1
) else (
    echo ✓ Подключение к GitHub успешно!
    for /f "tokens=2" %%a in ('ssh -T git@github.com 2^>^&1 ^| findstr /i "Hi"') do (
        set GITHUB_USER=%%a
        echo ✓ Аутентифицирован как: !GITHUB_USER!
    )
)

REM Шаг 6: Настройка remote URL (если нужно)
echo.
echo Шаг 6: Проверка remote URL...
echo.

REM Определяем директорию целевого проекта
set TARGET_PROJECT_DIR=
set SCRIPT_DIR=%~dp0
set ORIGINAL_DIR=%CD%

REM Вычисляем путь к .env файлу (на уровень выше scripts)
REM Используем более простой способ - вычисляем путь напрямую
set CODEAGENT_DIR=%SCRIPT_DIR%..
REM Получаем абсолютный путь через pushd/popd
pushd "%CODEAGENT_DIR%" >nul 2>&1
if errorlevel 1 (
    echo ⚠ Не удалось перейти в директорию codeAgent
    set ENV_FILE=
) else (
    set CODEAGENT_DIR=%CD%
    set ENV_FILE=%CD%\.env
    popd >nul 2>&1
)

REM Читаем PROJECT_DIR из .env файла
if "%ENV_FILE%"=="" (
    echo ⚠ Путь к .env файлу не определен
) else if not exist "%ENV_FILE%" (
    echo ⚠ Файл .env не найден: %ENV_FILE%
    echo Проверка существования директории: %CODEAGENT_DIR%
    if exist "%CODEAGENT_DIR%" (
        echo ✓ Директория codeAgent существует
        dir "%CODEAGENT_DIR%\.env*" 2>nul
    ) else (
        echo ✗ Директория codeAgent не найдена
    )
) else (
    echo Чтение PROJECT_DIR из .env файла...
    echo Путь к .env: %ENV_FILE%
    REM Используем временный файл для надежного парсинга
    set TEMP_ENV_LINE=%TEMP%\project_dir_line_%RANDOM%.txt
    findstr /i "^PROJECT_DIR=" "%ENV_FILE%" > "%TEMP_ENV_LINE%" 2>nul
    if exist "%TEMP_ENV_LINE%" (
        REM Читаем строку из временного файла и извлекаем значение после =
        REM Используем tokens=2* - это извлечет все после первого = (включая пробелы)
        for /f "usebackq tokens=2* delims==" %%a in ("%TEMP_ENV_LINE%") do (
            REM %%a = первая часть после =, %%b = остальное (если есть пробелы в пути)
            if "%%b"=="" (
                set TARGET_PROJECT_DIR=%%a
            ) else (
                REM Если есть остаток, объединяем (для путей с пробелами)
                set TARGET_PROJECT_DIR=%%a %%b
            )
        )
        REM Удаляем кавычки если есть
        set TARGET_PROJECT_DIR=!TARGET_PROJECT_DIR:"=!
        set TARGET_PROJECT_DIR=!TARGET_PROJECT_DIR:'=!
        REM Удаляем пробелы в начале
        :trim_start
        if "!TARGET_PROJECT_DIR:~0,1!"==" " (
            set TARGET_PROJECT_DIR=!TARGET_PROJECT_DIR:~1!
            goto :trim_start
        )
        REM Удаляем пробелы в конце
        :trim_end
        if "!TARGET_PROJECT_DIR:~-1!"==" " (
            set TARGET_PROJECT_DIR=!TARGET_PROJECT_DIR:~0,-1!
            goto :trim_end
        )
        del "%TEMP_ENV_LINE%" >nul 2>&1
    )
    :project_dir_found
    if not "!TARGET_PROJECT_DIR!"=="" (
        echo ✓ Найден PROJECT_DIR: !TARGET_PROJECT_DIR!
    ) else (
        echo ⚠ PROJECT_DIR не найден в .env файле
    )
)

REM Если PROJECT_DIR не найден, запрашиваем у пользователя
if "%TARGET_PROJECT_DIR%"=="" (
    echo ⚠ PROJECT_DIR не найден в .env файле
    echo.
    set /p TARGET_PROJECT_DIR="Введите путь к целевому проекту (или нажмите Enter для текущей директории): "
    if "!TARGET_PROJECT_DIR!"=="" (
        set TARGET_PROJECT_DIR=%CD%
    )
)

REM Проверяем существование директории
if not exist "!TARGET_PROJECT_DIR!" (
    echo ✗ Директория не найдена: !TARGET_PROJECT_DIR!
    echo ⚠ Продолжаем с текущей директорией
    set TARGET_PROJECT_DIR=%CD%
) else (
    echo ✓ Целевой проект: !TARGET_PROJECT_DIR!
)

REM Переключаемся в директорию целевого проекта
pushd "!TARGET_PROJECT_DIR!"

REM Проверяем, что это git репозиторий
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo ⚠ Git remote не настроен в директории: !TARGET_PROJECT_DIR!
    popd
    goto :final_check
)

for /f "delims=" %%a in ('git remote get-url origin') do set CURRENT_REMOTE=%%a

echo Текущий remote: %CURRENT_REMOTE%

echo %CURRENT_REMOTE% | findstr /c:"https://github.com" >nul
if not errorlevel 1 (
    echo Обнаружен HTTPS remote: %CURRENT_REMOTE%
    REM Извлекаем username и repo из HTTPS URL
    REM Формат: https://github.com/username/repo.git
    REM tokens=4,5 означает: token 4 = username, token 5 = repo.git
    for /f "tokens=4,5 delims=/" %%a in ("%CURRENT_REMOTE%") do (
        set USERNAME=%%a
        set REPO=%%b
    )
    REM Удаляем .git из конца repo, если есть
    set REPO=!REPO:.git=!
    REM Формируем SSH URL
    set SSH_URL=git@github.com:!USERNAME!/!REPO!.git
    REM Проверяем, что парсинг прошел успешно
    if "!USERNAME!"=="" (
        echo ✗ Ошибка: не удалось извлечь username из URL
        echo ⚠ Пропускаем переключение на SSH
        goto :skip_switch
    )
    if "!REPO!"=="" (
        echo ✗ Ошибка: не удалось извлечь repo из URL
        echo ⚠ Пропускаем переключение на SSH
        goto :skip_switch
    )
    
    echo.
    echo Предлагаемый SSH URL: !SSH_URL!
    set /p SWITCH_REMOTE="Переключить remote на SSH? (y/n): "
    if /i "!SWITCH_REMOTE!"=="y" (
        git remote set-url origin !SSH_URL!
        echo ✓ Remote переключен на SSH: !SSH_URL!
        echo ✓ Проект: !TARGET_PROJECT_DIR!
    ) else (
        echo Remote оставлен как HTTPS
    )
    :skip_switch
) else (
    echo %CURRENT_REMOTE% | findstr /c:"git@github.com" >nul
    if not errorlevel 1 (
        REM Проверяем, что SSH URL корректный
        echo %CURRENT_REMOTE% | findstr /r "^git@github.com:[^/]*/[^/]*\.git$" >nul
        if errorlevel 1 (
            echo ⚠ Обнаружен некорректный SSH URL: %CURRENT_REMOTE%
            echo ⚠ Ожидается формат: git@github.com:username/repo.git
            echo.
            set /p FIX_URL="Исправить URL? (y/n): "
            if /i "!FIX_URL!"=="y" (
                set /p CORRECT_URL="Введите правильный SSH URL (git@github.com:username/repo.git): "
                if not "!CORRECT_URL!"=="" (
                    git remote set-url origin !CORRECT_URL!
                    echo ✓ URL исправлен: !CORRECT_URL!
                )
            )
        ) else (
            echo ✓ Remote уже использует SSH: %CURRENT_REMOTE%
            echo ✓ Проект: !TARGET_PROJECT_DIR!
        )
    ) else (
        echo ⚠ Неизвестный формат remote: %CURRENT_REMOTE%
    )
)

REM Возвращаемся в исходную директорию
popd

:final_check
REM Шаг 7: Финальная проверка
echo.
echo ==========================================
echo Шаг 7: Финальная проверка
echo ==========================================
echo.

REM Переключаемся в директорию целевого проекта для проверки
if defined TARGET_PROJECT_DIR (
    if exist "!TARGET_PROJECT_DIR!" (
        pushd "!TARGET_PROJECT_DIR!"
        echo Проверка git push (dry-run) для проекта: !TARGET_PROJECT_DIR!
        git push --dry-run origin HEAD 2>&1 | findstr /i "Everything up-to-date would be pushed" >nul
        if errorlevel 1 (
            echo ⚠ Проверьте настройки репозитория
        ) else (
            echo ✓ Git push настроен корректно!
        )
        popd
    ) else (
        echo ⚠ Директория проекта не найдена для проверки
    )
) else (
    echo ⚠ PROJECT_DIR не определен, проверка пропущена
)

echo.
echo ==========================================
echo ✓ Настройка завершена!
echo ==========================================
echo.
echo Теперь git push будет работать автоматически без запросов пароля.
echo.
pause
