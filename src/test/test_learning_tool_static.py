"""
Статические тесты для LearningTool - проверка структуры данных, API, форматов
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock
import inspect


class TestLearningToolStatic:
    """Статические тесты LearningTool"""

    def test_learning_tool_class_attributes(self):
        """Проверка атрибутов класса LearningTool"""
        from src.tools.learning_tool import LearningTool

        # Проверяем поля Pydantic модели (только определенные в нашем классе)
        model_fields = LearningTool.model_fields
        assert 'name' in model_fields
        assert 'description' in model_fields
        assert 'experience_dir' in model_fields
        assert 'max_experience_tasks' in model_fields
        assert 'experience_file' in model_fields

        # Создаем экземпляр для проверки значений
        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            assert tool.name == "LearningTool"
            # Проверяем наличие ключевых слов в описании
            description_lower = tool.description.lower()
            assert "learning" in description_lower or "обучение" in description_lower
            assert "experience" in description_lower or "опыт" in description_lower
            assert tool.max_experience_tasks == 1000

    def test_learning_tool_initialization(self):
        """Проверка инициализации LearningTool"""
        from src.tools.learning_tool import LearningTool
        import inspect

        # Проверяем сигнатуру __init__
        init_sig = inspect.signature(LearningTool.__init__)
        expected_params = ['self', 'experience_dir', 'max_experience_tasks', 'enable_indexing', 'cache_size', 'cache_ttl_seconds', 'enable_cache_persistence', 'kwargs']

        actual_params = list(init_sig.parameters.keys())
        assert actual_params == expected_params

        # Проверяем типы параметров
        params = init_sig.parameters
        assert params['experience_dir'].annotation == str
        assert params['max_experience_tasks'].annotation == int

    def test_learning_tool_experience_file_structure(self):
        """Проверка структуры файла опыта"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Проверяем что файл опыта создан
            assert tool.experience_file.exists()

            # Проверяем структуру JSON
            with open(tool.experience_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Проверяем обязательные поля
            required_fields = ['version', 'tasks', 'patterns', 'statistics']
            for field in required_fields:
                assert field in data

            # Проверяем типы полей
            assert isinstance(data['version'], str)
            assert isinstance(data['tasks'], list)
            assert isinstance(data['patterns'], dict)
            assert isinstance(data['statistics'], dict)

    def test_learning_tool_initial_experience_structure(self):
        """Проверка структуры начального опыта"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            data = tool._load_experience()

            # Проверяем начальную структуру statistics
            stats = data['statistics']
            required_stats = ['total_tasks', 'successful_tasks', 'failed_tasks', 'average_execution_time']
            for stat in required_stats:
                assert stat in stats
                assert isinstance(stats[stat], (int, float))

            # Проверяем начальные значения
            assert stats['total_tasks'] == 0
            assert stats['successful_tasks'] == 0
            assert stats['failed_tasks'] == 0
            assert stats['average_execution_time'] == 0

    def test_save_task_experience_method_signature(self):
        """Проверка сигнатуры метода save_task_experience"""
        from src.tools.learning_tool import LearningTool
        import inspect

        sig = inspect.signature(LearningTool.save_task_experience)
        expected_params = ['self', 'task_id', 'task_description', 'success',
                          'execution_time', 'notes', 'patterns']

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

        # Проверяем типы параметров
        params = sig.parameters
        assert params['task_id'].annotation == str
        assert params['task_description'].annotation == str
        assert params['success'].annotation == bool
        assert params['execution_time'].annotation == Optional[float]
        assert params['notes'].annotation == str
        assert params['patterns'].annotation == List[str]

    def test_save_task_experience_return_type(self):
        """Проверка типа возвращаемого значения save_task_experience"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            result = tool.save_task_experience(
                task_id="test_task",
                task_description="Test task",
                success=True
            )

            assert isinstance(result, str)
            assert "сохранен" in result

    def test_save_task_experience_data_structure(self):
        """Проверка структуры сохраняемых данных задачи"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            task_id = "test_task_123"
            task_desc = "Test description"
            success = True
            exec_time = 2.5
            notes = "Test notes"
            patterns = ["pattern1", "pattern2"]

            tool.save_task_experience(
                task_id=task_id,
                task_description=task_desc,
                success=success,
                execution_time=exec_time,
                notes=notes,
                patterns=patterns
            )

            # Проверяем сохраненные данные
            data = tool._load_experience()
            assert len(data['tasks']) == 1

            task = data['tasks'][0]
            required_fields = ['task_id', 'description', 'success', 'execution_time',
                             'timestamp', 'notes', 'patterns']

            for field in required_fields:
                assert field in task

            # Проверяем значения
            assert task['task_id'] == task_id
            assert task['description'] == task_desc
            assert task['success'] == success
            assert task['execution_time'] == exec_time
            assert task['notes'] == notes
            assert task['patterns'] == patterns

            # Проверяем timestamp
            assert 'T' in task['timestamp']  # ISO format

    def test_find_similar_tasks_method_signature(self):
        """Проверка сигнатуры метода find_similar_tasks"""
        from src.tools.learning_tool import LearningTool
        import inspect

        sig = inspect.signature(LearningTool.find_similar_tasks)
        expected_params = ['self', 'query', 'limit']

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

        # Проверяем типы и значения по умолчанию
        params = sig.parameters
        assert params['query'].annotation == str
        assert params['limit'].annotation == int
        assert params['limit'].default == 5

    def test_find_similar_tasks_return_type(self):
        """Проверка типа возвращаемого значения find_similar_tasks"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            result = tool.find_similar_tasks("test query")

            assert isinstance(result, str)

    def test_get_recommendations_method_signature(self):
        """Проверка сигнатуры метода get_recommendations"""
        from src.tools.learning_tool import LearningTool
        import inspect

        sig = inspect.signature(LearningTool.get_recommendations)
        expected_params = ['self', 'current_task']

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

        assert sig.parameters['current_task'].annotation == str

    def test_get_statistics_method_signature(self):
        """Проверка сигнатуры метода get_statistics"""
        from src.tools.learning_tool import LearningTool
        import inspect

        sig = inspect.signature(LearningTool.get_statistics)
        expected_params = ['self']

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

    def test_get_statistics_return_structure(self):
        """Проверка структуры возвращаемых данных get_statistics"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            result = tool.get_statistics()

            assert isinstance(result, str)
            assert "📊 Статистика LearningTool" in result
            assert "Всего задач:" in result
            assert "Успешных задач:" in result
            assert "Неудачных задач:" in result

    def test_run_method_actions(self):
        """Проверка доступных действий в методе _run"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Проверяем все поддерживаемые действия
            actions = ['save_experience', 'find_similar', 'get_recommendations', 'get_statistics']

            for action in actions:
                # Вызываем действие без параметров для проверки обработки
                result = tool._run(action)
                assert isinstance(result, str)

    def test_run_method_unknown_action(self):
        """Проверка обработки неизвестного действия в _run"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            result = tool._run("unknown_action")

            assert isinstance(result, str)
            assert "Unknown action" in result

    def test_patterns_data_structure(self):
        """Проверка структуры данных паттернов"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Добавляем задачи с паттернами
            tool.save_task_experience(
                task_id="task1",
                task_description="Task 1",
                success=True,
                patterns=["pattern_a", "pattern_b"]
            )

            tool.save_task_experience(
                task_id="task2",
                task_description="Task 2",
                success=True,
                patterns=["pattern_a", "pattern_c"]
            )

            data = tool._load_experience()

            # Проверяем структуру паттернов
            patterns = data['patterns']
            assert isinstance(patterns, dict)

            # Проверяем что паттерны содержат списки task_id
            for pattern, task_ids in patterns.items():
                assert isinstance(task_ids, list)
                for task_id in task_ids:
                    assert isinstance(task_id, str)

            # Проверяем конкретные паттерны
            assert "pattern_a" in patterns
            assert "pattern_b" in patterns
            assert "pattern_c" in patterns
            assert len(patterns["pattern_a"]) == 2  # Используется в обоих задачах


