"""
Статические тесты для ContextAnalyzerTool - проверка структуры данных, API, форматов
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from unittest.mock import Mock, patch, MagicMock
import inspect


class TestContextAnalyzerToolStatic:
    """Статические тесты ContextAnalyzerTool"""

    def test_context_analyzer_class_attributes(self):
        """Проверка атрибутов класса ContextAnalyzerTool"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Проверяем поля Pydantic модели (только определенные в нашем классе)
        model_fields = ContextAnalyzerTool.model_fields
        assert 'name' in model_fields
        assert 'description' in model_fields
        assert 'project_dir' in model_fields
        assert 'docs_dir' in model_fields
        assert 'max_file_size' in model_fields
        assert 'supported_extensions' in model_fields

        # Создаем экземпляр для проверки значений
        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            assert tool.name == "ContextAnalyzerTool"
            assert "анализ" in tool.description.lower()
            assert tool.max_file_size == 1000000
            assert isinstance(tool.supported_extensions, list)

    def test_supported_extensions_list(self):
        """Проверка списка поддерживаемых расширений"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            expected_extensions = ['.md', '.txt', '.rst', '.py', '.js', '.ts', '.json', '.yaml', '.yml', '.java', '.cpp', '.hpp', '.c', '.h']

            assert tool.supported_extensions == expected_extensions

            # Проверяем что все расширения начинаются с точки
            for ext in tool.supported_extensions:
                assert ext.startswith('.')
                assert len(ext) > 1

    def test_context_analyzer_initialization(self):
        """Проверка инициализации ContextAnalyzerTool"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool
        import inspect

        # Проверяем сигнатуру __init__
        init_sig = inspect.signature(ContextAnalyzerTool.__init__)
        expected_params = ['self', 'project_dir', 'docs_dir', 'max_file_size',
                          'supported_extensions', 'supported_languages', 'max_dependency_depth', 'kwargs']

        actual_params = list(init_sig.parameters.keys())
        assert actual_params == expected_params

        # Проверяем типы параметров
        params = init_sig.parameters
        assert params['project_dir'].annotation == str
        assert params['docs_dir'].annotation == str
        assert params['max_file_size'].annotation == int
        # supported_extensions может быть None по умолчанию

    def test_context_analyzer_initialization_defaults(self):
        """Проверка значений по умолчанию при инициализации"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Проверяем применение значений по умолчанию
            assert str(tool.project_dir) == str(project_dir)
            assert str(tool.docs_dir) == str(project_dir / "docs")
            assert tool.max_file_size == 1000000
            # supported_extensions должен быть установлен по умолчанию
            assert tool.supported_extensions is not None
            assert len(tool.supported_extensions) > 0

    def test_context_analyzer_custom_config(self):
        """Проверка кастомной конфигурации ContextAnalyzerTool"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            custom_docs = project_dir / "custom_docs"
            custom_extensions = ['.md', '.py', '.txt']
            custom_max_size = 500000

            tool = ContextAnalyzerTool(
                project_dir=str(project_dir),
                docs_dir=str(custom_docs),
                max_file_size=custom_max_size,
                supported_extensions=custom_extensions
            )

            assert str(tool.docs_dir) == str(custom_docs)
            assert tool.max_file_size == custom_max_size
            assert tool.supported_extensions == custom_extensions

    def test_analyze_project_structure_method_signature(self):
        """Проверка сигнатуры метода analyze_project_structure"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool
        import inspect

        sig = inspect.signature(ContextAnalyzerTool.analyze_project_structure)
        expected_params = ['self']

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

    def test_analyze_project_structure_return_type(self):
        """Проверка типа возвращаемого значения analyze_project_structure"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            result = tool.analyze_project_structure()

            assert isinstance(result, str)
            assert "🏗️ Анализ структуры проекта" in result

    def test_find_file_dependencies_method_signature(self):
        """Проверка сигнатуры метода find_file_dependencies"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool
        import inspect

        sig = inspect.signature(ContextAnalyzerTool.find_file_dependencies)
        expected_params = ['self', 'file_path']

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

        assert sig.parameters['file_path'].annotation == str

    def test_get_task_context_method_signature(self):
        """Проверка сигнатуры метода get_task_context"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool
        import inspect

        sig = inspect.signature(ContextAnalyzerTool.get_task_context)
        expected_params = ['self', 'task_description']

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

        assert sig.parameters['task_description'].annotation == str

    def test_analyze_component_method_signature(self):
        """Проверка сигнатуры метода analyze_component"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool
        import inspect

        sig = inspect.signature(ContextAnalyzerTool.analyze_component)
        expected_params = ['self', 'component_path']

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

        assert sig.parameters['component_path'].annotation == str

    def test_find_related_files_method_signature(self):
        """Проверка сигнатуры метода find_related_files"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool
        import inspect

        sig = inspect.signature(ContextAnalyzerTool.find_related_files)
        expected_params = ['self', 'query']

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

        assert sig.parameters['query'].annotation == str

    def test_run_method_actions(self):
        """Проверка доступных действий в методе _run"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            # Проверяем все поддерживаемые действия
            actions = ['analyze_project', 'find_dependencies', 'get_context',
                      'analyze_component', 'find_related_files']

            for action in actions:
                # Вызываем действие с тестовыми параметрами
                if action == 'analyze_project':
                    result = tool._run(action)
                else:
                    result = tool._run(action, **{f"{action.split('_')[1]}_param": "test"})

                assert isinstance(result, str)

    def test_run_method_unknown_action(self):
        """Проверка обработки неизвестного действия в _run"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            result = tool._run("unknown_action")

            assert isinstance(result, str)
            assert "Unknown action" in result

    def test_file_dependencies_python_analysis(self):
        """Проверка анализа зависимостей Python файлов"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовый Python файл с импортами
            test_file = project_dir / "test_module.py"
            test_file.write_text("""
