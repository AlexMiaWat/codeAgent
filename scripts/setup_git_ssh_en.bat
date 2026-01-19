@echo off
REM Setup SSH key for GitHub (Windows)
REM Usage: scripts\setup_git_ssh_en.bat [email]

setlocal enabledelayedexpansion

set EMAIL=%~1
if "%EMAIL%"=="" set EMAIL=codeagent@github.com

set SSH_DIR=%USERPROFILE%\.ssh
set KEY_FILE=%SSH_DIR%\id_ed25519
set PUB_KEY_FILE=%SSH_DIR%\id_ed25519.pub
set KNOWN_HOSTS=%SSH_DIR%\known_hosts

echo ==========================================
echo GitHub SSH Key Setup
echo ==========================================
echo.

REM Step 1: Check existing key
echo Step 1: Checking for existing SSH key...
if exist "%KEY_FILE%" if exist "%PUB_KEY_FILE%" (
    echo [OK] SSH key already exists: %KEY_FILE%
    echo.
    echo Your public key:
    type "%PUB_KEY_FILE%"
    echo.
    set /p USE_EXISTING="Use existing key? (y/n): "
    if /i not "!USE_EXISTING!"=="y" (
        echo Creating new key...
        del /f /q "%KEY_FILE%" "%PUB_KEY_FILE%" 2>nul
        set EXISTING_KEY=false
    ) else (
        set EXISTING_KEY=true
    )
) else (
    echo SSH key not found, creating new one...
    set EXISTING_KEY=false
)

REM Step 2: Create new key (if needed)
if "%EXISTING_KEY%"=="false" (
    echo.
    echo Step 2: Creating new SSH key...
    if not exist "%SSH_DIR%" mkdir "%SSH_DIR%"
    
    REM Use ssh-keygen from Git for Windows
    where ssh-keygen >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] ssh-keygen not found. Please install Git for Windows.
        exit /b 1
    )
    
    ssh-keygen -t ed25519 -C "%EMAIL%" -f "%KEY_FILE%" -N "" -q
    
    if exist "%KEY_FILE%" (
        echo [OK] SSH key created: %KEY_FILE%
    ) else (
        echo [ERROR] Failed to create key
        exit /b 1
    )
)

REM Step 3: Add GitHub to known_hosts
echo.
echo Step 3: Adding GitHub to known_hosts...
findstr /c:"github.com" "%KNOWN_HOSTS%" >nul 2>&1
if errorlevel 1 (
    ssh-keyscan github.com >> "%KNOWN_HOSTS%" 2>nul
    echo [OK] GitHub added to known_hosts
) else (
    echo [OK] GitHub already in known_hosts
)

REM Step 4: Display public key
echo.
echo ==========================================
echo Step 4: Your public key for GitHub:
echo ==========================================
echo.
type "%PUB_KEY_FILE%"
echo.
echo ==========================================
echo Instructions:
echo ==========================================
echo 1. Copy the key above (entire block starting with ssh-ed25519)
echo 2. Open: https://github.com/settings/keys
echo 3. Click 'New SSH key'
echo 4. Paste the key and save
echo.
pause

REM Step 5: Test connection
echo.
echo Step 5: Testing connection to GitHub...
ssh -T git@github.com 2>&1 | findstr /i "successfully authenticated" >nul
if errorlevel 1 (
    echo [ERROR] Connection failed. Please check:
    echo   - Key is added to GitHub
    echo   - Key was copied correctly
    pause
    exit /b 1
) else (
    echo [OK] Connection to GitHub successful!
    for /f "tokens=2" %%a in ('ssh -T git@github.com 2^>^&1 ^| findstr /i "Hi"') do (
        set GITHUB_USER=%%a
        echo [OK] Authenticated as: !GITHUB_USER!
    )
)

REM Step 6: Configure remote URL (if needed)
echo.
echo Step 6: Checking remote URL...
echo.

REM Determine target project directory
set TARGET_PROJECT_DIR=
set SCRIPT_DIR=%~dp0
set ORIGINAL_DIR=%CD%

