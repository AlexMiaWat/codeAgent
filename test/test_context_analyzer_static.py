"""
Статические тесты для ContextAnalyzerTool
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.tools.context_analyzer_tool import ContextAnalyzerTool, normalize_unicode_text


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
        # Тест с диакритическими знаками
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


class TestContextAnalyzerToolInitialization:
    """Тесты инициализации ContextAnalyzerTool"""

    def test_initialization_with_defaults(self):
        """Тест инициализации с параметрами по умолчанию"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            assert tool.project_dir == Path(temp_dir)
            assert tool.docs_dir == Path(temp_dir) / "docs"
            assert tool.max_file_size == 1000000
            assert ".py" in tool.supported_extensions
            assert ".md" in tool.supported_extensions
            assert "python" in tool.supported_languages
            assert tool.max_dependency_depth == 5

    def test_initialization_with_custom_params(self):
        """Тест инициализации с пользовательскими параметрами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_extensions = [".py", ".js"]
            custom_languages = ["python", "javascript"]

            tool = ContextAnalyzerTool(
                project_dir=temp_dir,
                docs_dir="custom_docs",
                max_file_size=500000,
                supported_extensions=custom_extensions,
                supported_languages=custom_languages,
                max_dependency_depth=3
            )

            assert tool.docs_dir == Path(temp_dir) / "custom_docs"
            assert tool.max_file_size == 500000
            assert tool.supported_extensions == custom_extensions
            assert tool.supported_languages == custom_languages
            assert tool.max_dependency_depth == 3


class TestContextAnalyzerProjectStructure:
    """Тесты анализа структуры проекта"""

    def test_analyze_project_structure_empty(self):
        """Тест анализа пустого проекта"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            result = tool.analyze_project_structure()

            assert "Анализ структуры проекта" in result
            assert "Основные компоненты" in result
            assert "Типы файлов" in result

    def test_analyze_project_structure_with_files(self):
        """Тест анализа проекта с файлами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим структуру файлов
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "docs").mkdir()

            # Создадим файлы разных типов
            (Path(temp_dir) / "src" / "main.py").write_text("# Python file")
            (Path(temp_dir) / "src" / "utils.js").write_text("// JavaScript file")
            (Path(temp_dir) / "docs" / "README.md").write_text("# Documentation")
            (Path(temp_dir) / "config.yaml").write_text("key: value")

            tool = ContextAnalyzerTool(project_dir=temp_dir)
            result = tool.analyze_project_structure()

            assert "Анализ структуры проекта" in result
            assert ".py" in result or ".js" in result or ".md" in result or ".yaml" in result

    def test_project_structure_caching(self):
        """Тест кеширования анализа структуры"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Первый вызов
            result1 = tool.analyze_project_structure()

            # Второй вызов должен вернуть кешированный результат
            result2 = tool.analyze_project_structure()

            assert result1 == result2


class TestContextAnalyzerDependencies:
    """Тесты анализа зависимостей файлов"""

    def test_find_dependencies_python_file(self):
        """Тест поиска зависимостей Python файла"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим Python файлы
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "__init__.py").write_text("")
            (Path(temp_dir) / "src" / "utils.py").write_text("def helper(): pass")
            (Path(temp_dir) / "src" / "main.py").write_text("""
from src.utils import helper
import os
""")

            tool = ContextAnalyzerTool(project_dir=temp_dir)
            result = tool.find_file_dependencies("src/main.py")

            assert "Зависимости файла src/main.py" in result
            assert "src/utils.py" in result

    def test_find_dependencies_nonexistent_file(self):
        """Тест поиска зависимостей несуществующего файла"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            result = tool.find_file_dependencies("nonexistent.py")

            assert "не найден" in result

    def test_find_dependencies_large_file(self):
        """Тест поиска зависимостей в слишком большом файле"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir, max_file_size=100)

            # Создадим большой файл
            large_file = Path(temp_dir) / "large.py"
            large_file.write_text("#" * 200)

            result = tool.find_file_dependencies("large.py")

            assert "слишком большой" in result

    def test_analyze_python_dependencies(self):
        """Тест анализа Python зависимостей"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим структуру модулей
            (Path(temp_dir) / "custom_module").mkdir()
            (Path(temp_dir) / "custom_module" / "__init__.py").write_text("")
            (Path(temp_dir) / "custom_module" / "submodule.py").write_text("def function(): pass")

            tool = ContextAnalyzerTool(project_dir=temp_dir)

            content = """
import os
from pathlib import Path
import sys
from custom_module.submodule import function
"""

            dependencies = tool._analyze_python_dependencies(content)

            assert "os" not in dependencies  # Стандартная библиотека не должна включаться
            assert "pathlib" not in dependencies
            assert "sys" not in dependencies
            assert "custom_module/submodule.py" in dependencies

    def test_analyze_markdown_links(self):
        """Тест анализа ссылок в Markdown"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим файлы для ссылок
            (Path(temp_dir) / "README.md").write_text("# Main doc")
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "main.py").write_text("# Main code")

            tool = ContextAnalyzerTool(project_dir=temp_dir)

            content = """
# Documentation