class TestLearningToolDataFormats:
    """Тесты форматов данных LearningTool"""

    def test_timestamp_format(self):
        """Проверка формата timestamp"""
        from src.tools.learning_tool import LearningTool
        import re

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            tool.save_task_experience("test_task", "Test", True)

            data = tool._load_experience()
            timestamp = data['tasks'][0]['timestamp']

            # Проверяем ISO формат (YYYY-MM-DDTHH:MM:SS)
            iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
            assert re.match(iso_pattern, timestamp) is not None

    def test_json_file_encoding(self):
        """Проверка кодировки JSON файла"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Добавляем данные с unicode символами
            tool.save_task_experience(
                task_id="test_unicode",
                task_description="Тест с русскими символами: функция, класс, модуль",
                success=True,
                notes="Заметки с эмодзи: ✅❌🔍"
            )

            # Проверяем что файл читается без ошибок
            data = tool._load_experience()
            assert len(data['tasks']) == 1

            task = data['tasks'][0]
            assert "русскими" in task['description']
            assert "✅" in task['notes']

    def test_statistics_calculation(self):
        """Проверка корректности расчета статистики"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Добавляем тестовые задачи
            tool.save_task_experience("task1", "Task 1", True, 1.0)
            tool.save_task_experience("task2", "Task 2", True, 2.0)
            tool.save_task_experience("task3", "Task 3", False, 1.5)

            data = tool._load_experience()
            stats = data['statistics']

            # Проверяем расчеты
            assert stats['total_tasks'] == 3
            assert stats['successful_tasks'] == 2
            assert stats['failed_tasks'] == 1
            assert abs(stats['average_execution_time'] - 1.5) < 0.01  # (1.0 + 2.0 + 1.5) / 3 = 1.5

    def test_max_experience_tasks_limit(self):
        """Проверка ограничения max_experience_tasks"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            max_tasks = 3
            tool = LearningTool(experience_dir=tmp_dir, max_experience_tasks=max_tasks)

            # Добавляем больше задач чем лимит
            for i in range(5):
                tool.save_task_experience(f"task{i}", f"Task {i}", True)

            data = tool._load_experience()

            # Проверяем что количество задач не превышает лимит
            assert len(data['tasks']) <= max_tasks

    def test_normalize_unicode_text_function(self):
        """Проверка функции normalize_unicode_text"""
        from src.tools.learning_tool import normalize_unicode_text

        # Тест с обычным текстом
        assert normalize_unicode_text("Hello World") == "hello world"

        # Тест с Unicode символами
        result = normalize_unicode_text("Тест naïve résumé")
        assert "тест" in result
        assert "naive" in result  # без диакритических знаков
        assert "resume" in result  # без диакритических знаков

        # Тест с пустой строкой
        assert normalize_unicode_text("") == ""

        # Тест с None
        assert normalize_unicode_text(None) == ""

    def test_task_search_with_unicode(self):
        """Проверка поиска задач с Unicode символами"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Добавляем задачу с русскими символами
            tool.save_task_experience(
                task_id="unicode_task",
                task_description="Создать тестовый файл с русскими символами",
                success=True
            )

            # Ищем с использованием русских символов
            result = tool.find_similar_tasks("Создать")

            assert isinstance(result, str)
            assert "Создать тестовый файл" in result

    def test_task_search_with_diacritics_normalization(self):
        """Проверка поиска задач с учетом Unicode нормализации диакритических знаков"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Добавляем задачу с диакритическими знаками
            tool.save_task_experience(
                task_id="diacritics_task",
                task_description="Créer un fichier de test avec des caractères spéciaux",
                success=True
            )

            # Ищем только по слову "creer" (без диакритических знаков)
            result = tool.find_similar_tasks("creer")

            assert isinstance(result, str)
            # Проверяем что найдена задача (не "Похожие задачи не найдены")
            assert "найдено" in result.lower() and "Créer un fichier" in result

    def test_empty_patterns_handling(self):
        """Проверка обработки пустых паттернов"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Добавляем задачу без паттернов
            tool.save_task_experience(
                task_id="no_patterns_task",
                task_description="Task without patterns",
                success=True,
                patterns=[]
            )

            data = tool._load_experience()

            # Проверяем что задача сохранена
            assert len(data['tasks']) == 1
            assert data['tasks'][0]['patterns'] == []

    def test_none_values_handling(self):
        """Проверка обработки None значений"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Проверяем что функция правильно валидирует входные параметры
            with pytest.raises(ValueError, match="task_id must be a non-empty string"):
                tool.save_task_experience(
                    task_id=None,
                    task_description="test",
                    success=True
                )

            with pytest.raises(ValueError, match="task_description must be a non-empty string"):
                tool.save_task_experience(
                    task_id="test_id",
                    task_description=None,
                    success=True
                )

            # Проверяем что success должен быть boolean (не None)
            with pytest.raises(ValueError, match="success must be a boolean"):
                tool.save_task_experience(
                    task_id="test_id",
                    task_description="test description",
                    success=None
                )

            # Сохраняем корректную задачу для проверки
            tool.save_task_experience(
                task_id="test_id",
                task_description="test description",
                success=True
            )

            data = tool._load_experience()
            assert len(data['tasks']) == 1

    def test_large_task_descriptions(self):
        """Проверка обработки больших описаний задач"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Создаем большое описание
            large_description = "Test task description. " * 1000  # Повторяем 1000 раз

            tool.save_task_experience(
                task_id="large_task",
                task_description=large_description,
                success=True
            )

            data = tool._load_experience()

            # Проверяем что большое описание сохранено
            assert len(data['tasks']) == 1
            assert data['tasks'][0]['description'] == large_description