# Настройка Git аутентификации для автоматической отправки коммитов

**Дата создания:** 2026-01-19  
**Версия:** 1.0

---

## Проблема

При выполнении инструкции 8 (Коммит и отправка) через Cursor CLI может возникнуть ошибка:

```
Коммит создан локально. Для отправки в удалённый репозиторий требуется настройка аутентификации GitHub (SSH-ключ или Personal Access Token).
```

Это происходит потому, что Cursor CLI не имеет доступа к настройкам аутентификации Git.

**После настройки SSH:** Инструкция 8 будет автоматически отправлять коммиты в удаленный репозиторий без запросов пароля. Push выполняется автоматически после создания коммита.

---

## Быстрый старт (Автоматическая настройка)

Для автоматической настройки SSH-ключа используйте готовые скрипты:

**Windows:**
```bash
# Русская версия (может требовать UTF-8 поддержку в консоли)
scripts\setup_git_ssh.bat

# Английская версия (рекомендуется, если проблемы с кодировкой)
scripts\setup_git_ssh_en.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/setup_git_ssh.sh
./scripts/setup_git_ssh.sh
```

Скрипт автоматически:
- ✅ Проверит существующий ключ
- ✅ Создаст новый ключ (если нужно)
- ✅ Покажет публичный ключ для копирования
- ✅ Проверит подключение к GitHub
- ✅ **Прочитает PROJECT_DIR из .env файла** (целевой проект для Code Agent)
- ✅ Переключит remote на SSH для **целевого проекта** (не для codeAgent!)

**Важно:** Скрипт настраивает SSH для целевого проекта (указанного в `PROJECT_DIR` в `.env`), а не для самого codeAgent. Это правильное поведение, так как Code Agent работает с целевым проектом.

---

## Решения

### Вариант 1: Настройка SSH-ключа (Рекомендуется)

SSH-ключи работают автоматически и не требуют ввода паролей.

#### 1. Проверка существующего SSH-ключа

```bash
ls -al ~/.ssh
```

Если видите файлы `id_rsa` и `id_rsa.pub` (или `id_ed25519` и `id_ed25519.pub`), ключ уже существует.

#### 2. Создание нового SSH-ключа (если нужно)

**Автоматически (без пароля):**
```bash
# Для GitHub рекомендуется использовать ed25519
ssh-keygen -t ed25519 -C "codeagent@github" -f ~/.ssh/id_ed25519 -N ""

# Или для старых систем
ssh-keygen -t rsa -b 4096 -C "codeagent@github" -f ~/.ssh/id_rsa -N ""
```

**Интерактивно (с возможностью установить пароль):**
```bash
# Для GitHub рекомендуется использовать ed25519
ssh-keygen -t ed25519 -C "your_email@example.com"

# Или для старых систем
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

Нажмите Enter для принятия пути по умолчанию. При запросе пароля можно оставить пустым (или установить пароль для дополнительной безопасности).

**Примечание для Windows:**
- Убедитесь, что Git for Windows установлен (включает ssh-keygen)
- Если используете WSL, создавайте ключ в WSL, а не в Windows

#### 3. Добавление SSH-ключа в GitHub

```bash
# Скопируйте публичный ключ
cat ~/.ssh/id_ed25519.pub
# или
cat ~/.ssh/id_rsa.pub
```

Затем:
1. Откройте GitHub → Settings → SSH and GPG keys
2. Нажмите "New SSH key"
3. Вставьте содержимое публичного ключа
4. Сохраните

#### 4. Добавление GitHub в known_hosts (рекомендуется)

Перед проверкой подключения добавьте GitHub в known_hosts:

```bash
# Добавление GitHub в known_hosts
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

Это предотвратит запрос подтверждения при первом подключении.

#### 5. Проверка подключения

```bash
ssh -T git@github.com
```

**Успешный результат:**
```
Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

**Ошибка аутентификации:**
```
git@github.com: Permission denied (publickey).
```
→ Ключ еще не добавлен в GitHub или добавлен неправильно

**Ошибка хоста:**
```
Host key verification failed.
```
→ Выполните: `ssh-keyscan github.com >> ~/.ssh/known_hosts`

#### 6. Настройка remote URL на SSH

**Проверка текущего remote:**
```bash
git remote -v
```

**Если используется HTTPS (например, `https://github.com/username/repo.git`):**

