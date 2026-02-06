"""
Тесты для git_utils
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from git_utils import (
    execute_git_command,
    get_current_branch,
    get_last_commit_info,
    check_commit_exists,
    check_uncommitted_changes,
    check_unpushed_commits,
    push_to_remote,
    auto_push_after_commit,
    GitError
)


class TestGitUtils:
    """Тесты для функций git_utils"""

    @pytest.fixture
    def temp_git_dir(self, tmp_path):
        """Создает временную директорию с git репозиторием"""
        git_dir = tmp_path / "test_repo"
        git_dir.mkdir()

        # Инициализируем git репозиторий
        import subprocess
        subprocess.run(["git", "init"], cwd=git_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=git_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=git_dir, check=True)

        # Создаем начальный коммит
        test_file = git_dir / "test.txt"
        test_file.write_text("test content")
        subprocess.run(["git", "add", "test.txt"], cwd=git_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_dir, check=True)

        return git_dir

    def test_execute_git_command_success(self):
        """Тест успешного выполнения git команды"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "success output"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            success, stdout, stderr = execute_git_command(["git", "status"])

            assert success is True
            assert stdout == "success output"
            assert stderr == ""
            mock_run.assert_called_once()

    def test_execute_git_command_failure(self):
        """Тест неуспешного выполнения git команды"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "error message"
            mock_run.return_value = mock_result

            success, stdout, stderr = execute_git_command(["git", "invalid"])

            assert success is False
            assert stdout == ""
            assert stderr == "error message"

    def test_get_current_branch(self, temp_git_dir):
        """Тест получения текущей ветки"""
        branch = get_current_branch(temp_git_dir)
        assert branch is not None
        assert isinstance(branch, str)

    def test_get_last_commit_info(self, temp_git_dir):
        """Тест получения информации о последнем коммите"""
        commit_info = get_last_commit_info(temp_git_dir)

        assert commit_info is not None
        assert isinstance(commit_info, dict)
        assert 'hash_full' in commit_info
        assert 'message' in commit_info

    def test_check_commit_exists(self, temp_git_dir):
        """Тест проверки существования коммита"""
        # Получаем хэш существующего коммита
        commit_info = get_last_commit_info(temp_git_dir)
        commit_hash = commit_info['hash_full']

        # Проверяем существующий коммит
        assert check_commit_exists(commit_hash, temp_git_dir) is True

        # Проверяем несуществующий коммит
        assert check_commit_exists("nonexistent", temp_git_dir) is False

    def test_check_uncommitted_changes_no_changes(self, temp_git_dir):
        """Тест проверки некоммитнутых изменений (без изменений)"""
        has_changes = check_uncommitted_changes(temp_git_dir)
        assert has_changes is False

    def test_check_uncommitted_changes_with_changes(self, temp_git_dir):
        """Тест проверки некоммитнутых изменений (с изменениями)"""
        # Добавляем новый файл
        new_file = temp_git_dir / "new_file.txt"
        new_file.write_text("new content")

        has_changes = check_uncommitted_changes(temp_git_dir)
        assert has_changes is True

    def test_check_unpushed_commits(self, temp_git_dir):
        """Тест проверки неотправленных коммитов"""
        # В локальном репозитории без remote коммитов нет
        has_unpushed = check_unpushed_commits(temp_git_dir)
        assert has_unpushed is False

    @patch('git_utils.execute_git_command')
    def test_push_to_remote_success(self, mock_execute):
        """Тест успешной отправки в remote"""
        mock_execute.return_value = (True, "pushed successfully", "")

        success, stdout, stderr = push_to_remote("origin", "main", Path("/tmp"))

        assert success is True
        assert stdout == "pushed successfully"
        assert stderr == ""

    @patch('git_utils.execute_git_command')
    def test_push_to_remote_failure(self, mock_execute):
        """Тест неуспешной отправки в remote"""
        mock_execute.return_value = (False, "", "push failed")

        success, stdout, stderr = push_to_remote("origin", "main", Path("/tmp"))

        assert success is False
        assert stdout == ""
        assert stderr == "push failed"

    @patch('git_utils.check_unpushed_commits')
    @patch('git_utils.push_to_remote')
    def test_auto_push_after_commit_with_unpushed(self, mock_push, mock_check):
        """Тест авто-push при наличии неотправленных коммитов"""
        mock_check.return_value = True
        mock_push.return_value = (True, "pushed", "")

        result = auto_push_after_commit(Path("/tmp"))

        assert result["success"] is True
        assert result["push_success"] is True
        mock_push.assert_called_once()

    @patch('git_utils.check_unpushed_commits')
    def test_auto_push_after_commit_no_unpushed(self, mock_check):
        """Тест авто-push при отсутствии неотправленных коммитов"""
        mock_check.return_value = False

        result = auto_push_after_commit(Path("/tmp"))

        assert result["success"] is True
        assert result["push_success"] is False


class TestGitError:
    """Тесты для GitError исключения"""

    def test_git_error_creation(self):
        """Тест создания GitError"""
        error = GitError("Test error message")
        assert str(error) == "Test error message"

    def test_git_error_inheritance(self):
        """Тест наследования GitError"""
        error = GitError("Test")
        assert isinstance(error, Exception)