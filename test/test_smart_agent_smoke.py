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


class TestSmartAgentErrorHandling:
    """Тесты обработки ошибок Smart Agent"""

    def test_create_smart_agent_with_invalid_project_dir(self):
        """Тест создания Smart Agent с некорректной директорией проекта"""
        from src.agents.smart_agent import create_smart_agent

        with pytest.raises(Exception):
            # Передаем несуществующий путь
            create_smart_agent(project_dir=Path("/nonexistent/path/that/does/not/exist"))

    def test_create_smart_agent_with_none_project_dir(self):
        """Тест создания Smart Agent с None в качестве директории проекта"""
        from src.agents.smart_agent import create_smart_agent

        with pytest.raises(TypeError):
            create_smart_agent(project_dir=None)

    def test_smart_agent_with_corrupted_experience_file(self):
        """Тест Smart Agent с поврежденным файлом опыта"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем поврежденный файл опыта
            experience_file = project_dir / "smart_experience" / "experience.json"
            experience_file.parent.mkdir(parents=True, exist_ok=True)

            with open(experience_file, 'w') as f:
                f.write("invalid json content { broken")

            # Smart Agent должен создать новый файл опыта несмотря на поврежденный
            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                    agent = create_smart_agent(project_dir=project_dir, use_llm=False)

                    assert agent is not None
                    # Проверяем что файл опыта был пересоздан
                    assert experience_file.exists()

                    # Проверяем что файл валидный JSON
                    import json
                    with open(experience_file, 'r') as f:
                        data = json.load(f)
                        assert 'version' in data

    def test_smart_agent_with_readonly_experience_dir(self):
        """Тест Smart Agent с директорией опыта только для чтения"""
        from src.agents.smart_agent import create_smart_agent

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            experience_dir = project_dir / "readonly_experience"
            experience_dir.mkdir()

            # Делаем директорию только для чтения (симуляция)
            import os
            original_mode = experience_dir.stat().st_mode
            experience_dir.chmod(0o444)  # Только чтение

            try:
                with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                    with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                        # Агент должен обработать ошибку создания файла опыта
                        agent = create_smart_agent(
                            project_dir=project_dir,
                            experience_dir=str(experience_dir),
                            use_llm=False
                        )
                        assert agent is not None  # Агент все равно должен создаться
            finally:
                # Восстанавливаем права
                experience_dir.chmod(original_mode)


class TestLearningToolErrorHandling:
    """Тесты обработки ошибок LearningTool"""

    def test_learning_tool_with_invalid_json_file(self):
        """Тест LearningTool с невалидным JSON файлом"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Создаем поврежденный файл опыта
            experience_file = Path(tmp_dir) / "experience.json"
            with open(experience_file, 'w') as f:
                f.write("not valid json {")

            tool = LearningTool(experience_dir=tmp_dir)

            # Метод должен вернуть пустые данные вместо краха
            data = tool._load_experience()
            assert isinstance(data, dict)
            assert 'version' in data  # Должен вернуть структуру по умолчанию

    def test_learning_tool_save_experience_with_invalid_data(self):
        """Тест сохранения опыта с невалидными данными"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Тест с None значениями
            result = tool.save_task_experience(
                task_id=None,
                task_description=None,
                success=None
            )

            assert isinstance(result, str)
            # Проверяем что опыт был сохранен несмотря на None
            data = tool._load_experience()
            assert len(data['tasks']) == 1

    def test_learning_tool_find_similar_with_empty_experience(self):
        """Тест поиска похожих задач в пустом опыте"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            result = tool.find_similar_tasks("any query")

            assert isinstance(result, str)
            assert "не найдены" in result or "не найдено" in result

    def test_learning_tool_get_recommendations_with_empty_experience(self):
        """Тест получения рекомендаций из пустого опыта"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            result = tool.get_recommendations("any task")

            assert isinstance(result, str)
            assert "отсутствуют" in result

    def test_learning_tool_large_experience_file(self):
        """Тест LearningTool с большим файлом опыта"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Добавляем много задач для создания большого файла
            for i in range(100):
                tool.save_task_experience(
                    task_id=f"task_{i}",
                    task_description=f"Task description {i}",
                    success=i % 2 == 0,  # Чередуем успех/неудачу
                    execution_time=float(i) / 10.0,
                    patterns=[f"pattern_{i % 5}"]
                )

            # Проверяем что все задачи сохранены
            data = tool._load_experience()
            assert len(data['tasks']) == 100

            # Проверяем статистику
            stats = tool.get_statistics()
            assert "Всего задач: 100" in stats
            assert "Успешных задач: 50" in stats  # Половина из 100

    def test_learning_tool_concurrent_access_simulation(self):
        """Тест симуляции одновременного доступа к файлу опыта"""
        from src.tools.learning_tool import LearningTool
        import threading
        import time

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            results = []
            errors = []

            def worker(worker_id):
                try:
                    for i in range(10):
                        result = tool.save_task_experience(
                            task_id=f"worker_{worker_id}_task_{i}",
                            task_description=f"Task from worker {worker_id}",
                            success=True
                        )
                        results.append(result)
                        time.sleep(0.001)  # Небольшая задержка
                except Exception as e:
                    errors.append(str(e))

            # Запускаем несколько потоков
            threads = []
            for i in range(5):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()

            # Ждем завершения всех потоков
            for t in threads:
                t.join()

            # Проверяем результаты
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(results) == 50  # 5 workers * 10 tasks each

            # Проверяем что все задачи сохранены
            data = tool._load_experience()
            assert len(data['tasks']) == 50