```bash
# Автоматическое определение из текущего URL
git remote set-url origin git@github.com:username/repository.git

# Или вручную замените username и repository
```

**Пример:**
```bash
# Было: https://github.com/username/your-repo.git
# Стало: git@github.com:username/your-repo.git
git remote set-url origin git@github.com:username/your-repo.git
```

**Проверка после изменения:**
```bash
git remote -v
# Должно показать: origin  git@github.com:username/repository.git (fetch)
#                  origin  git@github.com:username/repository.git (push)
```

---

### Вариант 2: Personal Access Token (PAT)

Если SSH не подходит, используйте Personal Access Token.

#### 1. Создание Personal Access Token

1. Откройте GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Нажмите "Generate new token (classic)"
3. Выберите scope: `repo` (полный доступ к репозиториям)
4. Скопируйте токен (он показывается только один раз!)

#### 2. Настройка Git Credential Helper

**Для Windows:**
```bash
git config --global credential.helper wincred
```

**Для Linux/Mac:**
```bash
git config --global credential.helper store
```

#### 3. Использование токена

При следующем `git push` используйте токен как пароль:
- Username: ваш GitHub username
- Password: Personal Access Token (не ваш пароль GitHub!)

Или настройте URL с токеном:
```bash
git remote set-url origin https://TOKEN@github.com/username/repository.git
```

⚠️ **Внимание:** Токен в URL виден в истории команд. Лучше использовать credential helper.

---

### Вариант 3: Git Credential Manager

Git Credential Manager автоматически управляет аутентификацией.

#### Установка (Windows)

```bash
# Через Chocolatey
choco install git-credential-manager

# Или скачайте с https://github.com/GitCredentialManager/git-credential-manager/releases
```

#### Установка (Linux)

```bash
# Ubuntu/Debian
sudo apt-get install git-credential-manager

# Или через snap
sudo snap install git-credential-manager
```

После установки Git Credential Manager будет автоматически запрашивать аутентификацию при первом push.

---

## Проверка настройки

После настройки выполните полную проверку:

```bash
# 1. Проверка SSH-ключа
ls -la ~/.ssh/id_ed25519*

# 2. Проверка подключения к GitHub
ssh -T git@github.com

# 3. Проверка remote URL
git remote -v

# 4. Тестовая отправка (dry-run, не отправляет реальные изменения)
git push --dry-run origin HEAD

# 5. Реальная отправка (если есть коммиты для отправки)
git push origin main
```

**Признаки успешной настройки:**
- ✅ `ssh -T git@github.com` показывает приветствие с вашим username
- ✅ `git remote -v` показывает SSH URL (начинается с `git@github.com`)
- ✅ `git push` выполняется без запроса пароля/токена
- ✅ Нет ошибок типа "Permission denied" или "Authentication failed"

**Если что-то не работает:**
1. Проверьте, что ключ добавлен в GitHub: https://github.com/settings/keys
2. Убедитесь, что remote использует SSH, а не HTTPS
3. Проверьте права доступа к репозиторию на GitHub

---

## Решение проблемы в Code Agent

### Текущее поведение

Инструкция 8 теперь:
1. ✅ Создает коммит локально
2. ✅ Пытается выполнить `git push`
3. ✅ Если push не удался - создает отчет с информацией
4. ✅ Завершается успешно, если коммит создан (даже если push не удался)

### Что делать, если push не удался

1. **Проверьте отчет** в `docs/results/last_result.md` - там будет указан:
   - ID коммита
   - Причина неудачи
   - Инструкции для ручной отправки

2. **Настройте аутентификацию** по одному из вариантов выше:
   ```bash
   # Используйте автоматический скрипт
   scripts\setup_git_ssh.bat  # Windows
   # или
   ./scripts/setup_git_ssh.sh  # Linux/Mac
   ```

3. **Отправьте коммит вручную:**
   ```bash
   # Перейдите в директорию проекта
   cd D:\Space\your-project  # или ваш PROJECT_DIR
   
   # Отправьте последний коммит
   git push origin main
   
   # Или используйте конкретный ID коммита из отчета
   git push origin <commit-id>:main
   ```

4. **Проверьте, что push прошел:**
   ```bash
   git log --oneline -1  # Последний коммит
   git status            # Должно быть "Your branch is up to date"
   ```