See [main code](src/main.py) for implementation.
Also check [readme](README.md).
"""

            dependencies = tool._analyze_markdown_links(content)

            assert "src/main.py" in dependencies
            assert "README.md" in dependencies


class TestContextAnalyzerTaskContext:
    """Тесты получения контекста задач"""

    def test_get_task_context_validation(self):
        """Тест валидации входных параметров"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Тест пустой задачи
            with pytest.raises(ValueError, match="task_description must be a non-empty string"):
                tool.get_task_context("")

            # Тест слишком длинной задачи
            long_description = "a" * 10001
            with pytest.raises(ValueError, match="task_description is too long"):
                tool.get_task_context(long_description)

            # Тест None
            with pytest.raises(ValueError):
                tool.get_task_context(None)

    def test_get_task_context_with_files(self):
        """Тест получения контекста с существующими файлами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим структуру проекта
            (Path(temp_dir) / "docs").mkdir()
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "docs" / "api.md").write_text("# API Documentation\nContains authentication logic")
            (Path(temp_dir) / "src" / "auth.py").write_text("# Authentication module\nhandles user login")

            tool = ContextAnalyzerTool(project_dir=temp_dir)
            result = tool.get_task_context("implement user authentication")

            assert "Контекст для задачи" in result
            assert "Связанная документация" in result or "Релевантные файлы кода" in result

    def test_get_task_context_no_matches(self):
        """Тест получения контекста когда нет совпадений"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            result = tool.get_task_context("unique task with no matches")

            assert "Контекст для задачи" in result
            assert "не найдена" in result.lower()


class TestContextAnalyzerComponent:
    """Тесты анализа компонентов"""

    def test_analyze_component_directory(self):
        """Тест анализа директории"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим структуру директории
            (Path(temp_dir) / "src" / "utils").mkdir(parents=True)
            (Path(temp_dir) / "src" / "main.py").write_text("# Main file")
            (Path(temp_dir) / "src" / "utils" / "helpers.py").write_text("# Helper file")

            tool = ContextAnalyzerTool(project_dir=temp_dir)
            result = tool.analyze_component("src")

            assert "Анализ компонента: src" in result
            assert "Тип:** directory" in result
            assert "Файлов:**" in result

    def test_analyze_component_file(self):
        """Тест анализа файла"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим файл с зависимостями
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "utils.py").write_text("def helper(): pass")
            (Path(temp_dir) / "src" / "main.py").write_text("""
from src.utils import helper
""")

            tool = ContextAnalyzerTool(project_dir=temp_dir)
            result = tool.analyze_component("src/main.py")

            assert "Анализ компонента: src/main.py" in result
            assert "Тип:** file" in result
            assert "Зависимости:**" in result

    def test_analyze_component_nonexistent(self):
        """Тест анализа несуществующего компонента"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            result = tool.analyze_component("nonexistent")

            assert "не найден" in result


class TestContextAnalyzerRelatedFiles:
    """Тесты поиска связанных файлов"""

    def test_find_related_files_with_matches(self):
        """Тест поиска связанных файлов с совпадениями"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим файлы с содержимым
            (Path(temp_dir) / "docs").mkdir()
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "docs" / "auth.md").write_text("# Authentication\nUser login process")
            (Path(temp_dir) / "src" / "auth.py").write_text("# Authentication module\nhandles login")

            tool = ContextAnalyzerTool(project_dir=temp_dir)
            result = tool.find_related_files("authentication")

            assert "связанные с запросом" in result.lower()
            assert "auth.md" in result or "auth.py" in result

    def test_find_related_files_no_matches(self):
        """Тест поиска связанных файлов без совпадений"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            result = tool.find_related_files("nonexistent_topic")

            assert "не найдены" in result


class TestContextAnalyzerErrorHandling:
    """Тесты обработки ошибок"""

    def test_unicode_decode_error_handling(self):
        """Тест обработки ошибок декодирования Unicode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим файл с некорректной кодировкой (бинарный файл)
            binary_file = Path(temp_dir) / "binary.dat"
            binary_file.write_bytes(b'\x80\x81\x82\x83')

            tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Попытка анализа файла не должна вызвать исключение
            result = tool.find_file_dependencies("binary.dat")
            # Должна вернуться пустая зависимость или сообщение об ошибке

    @patch('builtins.open')
    def test_file_operation_error_handling(self, mock_open):
        """Тест обработки ошибок операций с файлами"""
        mock_open.side_effect = PermissionError("Permission denied")

        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Попытка анализа должна обработать ошибку
            result = tool.analyze_project_structure()
            # Операция должна продолжиться несмотря на ошибку

    def test_dependency_analysis_edge_cases(self):
        """Тест граничных случаев анализа зависимостей"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Тест с пустым содержимым
            empty_deps = tool._analyze_python_dependencies("")
            assert empty_deps == set()

            # Тест с некорректным импортом
            invalid_deps = tool._analyze_python_dependencies("import")
            assert invalid_deps == set()


class TestContextAnalyzerConfigurationFiles:
    """Тесты анализа конфигурационных файлов"""

    def test_analyze_requirements_txt(self):
        """Тест анализа requirements.txt"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            content = """
requests>=2.25.0
flask==2.0.1
# Comment
-e git+https://github.com/user/repo.git#egg=package
"""

            dependencies = tool._analyze_requirements_txt_dependencies(content)

            assert "requests" in dependencies
            assert "flask" in dependencies
            # Git dependencies are parsed differently, check for the git URL part
            assert any("git" in dep or "repo" in dep for dep in dependencies)

    def test_analyze_package_json(self):
        """Тест анализа package.json"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)

            content = '''
{
  "dependencies": {
    "react": "^17.0.0",
    "lodash": "~4.17.0"
  },
  "devDependencies": {
    "jest": "^27.0.0"
  }
}
'''

            dependencies = tool._analyze_package_json_dependencies(content)

            assert "react" in dependencies
            assert "lodash" in dependencies
            assert "jest" in dependencies