import os
import sys
from pathlib import Path
from typing import List, Dict
""")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.find_file_dependencies("test_module.py")

            # Проверяем что результат содержит информацию о зависимостях
            assert isinstance(result, str)
            assert "test_module.py" in result

    def test_file_dependencies_markdown_analysis(self):
        """Проверка анализа зависимостей Markdown файлов"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовый MD файл со ссылками
            test_file = project_dir / "test.md"
            test_file.write_text("""
# Test Document

See [API docs](api.md) for details.
Also check [utils](utils.py) module.

Related: [config](config.yaml)
""")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.find_file_dependencies("test.md")

            assert isinstance(result, str)
            assert "test.md" in result

    def test_get_task_context_structure(self):
        """Проверка структуры контекста задачи"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовые файлы
            docs_dir = project_dir / "docs"
            docs_dir.mkdir()
            (docs_dir / "api.md").write_text("# API Documentation\nThis is about API development")
            (docs_dir / "guide.md").write_text("# User Guide\nHow to use the system")

            src_dir = project_dir / "src"
            src_dir.mkdir()
            (src_dir / "api.py").write_text("# API implementation\ndef get_data():\n    pass")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.get_task_context("разработать API")

            assert isinstance(result, str)
            assert "📋 Контекст для задачи" in result

    def test_analyze_component_file(self):
        """Проверка анализа компонента-файла"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовый файл
            test_file = project_dir / "test.py"
            test_content = "# Test Python file\ndef hello():\n    return 'world'"
            test_file.write_text(test_content)

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.analyze_component("test.py")

            assert isinstance(result, str)
            assert "🔍 Анализ компонента" in result
            assert "test.py" in result
            assert "Тип:" in result and "file" in result

    def test_analyze_component_directory(self):
        """Проверка анализа компонента-директории"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовую директорию с файлами
            test_dir = project_dir / "test_package"
            test_dir.mkdir()

            (test_dir / "__init__.py").write_text("")
            (test_dir / "module1.py").write_text("# Module 1")
            (test_dir / "module2.py").write_text("# Module 2")
            (test_dir / "README.md").write_text("# Package docs")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.analyze_component("test_package")

            assert isinstance(result, str)
            assert "🔍 Анализ компонента" in result
            assert "test_package" in result
            assert "Тип:" in result and "directory" in result
            assert "Файлов:" in result

    def test_find_related_files_structure(self):
        """Проверка структуры поиска связанных файлов"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовые файлы
            docs_dir = project_dir / "docs"
            docs_dir.mkdir()
            (docs_dir / "search.md").write_text("# Search functionality\nHow to implement search")

            src_dir = project_dir / "src"
            src_dir.mkdir()
            (src_dir / "search.py").write_text("# Search implementation\ndef find():\n    pass")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.find_related_files("search")

            assert isinstance(result, str)
            assert "📁 Файлы, связанные с запросом" in result


class TestContextAnalyzerToolFormats:
    """Тесты форматов и поддерживаемых типов файлов"""

    def test_supported_file_types(self):
        """Проверка поддержки различных типов файлов"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем файлы разных поддерживаемых типов
            test_files = {
                "test.md": "# Markdown file",
                "test.txt": "Plain text file",
                "test.py": "# Python file",
                "test.json": '{"key": "value"}',
                "test.yaml": "key: value",
                "test.yml": "key: value"
            }

            for filename, content in test_files.items():
                (project_dir / filename).write_text(content)

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Проверяем что все файлы могут быть проанализированы
            for filename in test_files.keys():
                result = tool.analyze_component(filename)
                assert isinstance(result, str)
                assert filename in result

    def test_file_size_limits(self):
        """Проверка ограничений на размер файлов"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем файл с размером больше лимита
            large_file = project_dir / "large.py"
            large_content = "# Large file with more content to exceed size limit\n" * 200000  # Делаем файл значительно больше лимита
            large_file.write_text(large_content)

            # Проверяем размер (должен быть значительно больше 1MB)
            file_size = large_file.stat().st_size
            assert file_size > 1000000, f"File size {file_size} is not greater than 1MB limit"
            assert file_size > 2000000, f"File size {file_size} should be much larger than 1MB for reliable testing"

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Попытка анализа большого файла в поиске зависимостей
            result = tool.find_file_dependencies("large.py")

            # Должен вернуть сообщение о слишком большом файле или обработать gracefully
            assert isinstance(result, str)

    def test_cache_initialization(self):
        """Проверка инициализации кэшей"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            # Проверяем что кэши инициализированы
            assert hasattr(tool, '_analysis_cache')
            assert hasattr(tool, '_dependency_cache')

            assert isinstance(tool._analysis_cache, dict)
            assert isinstance(tool._dependency_cache, dict)

            # Проверяем что кэши пустые при инициализации
            assert len(tool._analysis_cache) == 0
            assert len(tool._dependency_cache) == 0

    def test_normalize_unicode_text_function(self):
        """Проверка функции normalize_unicode_text"""
        from src.tools.context_analyzer_tool import normalize_unicode_text

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
        import pytest

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = ContextAnalyzerTool(project_dir=tmp_dir)

            # Функция должна валидировать входные параметры
            with pytest.raises(ValueError, match="task_description must be a non-empty string"):
                tool.get_task_context("")

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