### Автоматическая настройка перед запуском Code Agent

Рекомендуется настроить SSH-ключи **до** запуска Code Agent:

```bash
# 1. Настройте SSH-ключ
scripts\setup_git_ssh.bat

# 2. Проверьте настройку
ssh -T git@github.com
git remote -v

# 3. Запустите Code Agent
python main.py
```

Теперь инструкция 8 будет автоматически отправлять коммиты без проблем.

---

## Рекомендации

1. **Используйте SSH-ключи** - это самый безопасный и удобный способ
2. **Не храните токены в коде** - используйте credential helper или переменные окружения
3. **Проверяйте настройку** перед запуском Code Agent на новой машине
4. **Используйте разные ключи** для разных проектов (если нужно)

---

## Дополнительные ресурсы

- [GitHub: Generating a new SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
- [GitHub: Creating a personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [Git Credential Manager](https://github.com/GitCredentialManager/git-credential-manager)

---

## Устранение проблем

### Проблема: "Permission denied (publickey)"

**Причины:**
- Ключ не добавлен в GitHub
- Неправильно скопирован ключ
- Используется неправильный ключ

**Решение:**
1. Проверьте, что ключ добавлен: https://github.com/settings/keys
2. Убедитесь, что скопирован весь ключ (начинается с `ssh-ed25519` или `ssh-rsa`)
3. Проверьте подключение: `ssh -T git@github.com`

### Проблема: "Host key verification failed"

**Причина:** GitHub не в known_hosts

**Решение:**
```bash
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

### Проблема: Кракозябры в консоли Windows (проблемы с кодировкой)

**Причина:** Windows cmd.exe использует кодовую страницу 866/1251 вместо UTF-8

**Решение:**
1. Используйте английскую версию скрипта:
   ```bash
   scripts\setup_git_ssh_en.bat
   ```

2. Или установите UTF-8 вручную перед запуском:
   ```bash
   chcp 65001
   scripts\setup_git_ssh.bat
   ```

3. Или используйте PowerShell вместо cmd.exe (лучше поддерживает UTF-8):
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   .\scripts\setup_git_ssh.bat
   ```

### Проблема: Push все еще запрашивает пароль

**Причины:**
- Remote использует HTTPS вместо SSH
- SSH-ключ не загружен в ssh-agent

**Решение:**
```bash
# 1. Проверьте remote
git remote -v

# 2. Переключите на SSH (если используется HTTPS)
git remote set-url origin git@github.com:username/repository.git

# 3. Добавьте ключ в ssh-agent (Windows)
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 4. Проверьте снова
git push origin main
```

### Проблема: "Could not read from remote repository"

**Причины:**
- Нет прав доступа к репозиторию
- Репозиторий не существует
- Неправильный URL

**Решение:**
1. Проверьте права доступа на GitHub
2. Убедитесь, что репозиторий существует
3. Проверьте URL: `git remote -v`

---

## FAQ

**Q: Можно ли использовать один SSH-ключ для всех репозиториев?**  
A: Да, один ключ можно использовать для всех репозиториев GitHub. Просто добавьте его один раз в GitHub Settings.

**Q: Безопасно ли хранить токен в credential helper?**  
A: Да, credential helper хранит токены в зашифрованном виде. Но SSH-ключи более безопасны и удобны.

**Q: Что делать, если push все равно не работает?**  
A: 
1. Проверьте права доступа к репозиторию на GitHub
2. Убедитесь, что remote URL настроен правильно (`git remote -v`)
3. Проверьте подключение: `ssh -T git@github.com`
4. Убедитесь, что используете правильную ветку: `git branch`

**Q: Нужно ли настраивать аутентификацию для каждого проекта отдельно?**  
A: Нет, SSH-ключи настраиваются один раз на машине и работают для всех проектов. Remote URL настраивается для каждого репозитория отдельно.

**Q: Работает ли это в Docker/WSL?**  
A: Да, но нужно убедиться, что:
- SSH-ключи находятся в правильной директории (`~/.ssh` в контейнере/WSL)
- Known_hosts настроен
- Remote URL использует SSH

**Q: Можно ли использовать один ключ для нескольких GitHub аккаунтов?**  
A: Да, один ключ можно добавить в несколько аккаунтов GitHub. Но для разных аккаунтов лучше использовать разные ключи с настройкой `~/.ssh/config`.
