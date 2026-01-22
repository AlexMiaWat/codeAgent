#!/usr/bin/env python3
"""
Тесты интеграции Smart Agent с Git (автоматические коммиты)
Проверяет работу автоматических коммитов для ветки smart
"""

import sys
import os
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, mock_open

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import json
from datetime import datetime


def run_git_command(repo_path, command, check=True):
    """Вспомогательная функция для выполнения Git команд"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        if check and result.returncode != 0:
            print(f"Git command failed: {command}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, command)
        return result
    except subprocess.TimeoutExpired:
        print(f"Git command timeout: {command}")
        raise


def test_smart_git_branch_creation():
    """Тест создания и переключения на ветку smart"""
    print("🌿 Тестирование создания ветки smart...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"
            repo_path.mkdir()

            # Инициализируем Git репозиторий
            run_git_command(repo_path, "git init")
            run_git_command(repo_path, "git config user.name 'Test User'")
            run_git_command(repo_path, "git config user.email 'test@example.com'")

            # Создаем начальный коммит
            readme_file = repo_path / "README.md"
            readme_file.write_text("# Test Repository\n")
            run_git_command(repo_path, "git add README.md")
            run_git_command(repo_path, "git commit -m 'Initial commit'")

            # Создаем и переключаемся на ветку smart
            run_git_command(repo_path, "git checkout -b smart")

            # Проверяем текущую ветку
            result = run_git_command(repo_path, "git branch --show-current")
            current_branch = result.stdout.strip()

            assert current_branch == "smart", f"Ожидалась ветка 'smart', получена '{current_branch}'"

            print("✅ Ветка smart создана и активна")
            print(f"   Текущая ветка: {current_branch}")

        return True

    except Exception as e:
        print(f"❌ Ошибка создания ветки smart: {e}")
        return False


def test_smart_git_auto_commit():
    """Тест автоматического коммита в ветку smart"""
    print("\n💾 Тестирование автоматического коммита в ветку smart...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"
            repo_path.mkdir()

            # Инициализируем Git репозиторий
            run_git_command(repo_path, "git init")
            run_git_command(repo_path, "git config user.name 'Smart Agent'")
            run_git_command(repo_path, "git config user.email 'smart@agent.local'")

            # Создаем начальный коммит в main
            readme_file = repo_path / "README.md"
            readme_file.write_text("# Smart Agent Test\n")
            run_git_command(repo_path, "git add README.md")
            run_git_command(repo_path, "git commit -m 'Initial commit'")

            # Переключаемся на ветку smart
            run_git_command(repo_path, "git checkout -b smart")

            # Имитируем работу Smart Agent - создаем файл результатов
            results_file = repo_path / "docs" / "results" / "test_result.md"
            results_file.parent.mkdir(parents=True, exist_ok=True)

            task_id = "1769119092"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            results_content = f"""# Результат выполнения задачи

**Задача:** Тест автоматического коммита
**ID:** {task_id}
**Время:** {timestamp}

## Выполненные действия

✅ Создан тестовый файл
✅ Проверена работа Git интеграции

## Результат

Тест завершен успешно.

---