REM Calculate path to .env file (one level up from scripts)
REM Use simpler way - calculate path directly
set CODEAGENT_DIR=%SCRIPT_DIR%..
REM Get absolute path through pushd/popd
pushd "%CODEAGENT_DIR%" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Failed to change to codeAgent directory
    set ENV_FILE=
) else (
    set CODEAGENT_DIR=%CD%
    set ENV_FILE=%CD%\.env
    popd >nul 2>&1
)

REM Read PROJECT_DIR from .env file
if "%ENV_FILE%"=="" (
    echo [WARNING] .env file path not defined
) else if not exist "%ENV_FILE%" (
    echo [WARNING] .env file not found: %ENV_FILE%
    echo Checking directory existence: %CODEAGENT_DIR%
    if exist "%CODEAGENT_DIR%" (
        echo [OK] codeAgent directory exists
        dir "%CODEAGENT_DIR%\.env*" 2>nul
    ) else (
        echo [ERROR] codeAgent directory not found
    )
) else (
    echo Reading PROJECT_DIR from .env file...
    echo .env path: %ENV_FILE%
    REM Use temp file for reliable parsing
    set TEMP_ENV_LINE=%TEMP%\project_dir_line_%RANDOM%.txt
    findstr /i "^PROJECT_DIR=" "%ENV_FILE%" > "%TEMP_ENV_LINE%" 2>nul
    if exist "%TEMP_ENV_LINE%" (
        REM Read line from temp file and extract value after =
        REM Use tokens=2* - this will extract everything after first =
        for /f "usebackq tokens=2* delims==" %%a in ("%TEMP_ENV_LINE%") do (
            REM %%a = first part after =, %%b = rest (if there are spaces in path)
            if "%%b"=="" (
                set TARGET_PROJECT_DIR=%%a
            ) else (
                REM If there's remainder, combine (for paths with spaces)
                set TARGET_PROJECT_DIR=%%a %%b
            )
        )
        REM Remove quotes if present
        set TARGET_PROJECT_DIR=!TARGET_PROJECT_DIR:"=!
        set TARGET_PROJECT_DIR=!TARGET_PROJECT_DIR:'=!
        REM Remove leading spaces
        :trim_start
        if "!TARGET_PROJECT_DIR:~0,1!"==" " (
            set TARGET_PROJECT_DIR=!TARGET_PROJECT_DIR:~1!
            goto :trim_start
        )
        REM Remove trailing spaces
        :trim_end
        if "!TARGET_PROJECT_DIR:~-1!"==" " (
            set TARGET_PROJECT_DIR=!TARGET_PROJECT_DIR:~0,-1!
            goto :trim_end
        )
        del "%TEMP_ENV_LINE%" >nul 2>&1
    )
    :project_dir_found
    if not "!TARGET_PROJECT_DIR!"=="" (
        echo [OK] Found PROJECT_DIR: !TARGET_PROJECT_DIR!
    ) else (
        echo [WARNING] PROJECT_DIR not found in .env file
    )
)

REM If PROJECT_DIR not found, ask user
if "%TARGET_PROJECT_DIR%"=="" (
    echo [WARNING] PROJECT_DIR not found in .env file
    echo.
    set /p TARGET_PROJECT_DIR="Enter target project path (or press Enter for current directory): "
    if "!TARGET_PROJECT_DIR!"=="" (
        set TARGET_PROJECT_DIR=%CD%
    )
)

REM Check if directory exists
if not exist "!TARGET_PROJECT_DIR!" (
    echo [ERROR] Directory not found: !TARGET_PROJECT_DIR!
    echo [WARNING] Continuing with current directory
    set TARGET_PROJECT_DIR=%CD%
) else (
    echo [OK] Target project: !TARGET_PROJECT_DIR!
)

REM Switch to target project directory
pushd "!TARGET_PROJECT_DIR!"

