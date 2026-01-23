"""
ContextAnalyzerTool - инструмент для анализа контекста проекта
"""

import re
import logging
import unicodedata
from pathlib import Path
from typing import Dict, List, Any, Set
from crewai.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


def normalize_unicode_text(text: str) -> str:
    """
    Нормализует Unicode текст для улучшения поиска и сравнения.

    Args:
        text: Исходный текст

    Returns:
        Нормализованный текст
    """
    if text is None:
        return ""
    if not text:
        return text

    # Нормализуем Unicode (NFD - canonical decomposition)
    normalized = unicodedata.normalize('NFD', text)

    # Удаляем диакритические знаки (combining characters)
    normalized = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')

    # Приводим к нижнему регистру
    normalized = normalized.lower()

    return normalized


class ContextAnalyzerTool(BaseTool):
    """
    Инструмент для анализа контекста проекта.

    Позволяет:
    - Анализировать структуру проекта
    - Понимать зависимости и связи между компонентами
    - Предоставлять контекстную информацию для задач
    """

    name: str = "ContextAnalyzerTool"
    description: str = """
    Инструмент для анализа контекста проекта.
    Позволяет анализировать структуру, зависимости и предоставлять контекстную информацию.
    """
    project_dir: str = "."
    docs_dir: str = "docs"
    max_file_size: int = 1000000
    supported_extensions: list = [".md", ".txt", ".rst", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".java", ".cpp", ".hpp", ".c", ".h"]
    supported_languages: list = ["python", "javascript", "typescript", "java", "cpp", "c"]
    max_dependency_depth: int = 5

    def __init__(self, project_dir: str = ".", docs_dir: str = "docs",
                 max_file_size: int = 1000000, supported_extensions: List[str] = None,
                 supported_languages: List[str] = None, max_dependency_depth: int = 5, **kwargs):
        """
        Инициализация ContextAnalyzerTool

        Args:
            project_dir: Корневая директория проекта
            docs_dir: Директория с документацией
            max_file_size: Максимальный размер файла для анализа
            supported_extensions: Поддерживаемые расширения файлов
            supported_languages: Поддерживаемые языки программирования
            max_dependency_depth: Максимальная глубина анализа зависимостей
        """
        super().__init__(**kwargs)
        self.project_dir = Path(project_dir)
        self.docs_dir = self.project_dir / docs_dir
        self.max_file_size = max_file_size
        self.supported_extensions = supported_extensions or self.supported_extensions
        self.supported_languages = supported_languages or self.supported_languages
        self.max_dependency_depth = max_dependency_depth

        # Кэш для анализа
        self._analysis_cache: Dict[str, Any] = {}
        self._dependency_cache: Dict[str, Set[str]] = {}

    def _run(self, action: str, **kwargs) -> str:
        """
        Выполнение действия с инструментом анализа контекста

        Args:
            action: Действие (analyze_project, find_dependencies, get_context, etc.)
            **kwargs: Параметры действия

        Returns:
            Результат выполнения действия
        """
        try:
            if action == "analyze_project":
                return self.analyze_project_structure()
            elif action == "find_dependencies":
                return self.find_file_dependencies(kwargs.get("file_path", ""))
            elif action == "get_context":
                return self.get_task_context(kwargs.get("task_description", ""))
            elif action == "analyze_component":
                return self.analyze_component(kwargs.get("component_path", ""))
            elif action == "find_related_files":
                return self.find_related_files(kwargs.get("query", ""))
            else:
                return f"Unknown action: {action}"

        except Exception as e:
            logger.error(f"Error in ContextAnalyzerTool._run with action '{action}': {e}", exc_info=True)
            return f"Error executing action '{action}': {str(e)}"

    def analyze_project_structure(self) -> str:
        """
        Анализ общей структуры проекта

        Returns:
            Описание структуры проекта
        """
        try:
            # Проверяем кэш анализа структуры
            cache_key = "project_structure"
            if cache_key in self._analysis_cache:
                return self._analysis_cache[cache_key]
            structure = {
                "directories": {},
                "file_types": {},
                "main_components": []
            }

            # Анализируем директории
            for dir_path in self.project_dir.rglob("*"):
                if dir_path.is_dir() and not any(part.startswith('.') for part in dir_path.parts):
                    level = len(dir_path.relative_to(self.project_dir).parts)
                    if level <= 3:  # Ограничиваем глубину анализа
                        try:
                            file_count = len(list(dir_path.glob("*")))
                            structure["directories"][str(dir_path.relative_to(self.project_dir))] = file_count
                        except PermissionError:
                            continue

            # Анализируем типы файлов (оптимизированный один проход)
            file_counts = {}
            for file_path in self.project_dir.rglob("*"):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in self.supported_extensions:
                        file_counts[ext] = file_counts.get(ext, 0) + 1

            structure["file_types"] = file_counts

            # Определяем основные компоненты
            main_dirs = ["src", "docs", "test", "config", "scripts"]
            for main_dir in main_dirs:
                dir_path = self.project_dir / main_dir
                if dir_path.exists():
                    structure["main_components"].append({
                        "name": main_dir,
                        "path": main_dir,
                        "files": len(list(dir_path.rglob("*.*")))
                    })

            # Формируем отчет
            result = "🏗️ Анализ структуры проекта:\n\n"

            result += "**Основные компоненты:**\n"
            for comp in structure["main_components"]:
                result += f"• {comp['name']}: {comp['files']} файлов\n"

            result += "\n**Типы файлов:**\n"
            for ext, count in structure["file_types"].items():
                result += f"• {ext}: {count} файлов\n"

            result += "\n**Структура директорий:**\n"
            for dir_name, file_count in list(structure["directories"].items())[:10]:  # Ограничиваем вывод
                result += f"• {dir_name}: {file_count} элементов\n"

            # Кэшируем результат
            self._analysis_cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Error analyzing project structure for {self.project_dir}: {e}", exc_info=True)
            return f"Ошибка анализа структуры проекта: {str(e)}"

    def find_file_dependencies(self, file_path: str) -> str:
        """
        Поиск зависимостей файла

        Args:
            file_path: Путь к файлу

        Returns:
            Список зависимостей файла
        """
        try:
            target_file = Path(file_path)
            if not target_file.is_absolute():
                target_file = self.project_dir / file_path

            if not target_file.exists():
                return f"Файл не найден: {file_path}"

            # Проверяем размер файла
            if target_file.stat().st_size > self.max_file_size:
                return f"Файл слишком большой для анализа: {target_file.stat().st_size} байт"

            # Проверяем кэш зависимостей
            cache_key = str(target_file.relative_to(self.project_dir))
            if cache_key in self._dependency_cache:
                dependencies = self._dependency_cache[cache_key]
            else:
                dependencies = set()

                # Анализируем зависимости в зависимости от типа файла
                file_extension = target_file.suffix.lower()
                file_name = target_file.name.lower()

                try:
                    with open(target_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Python файлы
                    if file_extension == ".py":
                        dependencies.update(self._analyze_python_dependencies(content))

                    # JavaScript/TypeScript файлы
                    elif file_extension in [".js", ".ts", ".jsx", ".tsx"]:
                        dependencies.update(self._analyze_js_ts_dependencies(content))

                    # Java файлы
                    elif file_extension == ".java":
                        dependencies.update(self._analyze_java_dependencies(content))

                    # C/C++ файлы
                    elif file_extension in [".cpp", ".hpp", ".c", ".h"]:
                        dependencies.update(self._analyze_cpp_dependencies(content))

                    # Markdown файлы
                    elif file_extension == ".md":
                        dependencies.update(self._analyze_markdown_links(content))

                    # YAML/JSON конфигурационные файлы
                    elif file_extension in [".yaml", ".yml", ".json"]:
                        if file_name == "pyproject.toml":
                            dependencies.update(self._analyze_pyproject_dependencies(content))
                        elif file_name == "package.json":
                            dependencies.update(self._analyze_package_json_dependencies(content))
                        else:
                            dependencies.update(self._analyze_config_dependencies(content, file_extension))

                    # Специальные файлы зависимостей
                    elif file_name == "requirements.txt":
                        dependencies.update(self._analyze_requirements_txt_dependencies(content))
                    elif file_name == "pyproject.toml":
                        dependencies.update(self._analyze_pyproject_dependencies(content))
                    elif file_name == "package.json":
                        dependencies.update(self._analyze_package_json_dependencies(content))

                    # Кэшируем результат
                    self._dependency_cache[cache_key] = dependencies

                except UnicodeDecodeError:
                    logger.warning(f"Cannot decode file {target_file} with UTF-8 encoding")
                except Exception as e:
                    logger.error(f"Error analyzing dependencies for {target_file}: {e}")

            if not dependencies:
                return f"Зависимости для файла {file_path} не найдены."

            result = f"🔗 Зависимости файла {file_path}:\n\n"
            for dep in sorted(dependencies):
                result += f"• {dep}\n"

            return result

        except Exception as e:
            logger.error(f"Error finding dependencies for file '{file_path}': {e}", exc_info=True)
            return f"Ошибка поиска зависимостей: {str(e)}"

    def _analyze_python_dependencies(self, content: str) -> Set[str]:
        """Анализ зависимостей Python файлов"""
        dependencies = set()

        # Находим импорты
        import_patterns = [
            r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
            r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import'
        ]

        for pattern in import_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                # Преобразуем в путь к файлу
                module_path = match.replace('.', '/')
                possible_files = [
                    f"{module_path}.py",
                    f"{module_path}/__init__.py"
                ]

                for possible_file in possible_files:
                    if (self.project_dir / possible_file).exists():
                        dependencies.add(possible_file)

        return dependencies

    def _analyze_js_ts_dependencies(self, content: str) -> Set[str]:
        """Анализ зависимостей JavaScript/TypeScript файлов"""
        dependencies = set()

        # Импорты ES6
        import_patterns = [
            r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        ]

        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Преобразуем в путь к файлу
                if not match.startswith('.'):
                    continue  # Пропускаем внешние зависимости

                # Обрабатываем относительные пути
                if match.endswith('/'):
                    match = match[:-1]

                possible_extensions = ['.js', '.ts', '.jsx', '.tsx', '/index.js', '/index.ts']
                for ext in possible_extensions:
                    dep_path = match + ext
                    if (self.project_dir / dep_path).exists():
                        dependencies.add(dep_path)
                        break

        return dependencies

    def _analyze_java_dependencies(self, content: str) -> Set[str]:
        """Анализ зависимостей Java файлов"""
        dependencies = set()

        # Импорты классов
        import_pattern = r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*;'
        matches = re.findall(import_pattern, content, re.MULTILINE)

        for match in matches:
            # Преобразуем в путь к файлу
            class_path = match.replace('.', '/') + '.java'
            if (self.project_dir / class_path).exists():
                dependencies.add(class_path)

        return dependencies

    def _analyze_cpp_dependencies(self, content: str) -> Set[str]:
        """Анализ зависимостей C/C++ файлов"""
        dependencies = set()

        # Include директивы
        include_pattern = r'#include\s+["<]([^">]+)[">]'
        matches = re.findall(include_pattern, content)

        for match in matches:
            # Проверяем локальные include файлы
            if match.startswith('.'):
                continue  # Пропускаем системные include

            possible_files = [match]
            if not match.endswith('.h') and not match.endswith('.hpp'):
                possible_files.extend([match + '.h', match + '.hpp'])

            for dep_file in possible_files:
                if (self.project_dir / dep_file).exists():
                    dependencies.add(dep_file)
                    break

        return dependencies

    def _analyze_markdown_links(self, content: str) -> Set[str]:
        """Анализ ссылок в Markdown файлах"""
        dependencies = set()

        # Находим ссылки на файлы
        link_patterns = [
            r'\[([^\]]+)\]\(([^)]+\.md)\)',  # Markdown ссылки
            r'\[([^\]]+)\]\(([^)]+\.py)\)',  # Ссылки на Python файлы
            r'\[([^\]]+)\]\(([^)]+\.(?:js|ts|java|cpp|h|hpp))\)',  # Ссылки на код
            r'([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*\.(?:py|js|ts|java|cpp|h|hpp))',  # Файлы в тексте
        ]

        for pattern in link_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    file_ref = match[1]
                else:
                    file_ref = match

                # Проверяем существование файла
                ref_path = self.project_dir / file_ref
                if ref_path.exists():
                    dependencies.add(file_ref)

        return dependencies

    def _analyze_requirements_txt_dependencies(self, content: str) -> Set[str]:
        """Анализ зависимостей из requirements.txt"""
        dependencies = set()

        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Удаляем комментарии и версии
                dep = line.split('#')[0].strip()
                dep = dep.split(';')[0].strip()  # Удаляем условия
                dep = dep.split('>=')[0].strip()
                dep = dep.split('==')[0].strip()
                dep = dep.split('<')[0].strip()
                dep = dep.split('>')[0].strip()
                dep = dep.split('!')[0].strip()

                if dep and dep != line:  # Если что-то изменилось
                    dependencies.add(dep)

        return dependencies

    def _analyze_pyproject_dependencies(self, content: str) -> Set[str]:
        """Анализ зависимостей из pyproject.toml"""
        dependencies = set()

        try:
            import tomllib
            data = tomllib.loads(content)
        except ImportError:
            # Для Python < 3.11 используем tomli
            try:
                import tomli as tomllib
                data = tomllib.loads(content)
            except ImportError:
                logger.warning("tomli/tomllib not available for pyproject.toml parsing")
                return dependencies

        # Ищем секции зависимостей
        dependency_sections = [
            "project.dependencies",
            "project.optional-dependencies",
            "tool.poetry.dependencies",
            "tool.poetry.dev-dependencies",
            "build-system.requires"
        ]

        def extract_deps(obj):
            """Рекурсивное извлечение зависимостей"""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str):
                        # Удаляем версии из зависимостей
                        dep = value.split('>=')[0].split('==')[0].split('<')[0].split('>')[0].split(';')[0].strip()
                        if dep and not dep.startswith('python'):
                            dependencies.add(dep)
                    elif isinstance(value, list):
                        for item in value:
                            extract_deps(item)
                    elif isinstance(value, dict):
                        extract_deps(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, str):
                        dep = item.split('>=')[0].split('==')[0].split('<')[0].split('>')[0].split(';')[0].strip()
                        if dep and not dep.startswith('python'):
                            dependencies.add(dep)
                    elif isinstance(item, dict):
                        extract_deps(item)

        # Проходим по всем секциям зависимостей
        for section_path in dependency_sections:
            current_data = data
            try:
                for part in section_path.split('.'):
                    current_data = current_data[part]
                extract_deps(current_data)
            except (KeyError, TypeError):
                continue

        return dependencies

    def _analyze_package_json_dependencies(self, content: str) -> Set[str]:
        """Анализ зависимостей из package.json"""
        dependencies = set()

        try:
            import json
            data = json.loads(content)

            # Ищем все секции зависимостей
            dep_sections = [
                "dependencies",
                "devDependencies",
                "peerDependencies",
                "optionalDependencies",
                "bundledDependencies"
            ]

            for section in dep_sections:
                if section in data and isinstance(data[section], dict):
                    for dep_name in data[section].keys():
                        dependencies.add(dep_name)

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error parsing package.json: {e}")

        return dependencies

    def _analyze_config_dependencies(self, content: str, file_extension: str) -> Set[str]:
        """Анализ зависимостей в конфигурационных файлах"""
        dependencies = set()

        try:
            if file_extension == ".json":
                import json
                data = json.loads(content)
            else:  # YAML
                import yaml
                data = yaml.safe_load(content)

            # Рекурсивно ищем строковые значения, которые могут быть путями к файлам
            def find_file_paths(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        find_file_paths(value, f"{path}.{key}" if path else key)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        find_file_paths(item, f"{path}[{i}]")
                elif isinstance(obj, str):
                    # Проверяем, выглядит ли значение как путь к файлу
                    if any(obj.endswith(ext) for ext in self.supported_extensions):
                        if (self.project_dir / obj).exists():
                            dependencies.add(obj)

            find_file_paths(data)

        except Exception as e:
            logger.debug(f"Could not parse config file: {e}")

        return dependencies

    def get_task_context(self, task_description: str) -> str:
        """
        Получение контекстной информации для задачи

        Args:
            task_description: Описание задачи

        Returns:
            Контекстная информация
        """
        # Валидация входных параметров
        if not task_description or not isinstance(task_description, str):
            raise ValueError("task_description must be a non-empty string")

        if len(task_description) > 10000:  # Ограничение на длину
            raise ValueError("task_description is too long (max 10000 characters)")

        try:
            context_info = {
                "relevant_files": [],
                "documentation": [],
                "similar_tasks": [],
                "project_patterns": []
            }

            # Ищем релевантные файлы с улучшенной Unicode обработкой
            task_normalized = normalize_unicode_text(task_description)

            # Поиск в документации
            if self.docs_dir.exists():
                for doc_file in self.docs_dir.rglob("*.md"):
                    try:
                        if doc_file.stat().st_size > self.max_file_size:
                            continue

                        with open(doc_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        content_normalized = normalize_unicode_text(content)

                        # Ищем ключевые слова с учетом Unicode нормализации
                        if any(normalize_unicode_text(keyword) in content_normalized
                               for keyword in task_description.split()):
                            rel_path = doc_file.relative_to(self.project_dir)
                            context_info["documentation"].append(str(rel_path))

                    except UnicodeDecodeError:
                        # Пропускаем файлы с некорректной кодировкой
                        continue
                    except Exception:
                        continue

            # Поиск в исходном коде
            src_dir = self.project_dir / "src"
            if src_dir.exists():
                for src_file in src_dir.rglob("*.py"):
                    try:
                        if src_file.stat().st_size > self.max_file_size:
                            continue

                        with open(src_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        content_normalized = normalize_unicode_text(content)

                        # Ищем ключевые слова с учетом Unicode нормализации
                        if any(normalize_unicode_text(keyword) in content_normalized
                               for keyword in task_description.split()):
                            rel_path = src_file.relative_to(self.project_dir)
                            context_info["relevant_files"].append(str(rel_path))

                    except UnicodeDecodeError:
                        # Пропускаем файлы с некорректной кодировкой
                        continue
                    except Exception:
                        continue

            # Формируем результат
            result = f"📋 Контекст для задачи: '{task_description}'\n\n"

            if context_info["documentation"]:
                result += "**Связанная документация:**\n"
                for doc in context_info["documentation"][:5]:  # Ограничиваем вывод
                    result += f"• {doc}\n"
                result += "\n"

            if context_info["relevant_files"]:
                result += "**Релевантные файлы кода:**\n"
                for file in context_info["relevant_files"][:5]:  # Ограничиваем вывод
                    result += f"• {file}\n"
                result += "\n"

            if not context_info["documentation"] and not context_info["relevant_files"]:
                result += "Контекстная информация не найдена. Рекомендуется изучить основную документацию проекта.\n"

            return result

        except Exception as e:
            logger.error(f"Error getting task context for '{task_description[:50]}...': {e}", exc_info=True)
            return f"Ошибка получения контекста: {str(e)}"

    def analyze_component(self, component_path: str) -> str:
        """
        Анализ конкретного компонента проекта

        Args:
            component_path: Путь к компоненту

        Returns:
            Анализ компонента
        """
        try:
            component = Path(component_path)
            if not component.is_absolute():
                component = self.project_dir / component_path

            if not component.exists():
                return f"Компонент не найден: {component_path}"

            analysis = {
                "type": "directory" if component.is_dir() else "file",
                "size": component.stat().st_size if component.is_file() else 0,
                "files": 0,
                "subdirs": 0,
                "languages": {},
                "dependencies": []
            }

            if component.is_dir():
                # Анализируем директорию
                all_files = list(component.rglob("*.*"))
                analysis["files"] = len([f for f in all_files if f.is_file()])
                analysis["subdirs"] = len([d for d in component.rglob("*") if d.is_dir() and d != component])

                # Определяем языки программирования
                for file in all_files[:50]:  # Ограничиваем для производительности
                    ext = file.suffix.lower()
                    if ext in analysis["languages"]:
                        analysis["languages"][ext] += 1
                    else:
                        analysis["languages"][ext] = 1

            elif component.is_file():
                # Анализируем файл
                analysis["language"] = component.suffix

                # Ищем зависимости
                deps_result = self.find_file_dependencies(str(component))
                if "•" in deps_result:
                    deps_lines = deps_result.split("\n")[2:]  # Пропускаем заголовок
                    analysis["dependencies"] = [line.strip("• ").strip() for line in deps_lines if line.strip()]

            # Формируем отчет
            result = f"🔍 Анализ компонента: {component_path}\n\n"

            result += f"**Тип:** {analysis['type']}\n"

            if analysis["type"] == "directory":
                result += f"**Файлов:** {analysis['files']}\n"
                result += f"**Поддиректорий:** {analysis['subdirs']}\n"

                if analysis["languages"]:
                    result += "**Языки программирования:**\n"
                    for lang, count in sorted(analysis["languages"].items(), key=lambda x: x[1], reverse=True):
                        result += f"• {lang}: {count} файлов\n"
            else:
                result += f"**Размер:** {analysis['size']} байт\n"
                result += f"**Язык:** {analysis.get('language', 'неизвестен')}\n"

                # Анализируем зависимости с учетом глубины
                deps_result = self.find_file_dependencies(str(component))
                if "•" in deps_result:
                    deps_lines = deps_result.split("\n")[2:]  # Пропускаем заголовок
                    analysis["dependencies"] = [line.strip("• ").strip() for line in deps_lines if line.strip()]

                    # Анализируем зависимости зависимостей (глубина 2)
                    if self.max_dependency_depth > 1:
                        deep_deps = set()
                        for dep in analysis["dependencies"][:5]:  # Ограничиваем для производительности
                            dep_result = self.find_file_dependencies(dep)
                            if "•" in dep_result:
                                dep_lines = dep_result.split("\n")[2:]
                                for line in dep_lines:
                                    deep_dep = line.strip("• ").strip()
                                    if deep_dep and deep_dep != dep:
                                        deep_deps.add(deep_dep)

                        if deep_deps:
                            analysis["deep_dependencies"] = list(deep_deps)[:10]  # Ограничиваем вывод

                if analysis["dependencies"]:
                    result += "**Зависимости:**\n"
                    for dep in analysis["dependencies"]:
                        result += f"• {dep}\n"

                    if "deep_dependencies" in analysis and analysis["deep_dependencies"]:
                        result += "\n**Глубокие зависимости:**\n"
                        for dep in analysis["deep_dependencies"]:
                            result += f"  • {dep}\n"

            return result

        except Exception as e:
            logger.error(f"Error analyzing component: {e}")
            return f"Ошибка анализа компонента: {str(e)}"

    def find_related_files(self, query: str) -> str:
        """
        Поиск файлов, связанных с запросом

        Args:
            query: Поисковый запрос

        Returns:
            Список связанных файлов
        """
        try:
            query_normalized = normalize_unicode_text(query)
            related_files = []

            # Ищем в документации
            if self.docs_dir.exists():
                for doc_file in self.docs_dir.rglob("*.md"):
                    try:
                        if doc_file.stat().st_size > self.max_file_size:
                            continue

                        with open(doc_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        content_normalized = normalize_unicode_text(content)

                        if query_normalized in content_normalized:
                            related_files.append({
                                "path": str(doc_file.relative_to(self.project_dir)),
                                "type": "documentation",
                                "matches": content_normalized.count(query_normalized)
                            })

                    except UnicodeDecodeError:
                        # Пропускаем файлы с некорректной кодировкой
                        continue
                    except Exception:
                        continue

            # Ищем в исходном коде
            src_dir = self.project_dir / "src"
            if src_dir.exists():
                for src_file in src_dir.rglob("*.py"):
                    try:
                        if src_file.stat().st_size > self.max_file_size:
                            continue

                        with open(src_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        content_normalized = normalize_unicode_text(content)

                        if query_normalized in content_normalized:
                            related_files.append({
                                "path": str(src_file.relative_to(self.project_dir)),
                                "type": "code",
                                "matches": content_normalized.count(query_normalized)
                            })

                    except UnicodeDecodeError:
                        # Пропускаем файлы с некорректной кодировкой
                        continue
                    except Exception:
                        continue

            # Сортируем по количеству совпадений
            related_files.sort(key=lambda x: x["matches"], reverse=True)
            related_files = related_files[:10]  # Ограничиваем вывод

            if not related_files:
                return f"Файлы, связанные с запросом '{query}', не найдены."

            result = f"📁 Файлы, связанные с запросом '{query}':\n\n"

            for file_info in related_files:
                result += f"• **{file_info['path']}** ({file_info['type']}) - {file_info['matches']} совпадений\n"

            return result

        except Exception as e:
            logger.error(f"Error finding related files: {e}")
            return f"Ошибка поиска связанных файлов: {str(e)}"