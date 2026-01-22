"""
ContextAnalyzerTool - инструмент для анализа контекста проекта
"""

import os
import re
import json
import logging
import unicodedata
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
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
    supported_extensions: list = [".md", ".txt", ".rst", ".py", ".js", ".ts", ".json", ".yaml", ".yml"]

    def __init__(self, project_dir: str = ".", docs_dir: str = "docs",
                 max_file_size: int = 1000000, supported_extensions: List[str] = None, **kwargs):
        """
        Инициализация ContextAnalyzerTool

        Args:
            project_dir: Корневая директория проекта
            docs_dir: Директория с документацией
            max_file_size: Максимальный размер файла для анализа
            supported_extensions: Поддерживаемые расширения файлов
        """
        super().__init__(**kwargs)
        self.project_dir = Path(project_dir)
        self.docs_dir = self.project_dir / docs_dir
        self.max_file_size = max_file_size
        self.supported_extensions = supported_extensions or [".md", ".txt", ".rst", ".py", ".js", ".ts", ".json", ".yaml", ".yml"]

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
            logger.error(f"Error in ContextAnalyzerTool._run: {e}")
            return f"Error: {str(e)}"

    def analyze_project_structure(self) -> str:
        """
        Анализ общей структуры проекта

        Returns:
            Описание структуры проекта
        """
        try:
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

            return result

        except Exception as e:
            logger.error(f"Error analyzing project structure: {e}")
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

            dependencies = set()

            # Анализируем импорты в Python файлах
            if target_file.suffix == ".py":
                try:
                    with open(target_file, 'r', encoding='utf-8') as f:
                        content = f.read()

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

                except Exception as e:
                    logger.error(f"Error analyzing Python imports: {e}")

            # Анализируем ссылки в Markdown файлах
            elif target_file.suffix == ".md":
                try:
                    with open(target_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Находим ссылки на файлы
                    link_patterns = [
                        r'\[([^\]]+)\]\(([^)]+\.md)\)',  # Markdown ссылки
                        r'\[([^\]]+)\]\(([^)]+\.py)\)',  # Ссылки на Python файлы
                        r'([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*\.py)',  # Python файлы в тексте
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

                except Exception as e:
                    logger.error(f"Error analyzing Markdown links: {e}")

            if not dependencies:
                return f"Зависимости для файла {file_path} не найдены."

            result = f"🔗 Зависимости файла {file_path}:\n\n"
            for dep in sorted(dependencies):
                result += f"• {dep}\n"

            return result

        except Exception as e:
            logger.error(f"Error finding dependencies: {e}")
            return f"Ошибка поиска зависимостей: {str(e)}"

    def get_task_context(self, task_description: str) -> str:
        """
        Получение контекстной информации для задачи

        Args:
            task_description: Описание задачи

        Returns:
            Контекстная информация
        """
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
                    except Exception as e:
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
                    except Exception as e:
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
            logger.error(f"Error getting task context: {e}")
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

                if analysis["dependencies"]:
                    result += "**Зависимости:**\n"
                    for dep in analysis["dependencies"]:
                        result += f"• {dep}\n"

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
                    except Exception as e:
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
                    except Exception as e:
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