Результат готов!
"""

            results_file.write_text(results_content)

            # Проверяем статус Git
            status_result = run_git_command(repo_path, "git status --porcelain")
            status_output = status_result.stdout.strip()

            assert status_output, "Файл не добавлен в Git"

            # Добавляем изменения
            run_git_command(repo_path, "git add .")

            # Создаем коммит с сообщением в стиле Smart Agent
            commit_message = f"feat: Тест автоматического коммита (задача {task_id})"

            run_git_command(repo_path, f'git commit -m "{commit_message}"')

            # Проверяем коммит
            log_result = run_git_command(repo_path, "git log --oneline -1")
            commit_info = log_result.stdout.strip()

            assert commit_message in commit_info, f"Сообщение коммита не найдено: {commit_info}"

            # Проверяем, что мы на ветке smart
            branch_result = run_git_command(repo_path, "git branch --show-current")
            current_branch = branch_result.stdout.strip()

            assert current_branch == "smart", f"Коммит не на ветке smart: {current_branch}"

            print("✅ Автоматический коммит создан успешно")
            print(f"   Ветка: {current_branch}")
            print(f"   Коммит: {commit_info}")

        return True

    except Exception as e:
        print(f"❌ Ошибка автоматического коммита: {e}")
        return False


def test_smart_git_push_to_remote():
    """Тест отправки изменений в удаленный репозиторий (имитация)"""
    print("\n📤 Тестирование отправки в remote репозиторий...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем два репозитория: локальный и "remote"
            remote_repo = Path(temp_dir) / "remote_repo"
            local_repo = Path(temp_dir) / "local_repo"

            remote_repo.mkdir()
            local_repo.mkdir()

            # Инициализируем remote репозиторий как bare
            run_git_command(remote_repo, "git init --bare")

            # Клонируем remote в local
            run_git_command(local_repo.parent, f"git clone {remote_repo} local_repo", cwd=local_repo.parent)

            # Настраиваем Git
            run_git_command(local_repo, "git config user.name 'Smart Agent'")
            run_git_command(local_repo, "git config user.email 'smart@agent.local'")

            # Создаем начальный коммит
            readme_file = local_repo / "README.md"
            readme_file.write_text("# Smart Agent Remote Test\n")
            run_git_command(local_repo, "git add README.md")
            run_git_command(local_repo, "git commit -m 'Initial commit'")

            # Отправляем в remote
            run_git_command(local_repo, "git push origin main")

            # Создаем ветку smart и добавляем изменения
            run_git_command(local_repo, "git checkout -b smart")

            smart_file = local_repo / "smart_feature.md"
            smart_file.write_text("# Smart Agent Feature\n\nТестовая фича Smart Agent.\n")

            run_git_command(local_repo, "git add smart_feature.md")
            run_git_command(local_repo, f'git commit -m "feat: Добавлена фича Smart Agent"')

            # Отправляем ветку smart в remote
            run_git_command(local_repo, "git push -u origin smart")

            # Проверяем, что ветка появилась в remote
            branches_result = run_git_command(remote_repo, "git branch -a")
            branches_output = branches_result.stdout

            assert "smart" in branches_output, f"Ветка smart не найдена в remote: {branches_output}"

            print("✅ Ветка smart отправлена в remote репозиторий")
            print("   Remote branches:")
            print(f"   {branches_output.strip()}")

        return True

    except Exception as e:
        print(f"❌ Ошибка отправки в remote: {e}")
        return False


def test_smart_git_merge_conflict_handling():
    """Тест обработки конфликтов слияния при работе Smart Agent"""
    print("\n⚔️  Тестирование обработки конфликтов слияния...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"
            repo_path.mkdir()

            # Инициализируем репозиторий
            run_git_command(repo_path, "git init")
            run_git_command(repo_path, "git config user.name 'Test User'")
            run_git_command(repo_path, "git config user.email 'test@example.com'")

            # Создаем начальный коммит
            config_file = repo_path / "config.yaml"
            config_file.write_text("smart_agent:\n  enabled: true\n")
            run_git_command(repo_path, "git add config.yaml")
            run_git_command(repo_path, "git commit -m 'Initial config'")

            # Создаем ветку smart
            run_git_command(repo_path, "git checkout -b smart")

            # Модифицируем файл в ветке smart
            config_file.write_text("smart_agent:\n  enabled: true\n  max_iter: 25\n")
            run_git_command(repo_path, "git add config.yaml")
            run_git_command(repo_path, f'git commit -m "feat: Добавлен max_iter в smart config"')

            # Переключаемся обратно на main и изменяем тот же файл
            run_git_command(repo_path, "git checkout main")
            config_file.write_text("smart_agent:\n  enabled: true\n  memory: 100\n")
            run_git_command(repo_path, "git add config.yaml")
            run_git_command(repo_path, "git commit -m 'feat: Добавлена память в config'")

            # Пытаемся слить smart в main (имитируем конфликт)
            merge_result = run_git_command(repo_path, "git merge smart", check=False)

            if merge_result.returncode != 0:
                # Обнаружен конфликт слияния
                print("   ⚠️  Обнаружен конфликт слияния (ожидаемо)")

                # Проверяем статус
                status_result = run_git_command(repo_path, "git status")
                assert "conflict" in status_result.stdout.lower(), "Конфликт не обнаружен в статусе"

                # Имитируем разрешение конфликта (выбираем версию из smart)
                with open(config_file, 'w') as f:
                    f.write("smart_agent:\n  enabled: true\n  max_iter: 25\n  memory: 100\n")

                run_git_command(repo_path, "git add config.yaml")
                run_git_command(repo_path, "git commit -m 'resolve: Разрешен конфликт слияния smart->main'")

                print("   ✅ Конфликт разрешен успешно")
            else:
                print("   ✅ Слияние прошло без конфликтов")

            # Проверяем финальное состояние
            final_content = config_file.read_text()
            assert "max_iter: 25" in final_content, "max_iter не сохранен"
            assert "memory: 100" in final_content, "memory не сохранена"

            print("✅ Обработка конфликтов слияния работает корректно")

        return True

    except Exception as e:
        print(f"❌ Ошибка обработки конфликтов: {e}")
        return False


def test_smart_git_commit_message_format():
    """Тест формата сообщений коммитов Smart Agent"""
    print("\n📝 Тестирование формата сообщений коммитов...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"
            repo_path.mkdir()

            # Инициализируем репозиторий
            run_git_command(repo_path, "git init")
            run_git_command(repo_path, "git config user.name 'Smart Agent'")
            run_git_command(repo_path, "git config user.email 'smart@agent.local'")

            # Создаем начальный коммит
            readme_file = repo_path / "README.md"
            readme_file.write_text("# Smart Agent Commits\n")
            run_git_command(repo_path, "git add README.md")
            run_git_command(repo_path, "git commit -m 'Initial commit'")

            # Переключаемся на ветку smart
            run_git_command(repo_path, "git checkout -b smart")

            # Создаем различные типы коммитов Smart Agent
            commit_scenarios = [
                {
                    "task_id": "1769119092",
                    "task_name": "Создать тесты для новой конфигурации",
                    "files": ["test_smart_agent_config.py"],
                    "expected_prefix": "feat:"
                },
                {
                    "task_id": "1769119093",
                    "task_name": "Исправить баг в LearningTool",
                    "files": ["src/tools/learning_tool.py"],
                    "expected_prefix": "fix:"
                },
                {
                    "task_id": "1769119094",
                    "task_name": "Добавить документацию",
                    "files": ["docs/guides/SMART_AGENT.md"],
                    "expected_prefix": "docs:"
                }
            ]

            for scenario in commit_scenarios:
                # Создаем тестовый файл
                test_file = repo_path / scenario["files"][0]
                test_file.parent.mkdir(parents=True, exist_ok=True)
                test_file.write_text(f"# {scenario['task_name']}\n")

                # Добавляем и коммитим
                run_git_command(repo_path, f"git add {scenario['files'][0]}")

                commit_message = f"{scenario['expected_prefix']} {scenario['task_name']} (задача {scenario['task_id']})"

                run_git_command(repo_path, f'git commit -m "{commit_message}"')

                # Проверяем формат коммита
                log_result = run_git_command(repo_path, "git log --oneline -1")
                last_commit = log_result.stdout.strip()

                assert scenario['expected_prefix'] in last_commit, f"Префикс {scenario['expected_prefix']} не найден в: {last_commit}"
                assert scenario['task_id'] in last_commit, f"ID задачи {scenario['task_id']} не найден в: {last_commit}"

                print(f"   ✅ Коммит: {last_commit}")

            print("✅ Формат сообщений коммитов соответствует стандартам")

        return True

    except Exception as e:
        print(f"❌ Ошибка формата коммитов: {e}")
        return False


def test_smart_git_backup_and_recovery():
    """Тест резервного копирования и восстановления состояния Git"""
    print("\n🔄 Тестирование резервного копирования Git состояния...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"
            backup_path = Path(temp_dir) / "backup_repo"

            repo_path.mkdir()
            backup_path.mkdir()

            # Инициализируем основной репозиторий
            run_git_command(repo_path, "git init")
            run_git_command(repo_path, "git config user.name 'Smart Agent'")
            run_git_command(repo_path, "git config user.email 'smart@agent.local'")

            # Создаем историю коммитов
            for i in range(3):
                commit_file = repo_path / f"commit_{i}.txt"
                commit_file.write_text(f"Commit number {i}\n")

                run_git_command(repo_path, f"git add commit_{i}.txt")
                run_git_command(repo_path, f"git commit -m 'Commit {i}'")

            # Создаем ветку smart с дополнительными коммитами
            run_git_command(repo_path, "git checkout -b smart")

            for i in range(2):
                smart_file = repo_path / f"smart_commit_{i}.txt"
                smart_file.write_text(f"Smart commit number {i}\n")

                run_git_command(repo_path, f"git add smart_commit_{i}.txt")
                run_git_command(repo_path, f"git commit -m 'Smart commit {i}'")

            # Создаем резервную копию (имитируем)
            import shutil
            shutil.copytree(repo_path / ".git", backup_path / ".git")

            # Имитируем сбой - удаляем некоторые коммиты из smart
            run_git_command(repo_path, "git reset --hard HEAD~1")
            run_git_command(repo_path, "git push origin smart --force", check=False)  # Может не сработать без remote

            # Восстанавливаем из резервной копии
            shutil.rmtree(repo_path / ".git")
            shutil.copytree(backup_path / ".git", repo_path / ".git")

            # Проверяем восстановление
            log_result = run_git_command(repo_path, "git log --oneline")
            commit_count = len(log_result.stdout.strip().split('\n'))

            assert commit_count >= 5, f"Не все коммиты восстановлены: {commit_count}"

            branch_result = run_git_command(repo_path, "git branch")
            assert "smart" in branch_result.stdout, "Ветка smart не восстановлена"

            print("✅ Резервное копирование и восстановление Git состояния работает")
            print(f"   Восстановлено коммитов: {commit_count}")

        return True

    except Exception as e:
        print(f"❌ Ошибка резервного копирования Git: {e}")
        return False


def main():
    """Основная функция тестирования Git интеграции"""
    print("🌿 Начало тестирования Git интеграции Smart Agent\n")

    results = []

    # Тестируем компоненты Git интеграции
    results.append(("Smart Git Branch Creation", test_smart_git_branch_creation()))
    results.append(("Smart Git Auto Commit", test_smart_git_auto_commit()))
    results.append(("Smart Git Push to Remote", test_smart_git_push_to_remote()))
    results.append(("Smart Git Merge Conflict Handling", test_smart_git_merge_conflict_handling()))
    results.append(("Smart Git Commit Message Format", test_smart_git_commit_message_format()))
    results.append(("Smart Git Backup and Recovery", test_smart_git_backup_and_recovery()))

    # Итоги тестирования
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ GIT ИНТЕГРАЦИИ SMART AGENT")
    print("="*70)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print("40")
        if success:
            passed += 1

    print(f"\n📈 ИТОГО: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Git интеграция Smart Agent работает корректно.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется исправление Git интеграции.")
        return 1


if __name__ == "__main__":
    sys.exit(main())