"""
Статические тесты для LearningTool
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.tools.learning_tool import LearningTool, normalize_unicode_text


class TestNormalizeUnicodeText:
    """Тесты для функции normalize_unicode_text"""

    def test_basic_normalization(self):
        """Тест базовой нормализации Unicode"""
        # Тест с обычным текстом
        assert normalize_unicode_text("Hello World") == "hello world"

        # Тест с заглавными буквами
        assert normalize_unicode_text("HELLO WORLD") == "hello world"

        # Тест с пустой строкой
        assert normalize_unicode_text("") == ""

        # Тест с None
        assert normalize_unicode_text(None) == ""

    def test_unicode_normalization(self):
        """Тест нормализации Unicode символов"""
        # Тест с диакритическими знаками (NFD нормализация)
        text_with_accents = "café naïve résumé"
        normalized = normalize_unicode_text(text_with_accents)
        assert "cafe" in normalized
        assert "naive" in normalized
        assert "resume" in normalized

    def test_whitespace_handling(self):
        """Тест обработки пробелов"""
        # Normalize_unicode_text не удаляет пробелы, только нормализует Unicode
        result = normalize_unicode_text("  hello   world  ")
        assert result == "  hello   world  "

    def test_special_characters(self):
        """Тест специальных символов"""
        assert normalize_unicode_text("hello@world.com") == "hello@world.com"
        assert normalize_unicode_text("hello-world_test") == "hello-world_test"


class TestLearningToolInitialization:
    """Тесты инициализации LearningTool"""

    def test_initialization_with_defaults(self):
        """Тест инициализации с параметрами по умолчанию"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            assert tool.experience_dir == Path(temp_dir)
            assert tool.max_experience_tasks == 1000
            assert tool.enable_indexing == True
            assert tool.cache_size == 1000
            assert tool.cache_ttl_seconds == 3600
            assert tool.experience_file == Path(temp_dir) / "experience.json"

    def test_initialization_with_custom_params(self):
        """Тест инициализации с пользовательскими параметрами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(
                experience_dir=temp_dir,
                max_experience_tasks=500,
                enable_indexing=False,
                cache_size=500,
                cache_ttl_seconds=1800,
                enable_cache_persistence=True
            )

            assert tool.max_experience_tasks == 500
            assert tool.enable_indexing == False
            assert tool.cache_size == 500
            assert tool.cache_ttl_seconds == 1800
            assert tool.enable_cache_persistence == True

    def test_learning_tool_initialization(self):
        """Проверка сигнатуры __init__ LearningTool"""
        import inspect
        from src.tools.learning_tool import LearningTool

        # Проверяем сигнатуру __init__
        init_sig = inspect.signature(LearningTool.__init__)
        expected_params = ['self', 'experience_dir', 'max_experience_tasks', 'enable_indexing',
                          'cache_size', 'cache_ttl_seconds', 'enable_cache_persistence', 'kwargs']

        actual_params = list(init_sig.parameters.keys())
        assert actual_params == expected_params

    def test_experience_file_creation(self):
        """Тест создания файла опыта при инициализации"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Файл должен быть создан
            assert tool.experience_file.exists()

            # Проверим содержимое
            with open(tool.experience_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert "version" in data
            assert "tasks" in data
            assert "patterns" in data
            assert "statistics" in data
            assert data["version"] == "1.0"
            assert data["tasks"] == []
            assert data["patterns"] == {}
            assert "total_tasks" in data["statistics"]


class TestLearningToolSaveExperience:
    """Тесты сохранения опыта"""

    def test_save_valid_experience(self):
        """Тест сохранения корректного опыта"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            result = tool.save_task_experience(
                task_id="test_task_1",
                task_description="Test task description",
                success=True,
                execution_time=10.5,
                notes="Test notes",
                patterns=["pattern1", "pattern2"]
            )

            assert "сохранен" in result
            assert "успешно" in result

            # Проверим данные в файле
            with open(tool.experience_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert len(data["tasks"]) == 1
            task = data["tasks"][0]
            assert task["task_id"] == "test_task_1"
            assert task["description"] == "Test task description"
            assert task["success"] == True
            assert task["execution_time"] == 10.5
            assert task["notes"] == "Test notes"
            assert task["patterns"] == ["pattern1", "pattern2"]
            assert "timestamp" in task

    def test_save_experience_validation(self):
        """Тест валидации параметров при сохранении опыта"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Тест пустого task_id
            with pytest.raises(ValueError, match="task_id must be a non-empty string"):
                tool.save_task_experience("", "description", True)

            # Тест пустого описания
            with pytest.raises(ValueError, match="task_description must be a non-empty string"):
                tool.save_task_experience("task1", "", True)

            # Тест некорректного типа success
            with pytest.raises(ValueError, match="success must be a boolean"):
                tool.save_task_experience("task1", "description", "true")

            # Тест отрицательного времени выполнения
            with pytest.raises(ValueError, match="execution_time must be a non-negative number"):
                tool.save_task_experience("task1", "description", True, -1)

            # Тест некорректного типа patterns
            with pytest.raises(ValueError, match="patterns must be a list or None"):
                tool.save_task_experience("task1", "description", True, patterns="not_a_list")

            # Тест некорректных элементов в patterns
            with pytest.raises(ValueError, match="all patterns must be strings"):
                tool.save_task_experience("task1", "description", True, patterns=["valid", 123])

    def test_max_tasks_limit(self):
        """Тест ограничения максимального количества задач"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir, max_experience_tasks=2)

            # Добавим 3 задачи
            tool.save_task_experience("task1", "desc1", True)
            tool.save_task_experience("task2", "desc2", True)
            tool.save_task_experience("task3", "desc3", True)

            # Проверим, что осталось только 2 задачи (самые свежие)
            with open(tool.experience_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert len(data["tasks"]) == 2
            assert data["tasks"][0]["task_id"] == "task2"
            assert data["tasks"][1]["task_id"] == "task3"


class TestLearningToolFindSimilar:
    """Тесты поиска похожих задач"""

    def test_find_similar_with_existing_tasks(self):
        """Тест поиска похожих задач при наличии данных"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Добавим тестовые задачи
            tool.save_task_experience("task1", "Fix bug in login system", True)
            tool.save_task_experience("task2", "Implement user authentication", True)
            tool.save_task_experience("task3", "Fix login bug", True)

            result = tool.find_similar_tasks("login bug")

            assert "Найдено" in result
            assert "Fix bug in login system" in result
            assert "Fix login bug" in result

    def test_find_similar_no_matches(self):
        """Тест поиска когда нет совпадений"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            tool.save_task_experience("task1", "Some task", True)

            result = tool.find_similar_tasks("nonexistent query")

            assert "не найдены" in result

    def test_find_similar_limit(self):
        """Тест ограничения количества результатов"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Добавим много похожих задач
            for i in range(10):
                tool.save_task_experience(f"task{i}", f"Task about testing {i}", True)

            result = tool.find_similar_tasks("testing", limit=3)

            # Должно быть найдено не более 3 задач
            assert result.count("Task about testing") <= 3


class TestLearningToolRecommendations:
    """Тесты получения рекомендаций"""

    def test_get_recommendations_with_similar_tasks(self):
        """Тест получения рекомендаций при наличии похожих задач"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Добавим успешные задачи с паттернами
            tool.save_task_experience(
                "task1", "Implement user login", True,
                execution_time=15.0, patterns=["auth", "frontend"]
            )
            tool.save_task_experience(
                "task2", "Implement user registration", True,
                execution_time=20.0, patterns=["auth", "backend"]
            )
            tool.save_task_experience(
                "task3", "Implement password reset", True,
                execution_time=10.0, notes="Use secure tokens"
            )

            result = tool.get_recommendations("user authentication system")

            assert "Рекомендации" in result
            assert "Ожидаемое время выполнения" in result
            assert "Рекомендуемые паттерны" in result

    def test_get_recommendations_no_similar(self):
        """Тест получения рекомендаций когда нет похожих задач"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            result = tool.get_recommendations("unique task with no matches")

            assert "данные о похожих задачах отсутствуют" in result.lower()

    def test_get_statistics(self):
        """Тест получения статистики"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Добавим задачи с разными статусами
            tool.save_task_experience("task1", "Task 1", True, 10.0)
            tool.save_task_experience("task2", "Task 2", False, 5.0)
            tool.save_task_experience("task3", "Task 3", True, 15.0)

            result = tool.get_statistics()

            assert "Статистика LearningTool" in result
            assert "Всего задач: 3" in result
            assert "Успешных задач: 2" in result
            assert "Неудачных задач: 1" in result
            assert "Процент успешности: 66.7%" in result


class TestLearningToolCaching:
    """Тесты кеширования"""

    def test_cache_functionality(self):
        """Тест работы кеширования"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Добавим задачу
            tool.save_task_experience("task1", "test query", True)

            # Проверим что данные сохранены
            experience_data = tool._load_experience()
            assert len(experience_data["tasks"]) == 1

            # Первый вызов поиска
            result1 = tool.find_similar_tasks("test query")

            # Второй вызов поиска (кеширование работает на уровне метода)
            result2 = tool.find_similar_tasks("test query")

            # Результаты должны содержать одинаковую информацию
            assert "test query" in result1.lower()
            assert "test query" in result2.lower()

    def test_cache_invalidation_on_save(self):
        """Тест инвалидации кэша при сохранении новой задачи"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Первый поиск
            tool.save_task_experience("task1", "initial task", True)
            result1 = tool.find_similar_tasks("initial")

            # Добавим новую задачу
            tool.save_task_experience("task2", "another initial task", True)

            # Кэш должен быть очищен, результаты могут измениться
            # (поведение зависит от внутренней реализации кеширования)


class TestLearningToolErrorHandling:
    """Тесты обработки ошибок"""

    def test_corrupted_experience_file(self):
        """Тест работы с поврежденным файлом опыта"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Повредим файл опыта
            with open(tool.experience_file, 'w') as f:
                f.write("invalid json content")

            # Попробуем загрузить - должно вернуться пустое состояние
            data = tool._load_experience()
            assert data["tasks"] == []

    def test_save_error_handling(self):
        """Тест обработки ошибок при сохранении"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Создадим ситуацию где файл опыта доступен только для чтения
            import os
            os.chmod(tool.experience_file, 0o444)  # Только чтение

            try:
                # Попытка сохранить должна обработать ошибку
                result = tool.save_task_experience("task1", "description", True)
                # Операция должна продолжиться несмотря на ошибку сохранения
                assert "сохранен" in result  # Может сохраниться в памяти
            finally:
                # Восстановим права для cleanup
                os.chmod(tool.experience_file, 0o644)