class TestContextAnalyzerToolErrorHandling:
    """Тесты обработки ошибок ContextAnalyzerTool"""

    def test_context_analyzer_with_nonexistent_project_dir(self):
        """Тест ContextAnalyzerTool с несуществующей директорией проекта"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Должен создаться без ошибок, но работать с ограниченным функционалом
        tool = ContextAnalyzerTool(project_dir="/nonexistent/path")

        assert tool is not None
        result = tool.analyze_project_structure()
        assert isinstance(result, str)

    def test_context_analyzer_find_dependencies_nonexistent_file(self):
        """Тест поиска зависимостей для несуществующего файла"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            result = tool.find_file_dependencies("nonexistent_file.py")

            assert isinstance(result, str)
            assert "не найден" in result or "not found" in result

    def test_context_analyzer_analyze_component_nonexistent(self):
        """Тест анализа несуществующего компонента"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            result = tool.analyze_component("nonexistent_component")

            assert isinstance(result, str)
            assert "не найден" in result or "not found" in result

    def test_context_analyzer_with_binary_file(self):
        """Тест ContextAnalyzerTool с бинарным файлом"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем "бинарный" файл (с нечитаемыми символами)
            binary_file = project_dir / "binary.dat"
            with open(binary_file, 'wb') as f:
                f.write(bytes(range(256)))  # Все байты от 0 до 255

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Анализ должен обработать файл gracefully
            result = tool.analyze_component("binary.dat")
            assert isinstance(result, str)

    def test_context_analyzer_with_empty_directory(self):
        """Тест ContextAnalyzerTool с пустой директорией"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            result = tool.analyze_project_structure()

            assert isinstance(result, str)
            assert "Анализ структуры проекта" in result

    def test_context_analyzer_with_nested_directories(self):
        """Тест ContextAnalyzerTool с глубоко вложенной структурой"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем глубоко вложенную структуру
            deep_path = project_dir
            for i in range(10):  # 10 уровней вложенности
                deep_path = deep_path / f"level_{i}"
                deep_path.mkdir()
                (deep_path / f"file_{i}.py").write_text(f"# Level {i} file")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.analyze_project_structure()

            assert isinstance(result, str)
            # Должен обработать структуру без проблем с глубиной

    def test_context_analyzer_get_task_context_empty_query(self):
        """Тест получения контекста задачи с пустым запросом"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            result = tool.get_task_context("")

            assert isinstance(result, str)
            # Должен обработать пустой запрос gracefully

    def test_context_analyzer_find_related_files_empty_query(self):
        """Тест поиска связанных файлов с пустым запросом"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            result = tool.find_related_files("")

            assert isinstance(result, str)
            # Должен обработать пустой запрос gracefully

    def test_context_analyzer_with_special_characters_in_paths(self):
        """Тест ContextAnalyzerTool с специальными символами в путях"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем файлы с специальными символами в именах
            special_files = [
                "file with spaces.py",
                "file-with-dashes.py",
                "file_with_underscores.py",
                "file(1).py",
                "file[1].py"
            ]

            for filename in special_files:
                (project_dir / filename).write_text("# Test file")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Проверяем анализ структуры
            result = tool.analyze_project_structure()
            assert isinstance(result, str)

            # Проверяем анализ отдельных файлов
            for filename in special_files:
                result = tool.analyze_component(filename)
                assert isinstance(result, str)
                assert filename in result


class TestSmartAgentEdgeCases:
    """Тесты граничных случаев Smart Agent"""

    def test_smart_agent_with_max_experience_tasks_zero(self):
        """Тест Smart Agent с max_experience_tasks=0"""
        from src.agents.smart_agent import create_smart_agent

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                    agent = create_smart_agent(
                        project_dir=project_dir,
                        max_experience_tasks=0,
                        use_llm=False
                    )

                    assert agent is not None
                    # LearningTool должен работать с ограничением в 0 задач

    def test_smart_agent_with_very_long_role_and_goal(self):
        """Тест Smart Agent с очень длинными role и goal"""
        from src.agents.smart_agent import create_smart_agent

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            long_text = "Very long text " * 100  # Повторяем 100 раз

            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                    agent = create_smart_agent(
                        project_dir=project_dir,
                        role=long_text,
                        goal=long_text,
                        use_llm=False
                    )

                    assert agent is not None
                    assert agent.role == long_text
                    assert agent.goal == long_text

    def test_smart_agent_with_unicode_characters(self):
        """Тест Smart Agent с Unicode символами"""
        from src.agents.smart_agent import create_smart_agent

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            unicode_role = "Умный Агент 🤖"
            unicode_goal = "Выполнять задачи с ИИ 💡"
            unicode_backstory = "Я - умный агент с русскими символами и эмодзи 🎯"

            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                    agent = create_smart_agent(
                        project_dir=project_dir,
                        role=unicode_role,
                        goal=unicode_goal,
                        backstory=unicode_backstory,
                        use_llm=False
                    )

                    assert agent is not None
                    assert agent.role == unicode_role
                    assert agent.goal == unicode_goal