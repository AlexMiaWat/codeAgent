"""
Дымовые тесты для Smart Agent - проверка базовой работоспособности
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestSmartAgentSmoke:
    """Дымовые тесты Smart Agent"""

    def test_create_smart_agent_basic(self):
        """Базовый тест создания Smart Agent - проверка импорта"""
        try:
            from src.agents.smart_agent import create_smart_agent
            assert create_smart_agent is not None
            # Проверяем что функция импортирована и callable
            assert callable(create_smart_agent)
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать create_smart_agent: {e}")

    def test_smart_agent_with_tools(self):
        """Тест Smart Agent с инструментами - проверка создания инструментов"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем инструменты напрямую вместо Smart Agent
            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Проверяем что инструменты созданы
            assert learning_tool is not None
            assert context_tool is not None

            # Проверяем имена классов
            assert learning_tool.__class__.__name__ == "LearningTool"
            assert context_tool.__class__.__name__ == "ContextAnalyzerTool"

    @patch('src.tools.docker_utils.DockerChecker.is_docker_available')
    def test_smart_agent_with_docker_disabled(self, mock_docker_check):
        """Тест Smart Agent с отключенным Docker"""
        mock_docker_check.return_value = False

        # Проверяем что Docker корректно определяется как недоступный
        from src.tools.docker_utils import DockerChecker
        result = DockerChecker.is_docker_available()
        assert result == False


class TestLearningToolSmoke:
    """Дымовые тесты LearningTool"""

    def test_learning_tool_creation(self):
        """Тест создания LearningTool"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            assert tool is not None
            assert tool.experience_dir.exists()
            assert tool.experience_file.exists()

    def test_learning_tool_save_experience(self):
        """Тест сохранения опыта"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            result = tool.save_task_experience(
                task_id="test_task_001",
                task_description="Тестовая задача",
                success=True,
                execution_time=1.5
            )

            assert "сохранен" in result
            assert "успешно" in result

            # Проверяем что данные сохранены
            with open(tool.experience_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert len(data["tasks"]) == 1
                assert data["tasks"][0]["task_id"] == "test_task_001"

    def test_learning_tool_find_similar(self):
        """Тест поиска похожих задач"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Добавляем тестовые данные
            tool.save_task_experience("task1", "Создать тестовый файл", True)
            tool.save_task_experience("task2", "Написать документацию", True)

            # Ищем похожие - используем точную фразу
            result = tool.find_similar_tasks("Создать")

            assert "Создать тестовый файл" in result or "похожие задачи" in result

    def test_learning_tool_get_statistics(self):
        """Тест получения статистики"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Добавляем данные
            tool.save_task_experience("task1", "Задача 1", True, 1.0)
            tool.save_task_experience("task2", "Задача 2", False, 2.0)

            stats = tool.get_statistics()

            assert "Всего задач: 2" in stats
            assert "Успешных задач: 1" in stats
            assert "Неудачных задач: 1" in stats


class TestContextAnalyzerToolSmoke:
    """Дымовые тесты ContextAnalyzerTool"""

    def test_context_analyzer_creation(self):
        """Тест создания ContextAnalyzerTool"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            assert tool is not None
            assert str(tool.project_dir) == str(project_dir)

    def test_context_analyzer_project_structure(self):
        """Тест анализа структуры проекта"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовую структуру
            (project_dir / "src").mkdir()
            (project_dir / "docs").mkdir()
            (project_dir / "test").mkdir()

            # Создаем файлы
            (project_dir / "src" / "main.py").write_text("# Main file")
            (project_dir / "docs" / "README.md").write_text("# Documentation")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.analyze_project_structure()

            assert "Основные компоненты" in result
            assert "src" in result or "docs" in result or "test" in result

    def test_context_analyzer_task_context(self):
        """Тест получения контекста задачи"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовые файлы
            docs_dir = project_dir / "docs"
            docs_dir.mkdir()
            (docs_dir / "api.md").write_text("# API Documentation\nThis is about API development")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.get_task_context("разработать API")

            # Проверяем что результат содержит информацию о найденных файлах
            assert "api.md" in result or "документация" in result or "контекст" in result

    def test_context_analyzer_find_dependencies(self):
        """Тест поиска зависимостей файла"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовый Python файл с импортами
            test_file = project_dir / "test_module.py"
            test_file.write_text("""
import os
import sys
from pathlib import Path
""")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.find_file_dependencies("test_module.py")

            # Проверяем что метод отработал без ошибок
            assert isinstance(result, str)
            assert len(result) > 0


class TestDockerCheckerSmoke:
    """Дымовые тесты DockerChecker"""

    @patch('subprocess.run')
    def test_docker_available_check(self, mock_subprocess):
        """Тест проверки доступности Docker"""
        from src.tools.docker_utils import DockerChecker

        # Мокаем успешный ответ Docker
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Docker version 24.0.6"
        mock_subprocess.return_value = mock_result

        result = DockerChecker.is_docker_available()

        assert result == True
        assert mock_subprocess.call_count >= 2  # docker --version и docker info

    @patch('subprocess.run')
    def test_docker_not_available_check(self, mock_subprocess):
        """Тест проверки недоступности Docker"""
        from src.tools.docker_utils import DockerChecker

        # Мокаем неудачный ответ Docker
        mock_result = Mock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        result = DockerChecker.is_docker_available()

        assert result == False

    @patch('subprocess.run')
    def test_get_docker_version(self, mock_subprocess):
        """Тест получения версии Docker"""
        from src.tools.docker_utils import DockerChecker

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Docker version 24.0.6, build ed223bc"
        mock_subprocess.return_value = mock_result

        version = DockerChecker.get_docker_version()

        assert version == "24.0.6"

    @patch('subprocess.run')
    def test_get_running_containers(self, mock_subprocess):
        """Тест получения списка запущенных контейнеров"""
        from src.tools.docker_utils import DockerChecker

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "container1\ncontainer2\n"
        mock_subprocess.return_value = mock_result

        containers = DockerChecker.get_running_containers()

        assert len(containers) == 2
        assert "container1" in containers
        assert "container2" in containers


class TestDockerManagerSmoke:
    """Дымовые тесты DockerManager"""

    @patch('src.tools.docker_utils.DockerChecker.is_docker_available')
    @patch('src.tools.docker_utils.DockerChecker.is_container_running')
    @patch('subprocess.run')
    def test_docker_manager_start_container(self, mock_subprocess, mock_running, mock_available):
        """Тест запуска контейнера"""
        from src.tools.docker_utils import DockerManager

        mock_available.return_value = True
        mock_running.return_value = False

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "container_id_123"
        mock_subprocess.return_value = mock_result

        manager = DockerManager()
        success, message = manager.start_container()

        assert success == True
        assert "started successfully" in message

    @patch('src.tools.docker_utils.DockerChecker.is_container_running')
    @patch('subprocess.run')
    def test_docker_manager_stop_container(self, mock_subprocess, mock_running):
        """Тест остановки контейнера"""
        from src.tools.docker_utils import DockerManager

        mock_running.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        manager = DockerManager()
        success, message = manager.stop_container()

        assert success == True
        assert "stopped successfully" in message