REM Check if it's a git repository
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Git remote not configured in directory: !TARGET_PROJECT_DIR!
    popd
    goto :final_check
)

for /f "delims=" %%a in ('git remote get-url origin') do set CURRENT_REMOTE=%%a

echo Current remote: %CURRENT_REMOTE%

echo %CURRENT_REMOTE% | findstr /c:"https://github.com" >nul
if not errorlevel 1 (
    echo Detected HTTPS remote: %CURRENT_REMOTE%
    REM Extract username and repo from HTTPS URL
    REM Format: https://github.com/username/repo.git
    REM tokens=4,5 means: token 4 = username, token 5 = repo.git
    for /f "tokens=4,5 delims=/" %%a in ("%CURRENT_REMOTE%") do (
        set USERNAME=%%a
        set REPO=%%b
    )
    REM Remove .git from end of repo if present
    set REPO=!REPO:.git=!
    REM Form SSH URL
    set SSH_URL=git@github.com:!USERNAME!/!REPO!.git
    REM Check that parsing was successful
    if "!USERNAME!"=="" (
        echo [ERROR] Failed to extract username from URL
        echo [WARNING] Skipping SSH switch
        goto :skip_switch
    )
    if "!REPO!"=="" (
        echo [ERROR] Failed to extract repo from URL
        echo [WARNING] Skipping SSH switch
        goto :skip_switch
    )
    
    echo.
    echo Proposed SSH URL: !SSH_URL!
    set /p SWITCH_REMOTE="Switch remote to SSH? (y/n): "
    if /i "!SWITCH_REMOTE!"=="y" (
        git remote set-url origin !SSH_URL!
        echo [OK] Remote switched to SSH: !SSH_URL!
        echo [OK] Project: !TARGET_PROJECT_DIR!
    ) else (
        echo Remote kept as HTTPS
    )
    :skip_switch
) else (
    echo %CURRENT_REMOTE% | findstr /c:"git@github.com" >nul
    if not errorlevel 1 (
        REM Check that SSH URL is correct
        echo %CURRENT_REMOTE% | findstr /r "^git@github.com:[^/]*/[^/]*\.git$" >nul
        if errorlevel 1 (
            echo [WARNING] Detected incorrect SSH URL: %CURRENT_REMOTE%
            echo [WARNING] Expected format: git@github.com:username/repo.git
            echo.
            set /p FIX_URL="Fix URL? (y/n): "
            if /i "!FIX_URL!"=="y" (
                set /p CORRECT_URL="Enter correct SSH URL (git@github.com:username/repo.git): "
                if not "!CORRECT_URL!"=="" (
                    git remote set-url origin !CORRECT_URL!
                    echo [OK] URL fixed: !CORRECT_URL!
                )
            )
        ) else (
            echo [OK] Remote already uses SSH: %CURRENT_REMOTE%
            echo [OK] Project: !TARGET_PROJECT_DIR!
        )
    ) else (
        echo [WARNING] Unknown remote format: %CURRENT_REMOTE%
    )
)

REM Return to original directory
popd

:final_check
REM Step 7: Final verification
echo.
echo ==========================================
echo Step 7: Final verification
echo ==========================================
echo.

REM Switch to target project directory for verification
if defined TARGET_PROJECT_DIR (
    if exist "!TARGET_PROJECT_DIR!" (
        pushd "!TARGET_PROJECT_DIR!"
        echo Testing git push (dry-run) for project: !TARGET_PROJECT_DIR!
        git push --dry-run origin HEAD 2>&1 | findstr /i "Everything up-to-date would be pushed" >nul
        if errorlevel 1 (
            echo [WARNING] Please check repository settings
        ) else (
            echo [OK] Git push configured correctly!
        )
        popd
    ) else (
        echo [WARNING] Project directory not found for verification
    )
) else (
    echo [WARNING] PROJECT_DIR not defined, verification skipped
)

echo.
echo ==========================================
echo [OK] Setup completed!
echo ==========================================
echo.
echo Git push will now work automatically without password prompts.
echo.
pause
