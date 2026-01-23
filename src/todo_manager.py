"""
Модуль управления todo-листом проекта
"""

from pathlib import Path
from typing import List, Dict, Optional, Any
import yaml
import re
import logging
import os

logger = logging.getLogger(__name__)


class TodoItem:
    """Элемент todo-листа"""

    def __init__(self, text: str, level: int = 0, done: bool = False, skipped: bool = False, parent: Optional['TodoItem'] = None, comment: Optional[str] = None):
        """
        Инициализация элемента todo

        Args:
            text: Текст задачи
            level: Уровень вложенности (0 - корень)
            done: Выполнена ли задача
            skipped: Пропущена ли задача (не выполнена по решению, а не из-за невыполнения)
            parent: Родительский элемент
            comment: Комментарий к задаче (например, причина пропуска или краткое описание выполнения)
        """
        self.text = text.strip()
        self.level = level
        self.done = done
        self.skipped = skipped
        self.parent = parent
        self.children: List['TodoItem'] = []
        self.comment = comment
    
    def __repr__(self) -> str:
        if self.done:
            status = "[DONE]"
        elif self.skipped:
            status = "[SKIP]"
        else:
            status = "[TODO]"
        indent = "  " * self.level
        return f"{indent}{status} {self.text}"


class TodoManager:
    """Управление todo-листом проекта"""
    
    # Константы
    DEFAULT_MAX_FILE_SIZE = 1_000_000  # Максимальный размер файла todo по умолчанию (1 MB)
    
    def __init__(self, project_dir: Path, todo_format: str = "txt", max_file_size: Optional[int] = None):
        """
        Инициализация менеджера todo
        
        Args:
            project_dir: Директория проекта
            todo_format: Формат файла todo (txt, yaml, md)
        """
        self.project_dir = Path(project_dir)
        self.todo_format = todo_format
        self.max_file_size = max_file_size or self.DEFAULT_MAX_FILE_SIZE
        self.todo_files = self._find_todo_files()
        self.todo_file = self.todo_files[0] if self.todo_files else None  # Для обратной совместимости
        self.items: List[TodoItem] = []
        # Загрузка будет выполнена асинхронно при первом обращении
    
    def _find_todo_files(self) -> List[Path]:
        """
        Поиск всех файлов todo в директории проекта

        Returns:
            Список путей к найденным файлам todo
        """
        found_files = []
        possible_names = [
            f"todo.{self.todo_format}",
            "todo.txt",
            "TODO.txt",
            "todo.yaml",
            "TODO.md",
            "todo.md",
        ]

        # Сначала ищем в корне проекта
        for name in possible_names:
            file_path = self.project_dir / name
            if file_path.exists():
                found_files.append(file_path)

        # Затем ищем в поддиректории todo/
        todo_dir = self.project_dir / "todo"
        if todo_dir.exists() and todo_dir.is_dir():
            # Ищем файлы в todo/ директории
            for name in possible_names:
                file_path = todo_dir / name
                if file_path.exists() and file_path not in found_files:
                    found_files.append(file_path)

            # Ищем CURRENT.md, DEBT.md, ROADMAP.md в todo/
            common_todo_names = ["CURRENT.md", "DEBT.md", "ROADMAP.md"]
            for name in common_todo_names:
                file_path = todo_dir / name
                if file_path.exists() and file_path not in found_files:
                    found_files.append(file_path)

        return found_files

    def _find_todo_file(self) -> Optional[Path]:
        """
        Поиск основного файла todo в директории проекта (для обратной совместимости)

        Returns:
            Path к первому найденному файлу todo или None
        """
        files = self._find_todo_files()
        return files[0] if files else None
    
    def _detect_file_format(self) -> str:
        """
        Определение формата файла TODO на основе расширения и конфигурации
        
        Returns:
            Формат файла: 'yaml', 'md', или 'txt'
        
        Raises:
            ValueError: Если формат не поддерживается или не определен
        """
        if not self.todo_file:
            # Если файл не найден, используем формат из конфигурации
            return self.todo_format
        
        # Получаем расширение файла
        file_suffix = self.todo_file.suffix.lower()
        
        # Поддерживаемые форматы
        supported_formats = {
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'md',
            '.markdown': 'md',
            '.txt': 'txt',
            '': 'txt'  # Файлы без расширения считаем текстовыми
        }
        
        # Определяем формат по расширению
        detected_format = supported_formats.get(file_suffix, None)
        
        # Если формат определен по расширению, используем его
        if detected_format:
            # Проверяем соответствие с конфигурацией
            if self.todo_format != "txt" and detected_format != self.todo_format:
                logger.warning(
                    f"Несоответствие формата: файл имеет расширение {file_suffix} "
                    f"(формат: {detected_format}), но в конфигурации указан {self.todo_format}. "
                    f"Используется формат файла: {detected_format}"
                )
            return detected_format
        
        # Если расширение не распознано, используем формат из конфигурации
        if self.todo_format in ['yaml', 'md', 'txt']:
            logger.warning(
                f"Расширение файла {file_suffix} не распознано. "
                f"Используется формат из конфигурации: {self.todo_format}"
            )
            return self.todo_format
        
        # Если формат не определен, пробуем определить по содержимому
        logger.warning(
            f"Не удалось определить формат файла {self.todo_file}. "
            f"Пробуем определить по содержимому..."
        )
        
        # Пробуем прочитать первые несколько строк для определения формата
        try:
            with open(self.todo_file, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline() for _ in range(5)]
                content_preview = '\n'.join(first_lines)
                
                # Проверка на YAML (начинается с --- или содержит типичные YAML структуры)
                if content_preview.strip().startswith('---') or 'tasks:' in content_preview or 'todo:' in content_preview:
                    return 'yaml'
                
                # Проверка на Markdown (содержит чекбоксы или markdown синтаксис)
                if '- [' in content_preview or '# ' in content_preview:
                    return 'md'
                
                # По умолчанию текстовый формат
                return 'txt'
        except Exception as e:
            logger.error(f"Ошибка при определении формата файла: {e}", exc_info=True)
            # В случае ошибки используем формат из конфигурации или txt по умолчанию
            return self.todo_format if self.todo_format in ['yaml', 'md', 'txt'] else 'txt'
    
    async def _load_todos_async(self) -> None:
        """Асинхронная загрузка todo из всех найденных файлов с дедупликацией"""
        if not self.todo_files:
            self.items = []
            logger.debug(f"Файлы todo не найдены в {self.project_dir}, используем пустой список")
            return

        all_items = []
        loaded_files = []

        for todo_file in self.todo_files:
            try:
                # Проверка прав доступа на чтение
                if not os.access(todo_file, os.R_OK):
                    logger.warning(f"Нет прав на чтение файла todo: {todo_file}")
                    continue

                # Проверка размера файла
                try:
                    file_size = todo_file.stat().st_size
                    if file_size > self.max_file_size:
                        logger.error(
                            f"Файл todo слишком большой ({file_size} байт, максимум {self.max_file_size}): {todo_file}"
                        )
                        continue
                except OSError as e:
                    logger.error(f"Ошибка проверки размера файла todo: {todo_file}", exc_info=True)
                    continue

                # Определяем формат файла
                file_format = self._detect_file_format_for_file(todo_file)

                # Загружаем задачи из файла
                file_items = self._load_from_file(todo_file, file_format)
                all_items.extend(file_items)
                loaded_files.append(todo_file)

                logger.debug(f"Загружено {len(file_items)} задач из {todo_file}")

            except Exception as e:
                logger.error(
                    f"Ошибка при загрузке todo из файла {todo_file}",
                    exc_info=True,
                    extra={
                        "todo_file": str(todo_file),
                        "error_type": type(e).__name__
                    }
                )

        # Дедупликация задач
        self.items = await self._deduplicate_tasks(all_items)

        if loaded_files:
            logger.info(f"Загружено {len(self.items)} уникальных задач из {len(loaded_files)} файлов: {[str(f) for f in loaded_files]}")
        else:
            logger.warning("Не удалось загрузить ни один файл todo, используем пустой список задач")

    def _load_todos(self) -> None:
        """Загрузка todo из всех найденных файлов с дедупликацией (синхронная версия для обратной совместимости)"""
        # Этот метод больше не используется - загрузка происходит асинхронно через ensure_loaded()
        pass

    def _analyze_todo_structure(self, content: str) -> Dict[str, Any]:
        """Анализ структуры TODO файла для определения оптимального алгоритма разбора"""

        lines = content.split('\n')
        analysis = {
            'total_lines': len(lines),
            'checkbox_lines': 0,
            'header_lines': 0,
            'empty_lines': 0,
            'has_markdown_headers': False,
            'has_checkboxes': False,
            'estimated_tasks': 0,
            'structure_type': 'unknown'
        }

        for line in lines:
            line = line.strip()
            if not line:
                analysis['empty_lines'] += 1
                continue

            # Проверяем чекбоксы
            if '- [' in line and (']' in line):
                analysis['checkbox_lines'] += 1
                analysis['has_checkboxes'] = True

            # Проверяем заголовки Markdown
            if line.startswith('#'):
                analysis['header_lines'] += 1
                analysis['has_markdown_headers'] = True

        # Определяем тип структуры
        if analysis['has_checkboxes'] and analysis['has_markdown_headers']:
            analysis['structure_type'] = 'markdown_with_checkboxes'
        elif analysis['has_checkboxes']:
            analysis['structure_type'] = 'simple_checkboxes'
        elif analysis['has_markdown_headers']:
            analysis['structure_type'] = 'markdown_headers'
        else:
            analysis['structure_type'] = 'plain_text'

        # Оцениваем количество задач
        if analysis['has_checkboxes']:
            analysis['estimated_tasks'] = analysis['checkbox_lines']
        else:
            # Для обычного текста считаем непустые строки как потенциальные задачи
            analysis['estimated_tasks'] = analysis['total_lines'] - analysis['empty_lines'] - analysis['header_lines']

        return analysis

    def _optimize_parsing_strategy(self, file_path: Path) -> Dict[str, Any]:
        """Определяет оптимальную стратегию парсинга файла"""

        try:
            content = file_path.read_text(encoding='utf-8')
            analysis = self._analyze_todo_structure(content)

            # Пока используем стандартную стратегию для всех файлов
            return {
                'strategy': 'standard',
                'analysis': analysis
            }

        except Exception as e:
            logger.warning(f"Ошибка при определении стратегии парсинга для {file_path}: {e}")
            return {
                'strategy': 'standard',
                'analysis': {}
            }

    def _detect_file_format_for_file(self, file_path: Path) -> str:
        """Определение формата файла для конкретного файла"""
        if not file_path.exists():
            return self.todo_format

        # Получаем расширение файла
        file_suffix = file_path.suffix.lower()

        # Поддерживаемые форматы
        supported_formats = {
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'md',
            '.txt': 'txt',
        }

        # Проверяем расширение
        if file_suffix in supported_formats:
            return supported_formats[file_suffix]

        # Если расширение неизвестно, пытаемся определить по содержимому
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content_preview = f.read(1024)

                # Проверка на YAML
                if content_preview.strip().startswith('---') or ': ' in content_preview:
                    return 'yaml'

                # Проверка на Markdown (содержит чекбоксы или markdown синтаксис)
                if '- [' in content_preview or '# ' in content_preview:
                    return 'md'

                # По умолчанию текстовый формат
                return 'txt'
        except Exception as e:
            logger.error(f"Ошибка при определении формата файла {file_path}: {e}", exc_info=True)
            # В случае ошибки используем формат из конфигурации или txt по умолчанию
            return self.todo_format if self.todo_format in ['yaml', 'md', 'txt'] else 'txt'

    def _load_from_file(self, file_path: Path, file_format: str) -> List[TodoItem]:
        """Загрузка задач из конкретного файла"""
        try:
            if file_format == "yaml":
                return self._load_from_yaml_file(file_path)
            elif file_format == "md":
                return self._load_from_markdown_file(file_path)
            else:
                return self._load_from_text_file(file_path)
        except Exception as e:
            logger.error(f"Ошибка при загрузке файла {file_path}: {e}")
            return []

    async def _deduplicate_tasks(self, items: List[TodoItem]) -> List[TodoItem]:
        """Семантическая дедупликация задач с использованием LLM"""
        if not items:
            return items

        # Сначала выполняем простую дедупликацию по тексту
        text_deduplicated = self._deduplicate_by_text(items)

        # Затем выполняем семантическую дедупликацию
        semantic_deduplicated = await self._deduplicate_semantic(text_deduplicated)

        return semantic_deduplicated

    def _deduplicate_by_text(self, items: List[TodoItem]) -> List[TodoItem]:
        """Простая дедупликация по нормализованному тексту"""
        seen_texts = set()
        unique_items = []

        for item in items:
            # Нормализуем текст задачи для сравнения (убираем лишние пробелы)
            normalized_text = ' '.join(item.text.split())

            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_items.append(item)
            else:
                logger.debug(f"Удален текстовый дубликат задачи: '{item.text}'")

        return unique_items

    async def _deduplicate_semantic(self, items: List[TodoItem]) -> List[TodoItem]:
        """Семантическая дедупликация задач с использованием LLM"""
        if len(items) <= 1:
            return items

        try:
            # Сначала группируем задачи по простым критериям (ключевые слова)
            groups = self._group_similar_tasks(items)

            unique_items = []

            for group in groups:
                if len(group) == 1:
                    # В группе только одна задача - добавляем как уникальную
                    unique_items.extend(group)
                else:
                    # В группе несколько задач - используем LLM для точного сравнения
                    group_unique = await self._deduplicate_group_with_llm(group)
                    unique_items.extend(group_unique)

            removed_count = len(items) - len(unique_items)
            if removed_count > 0:
                logger.info(f"Удалено {removed_count} семантических дубликатов задач, осталось {len(unique_items)} уникальных")

            return unique_items

        except Exception as e:
            logger.warning(f"Ошибка при семантической дедупликации, возвращаем исходный список: {e}")
            return items

    def _group_similar_tasks(self, items: List[TodoItem]) -> List[List[TodoItem]]:
        """Группирует задачи по простым критериям похожести"""
        groups = []

        # Ключевые слова для группировки
        keywords = [
            'server', 'api', 'database', 'user', 'auth', 'test', 'doc', 'file',
            'module', 'class', 'function', 'method', 'interface', 'service',
            'cache', 'config', 'logging', 'error', 'exception', 'validation'
        ]

        used_indices = set()

        for i, item1 in enumerate(items):
            if i in used_indices:
                continue

            current_group = [item1]
            used_indices.add(i)

            item1_text_lower = item1.text.lower()

            # Ищем похожие задачи
            for j, item2 in enumerate(items):
                if j in used_indices:
                    continue

                item2_text_lower = item2.text.lower()

                # Проверяем совпадение ключевых слов
                common_keywords = 0
                for keyword in keywords:
                    if keyword in item1_text_lower and keyword in item2_text_lower:
                        common_keywords += 1

                # Если есть общие ключевые слова или тексты очень похожи
                if common_keywords >= 1 or self._texts_similar(item1_text_lower, item2_text_lower):
                    current_group.append(item2)
                    used_indices.add(j)

            groups.append(current_group)

        return groups

    def _texts_similar(self, text1: str, text2: str) -> bool:
        """Простая проверка похожести текстов"""
        # Убираем пунктуацию и сравниваем
        import re
        text1_clean = re.sub(r'[^\w\s]', '', text1)
        text2_clean = re.sub(r'[^\w\s]', '', text2)

        words1 = set(text1_clean.split())
        words2 = set(text2_clean.split())

        # Если 50% слов совпадают, считаем тексты похожими
        common_words = words1.intersection(words2)
        total_words = words1.union(words2)

        if len(total_words) == 0:
            return False

        similarity = len(common_words) / len(total_words)
        return similarity >= 0.5

    async def _deduplicate_group_with_llm(self, group: List[TodoItem]) -> List[TodoItem]:
        """Дедупликация группы задач с использованием LLM"""
        if len(group) <= 1:
            return group

        try:
            from src.llm.llm_manager import LLMManager
            llm_manager = LLMManager(config_path="config/llm_settings.yaml")

            # Для групп до 3 задач делаем попарное сравнение
            if len(group) <= 3:
                return await self._deduplicate_small_group(llm_manager, group)
            else:
                # Для больших групп используем другой подход
                logger.warning(f"Группа слишком большая ({len(group)} задач), пропускаем LLM дедупликацию")
                return group

        except Exception as e:
            logger.warning(f"Ошибка при дедупликации группы: {e}")
            return group

    async def _deduplicate_small_group(self, llm_manager: 'LLMManager', group: List[TodoItem]) -> List[TodoItem]:
        """Дедупликация небольшой группы задач"""
        unique_items = []
        processed_indices = set()

        for i, item1 in enumerate(group):
            if i in processed_indices:
                continue

            is_duplicate = False

            # Сравниваем только со следующими задачами (оптимизация)
            for j in range(i + 1, len(group)):
                if j in processed_indices:
                    continue

                if await self._are_tasks_similar(llm_manager, group[i], group[j]):
                    processed_indices.add(j)
                    logger.info(f"Найден семантический дубликат: '{group[i].text}' ↔ '{group[j].text}'")

            # Добавляем текущую задачу как уникальную
            unique_items.append(group[i])

        return unique_items

    async def _are_tasks_similar(self, llm_manager: 'LLMManager', task1: TodoItem, task2: TodoItem) -> bool:
        """Проверяет семантическую похожесть двух задач с использованием LLM"""

        prompt = f"""Проанализируй две задачи и определи, являются ли они семантически одинаковыми (дубликатами).

Задача 1: "{task1.text}"
Задача 2: "{task2.text}"

Критерии определения дубликата:
- Задачи описывают одну и ту же работу
- Разные формулировки, но одинаковый смысл
- Одна задача является уточнением или детализацией другой
- Задачи ведут к одинаковому результату

Примеры дубликатов:
- "Создать API для пользователей" ↔ "Реализовать user management API"
- "Исправить баг в авторизации" ↔ "Починить login functionality"
- "Добавить валидацию email" ↔ "Реализовать проверку корректности email адресов"

НЕ являются дубликатами:
- "Создать API" ↔ "Создать базу данных"
- "Исправить баг в авторизации" ↔ "Добавить двухфакторную аутентификацию"
- "Валидация email" ↔ "Валидация пароля"

Ответь только "YES" или "NO" и краткое обоснование (1 предложение)."""

        try:
            response = await llm_manager.generate_response(
                prompt=prompt
            )

            response_text = response.content.strip().upper()

            # Ищем YES/NO в ответе
            if "YES" in response_text:
                return True
            elif "NO" in response_text:
                return False
            else:
                # Неопределенный ответ - считаем не дубликатами
                logger.debug(f"Неопределенный ответ LLM для сравнения задач: {response_text}")
                return False

        except Exception as e:
            logger.warning(f"Ошибка при сравнении задач через LLM: {e}")
            return False

    def _load_from_yaml_file(self, file_path: Path) -> List[TodoItem]:
        """Загрузка задач из YAML файла"""
        try:
            # Читаем содержимое файла
            try:
                content = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    content = file_path.read_text(encoding='cp1251')
                    logger.info(f"YAML файл успешно прочитан с кодировкой cp1251: {file_path}")
                except Exception:
                    logger.error(f"Не удалось прочитать YAML файл с альтернативными кодировками: {file_path}")
                    return []

            # Парсим YAML
            try:
                data = yaml.safe_load(content) or {}
            except yaml.YAMLError as e:
                logger.error(f"Ошибка парсинга YAML файла: {file_path}", exc_info=True)
                return []

            items = []

            def parse_items(items_data: List[Any], level: int = 0) -> None:
                for item_data in items_data:
                    if isinstance(item_data, dict):
                        text = item_data.get('text', item_data.get('task', ''))
                        done = item_data.get('done', False)
                        skipped = item_data.get('skipped', False)
                        comment = item_data.get('comment', None)
                        items.append(TodoItem(text, level=level, done=done, skipped=skipped, comment=comment))

                        # Рекурсивно обрабатываем подзадачи
                        children = item_data.get('children', item_data.get('items', []))
                        if children:
                            parse_items(children, level + 1)
                    elif isinstance(item_data, str):
                        # Простая текстовая задача
                        items.append(TodoItem(item_data, level=level))

            # Если данные - список, обрабатываем как список задач
            if isinstance(data, list):
                parse_items(data)
            else:
                # Если данные - словарь, ищем ключ tasks или items
                tasks_data = data.get('tasks', data.get('items', data.get('todo', [])))
                if isinstance(tasks_data, list):
                    parse_items(tasks_data)

            return items

        except Exception as e:
            logger.error(f"Ошибка при загрузке YAML файла {file_path}: {e}", exc_info=True)
            return []

    def _load_from_markdown_file(self, file_path: Path) -> List[TodoItem]:
        """Загрузка задач из Markdown файла"""
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding='cp1251')
                logger.info(f"Markdown файл успешно прочитан с кодировкой cp1251: {file_path}")
            except Exception:
                logger.error(f"Не удалось прочитать Markdown файл с альтернативными кодировками: {file_path}")
                return []
        except Exception as e:
            logger.error(f"Ошибка чтения Markdown файла {file_path}: {e}", exc_info=True)
            return []

        items = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            original_line = line
            stripped_line = line.strip()
            if not stripped_line:
                continue

            # Ищем чекбоксы: - [ ] или - [x] или - [X]
            # Проверяем как в оригинальной строке, так и в stripped версии
            checkbox_found = False

            # Сначала проверяем в оригинальной строке (сохраняя отступы)
            if '- [' in original_line:
                checkbox_pos = original_line.find('- [')
                if checkbox_pos >= 0 and len(original_line) > checkbox_pos + 5:
                    # Ищем закрывающую скобку ]
                    bracket_end = original_line.find(']', checkbox_pos + 2)
                    if bracket_end > checkbox_pos + 2:
                        checkbox_part = original_line[checkbox_pos + 2:bracket_end + 1]
                        if checkbox_part in ['[ ]', '[x]', '[X]']:
                            done = checkbox_part.lower() == '[x]'
                            text_start = bracket_end + 1
                            text = original_line[text_start:].strip()
                            items.append(TodoItem(text, done=done))
                            checkbox_found = True
                            logger.debug(f"Найдена задача в строке {line_num}: '{text}' (done={done})")

            # Если не нашли в оригинальной, проверяем в stripped версии
            if not checkbox_found and '- [' in stripped_line:
                checkbox_pos = stripped_line.find('- [')
                if checkbox_pos >= 0 and len(stripped_line) > checkbox_pos + 6:
                    checkbox_part = stripped_line[checkbox_pos + 3:checkbox_pos + 6]
                    if checkbox_part in ['[ ]', '[x]', '[X]']:
                        done = checkbox_part.lower() == '[x]'
                        text = stripped_line[checkbox_pos + 7:].strip()
                        items.append(TodoItem(text, done=done))
                        checkbox_found = True
                        logger.debug(f"Найдена задача в строке {line_num} (stripped): '{text}' (done={done})")


        logger.info(f"Загружено {len(items)} задач из Markdown файла {file_path}")
        return items

    def _load_from_text_file(self, file_path: Path) -> List[TodoItem]:
        """Загрузка задач из текстового файла"""
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding='cp1251')
                logger.info(f"Текстовый файл успешно прочитан с кодировкой cp1251: {file_path}")
            except Exception:
                logger.error(f"Не удалось прочитать текстовый файл с альтернативными кодировками: {file_path}")
                return []
        except Exception as e:
            logger.error(f"Ошибка чтения текстового файла {file_path}: {e}", exc_info=True)
            return []

        items = []
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):  # Пропускаем пустые строки и комментарии
                # Проверяем на формат с чекбоксами
                if line.startswith('- [') and len(line) > 5:
                    checkbox_part = line[3:6]
                    if checkbox_part in ['[ ]', '[x]', '[X]']:
                        done = checkbox_part.lower() == '[x]'
                        text = line[7:].strip()
                        items.append(TodoItem(text, done=done))
                else:
                    # Обычная текстовая задача
                    items.append(TodoItem(line))

        return items
    
    def _load_from_text(self) -> None:
        """Загрузка todo из текстового файла"""
        try:
            content = self.todo_file.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            logger.error(
                f"Ошибка декодирования файла todo (не UTF-8): {self.todo_file}",
                exc_info=True,
                extra={"error_type": "UnicodeDecodeError"}
            )
            # Пробуем другие кодировки
            try:
                content = self.todo_file.read_text(encoding='cp1251')
                logger.info(f"Файл успешно прочитан с кодировкой cp1251")
            except Exception:
                logger.error(f"Не удалось прочитать файл с альтернативными кодировками")
                self.items = []
                return
        except Exception as e:
            logger.error(
                f"Ошибка чтения текстового файла todo: {self.todo_file}",
                exc_info=True,
                extra={"error_type": type(e).__name__}
            )
            self.items = []
            return
        
        lines = content.split('\n')
        
        items = []
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Определяем уровень вложенности по отступам
            level = len(line) - len(line.lstrip())
            level = level // 2  # Предполагаем отступ в 2 пробела
            
            # Убираем номера и маркеры списка
            text = re.sub(r'^\d+[.)]\s*', '', line)
            text = re.sub(r'^[-*+]\s+', '', text)
            
            # Парсим комментарий (формат: текст  # комментарий)
            comment = None
            if '  # ' in text or ' # ' in text:
                parts = re.split(r'\s+#\s+', text, 1)
                if len(parts) == 2:
                    text = parts[0].strip()
                    comment = parts[1].strip()
            
            text = text.strip()
            
            if text:
                items.append(TodoItem(text, level=level, comment=comment))
        
        self.items = items
    
    def _load_from_markdown(self) -> None:
        """Загрузка todo из Markdown файла с чекбоксами"""
        try:
            content = self.todo_file.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            logger.error(
                f"Ошибка декодирования Markdown файла todo (не UTF-8): {self.todo_file}",
                exc_info=True,
                extra={"error_type": "UnicodeDecodeError"}
            )
            try:
                content = self.todo_file.read_text(encoding='cp1251')
                logger.info(f"Markdown файл успешно прочитан с кодировкой cp1251")
            except Exception:
                logger.error(f"Не удалось прочитать Markdown файл с альтернативными кодировками")
                self.items = []
                return
        except Exception as e:
            logger.error(
                f"Ошибка чтения Markdown файла todo: {self.todo_file}",
                exc_info=True,
                extra={"error_type": type(e).__name__}
            )
            self.items = []
            return
        
        lines = content.split('\n')
        
        items = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Парсинг чекбоксов: - [ ] или - [x] или - [-] с возможным комментарием
            # Формат: - [x] Текст задачи <!-- комментарий -->
            # Где: [x] = выполнена, [-] = пропущена, [ ] = не выполнена
            # Используем более гибкий regex для парсинга комментариев
            checkbox_match = re.match(r'^(\s*)- \[([ xX-])\]\s*(.+?)(?:\s*<!--\s*(.+?)\s*-->)?\s*$', line)
            if checkbox_match:
                indent = len(checkbox_match.group(1))
                status = checkbox_match.group(2).lower()
                text = checkbox_match.group(3).strip()
                comment = checkbox_match.group(4) if checkbox_match.group(4) else None

                # Определяем статус задачи
                if status == 'x':
                    # [x] = выполнена
                    done = True
                    skipped = False
                elif status == '-':
                    # [-] = пропущена
                    done = False
                    skipped = True
                else:
                    # [ ] = не выполнена
                    done = False
                    skipped = False

                level = indent // 2
                items.append(TodoItem(text, level=level, done=done, skipped=skipped, comment=comment))
            # Парсинг обычных списков
            elif re.match(r'^\s*[-*+]\s+', line):
                level = (len(line) - len(line.lstrip())) // 2
                # Парсинг с возможным комментарием
                text_match = re.match(r'^\s*[-*+]\s+(.+?)(?:\s*<!--\s*(.+?)\s*-->)?$', line)
                if text_match:
                    text = text_match.group(1).strip()
                    comment = text_match.group(2) if text_match.group(2) else None
                    if text:
                        items.append(TodoItem(text, level=level, comment=comment))
        
        self.items = items
    
    def _load_from_yaml(self) -> None:
        """Загрузка todo из YAML файла"""
        try:
            content = self.todo_file.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            logger.error(
                f"Ошибка декодирования YAML файла todo (не UTF-8): {self.todo_file}",
                exc_info=True,
                extra={"error_type": "UnicodeDecodeError"}
            )
            try:
                content = self.todo_file.read_text(encoding='cp1251')
                logger.info(f"YAML файл успешно прочитан с кодировкой cp1251")
            except Exception:
                logger.error(f"Не удалось прочитать YAML файл с альтернативными кодировками")
                self.items = []
                return
        except Exception as e:
            logger.error(
                f"Ошибка чтения YAML файла todo: {self.todo_file}",
                exc_info=True,
                extra={"error_type": type(e).__name__}
            )
            self.items = []
            return
        
        try:
            data = yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            logger.error(
                f"Ошибка парсинга YAML файла todo: {self.todo_file}",
                exc_info=True,
                extra={
                    "error_type": "YAMLError",
                    "yaml_error": str(e)
                }
            )
            self.items = []
            return
        
        items = []
        
        def parse_items(items_data: List[Any], level: int = 0) -> None:
            for item_data in items_data:
                if isinstance(item_data, dict):
                    text = item_data.get('text', item_data.get('task', ''))
                    done = item_data.get('done', False)
                    skipped = item_data.get('skipped', False)
                    comment = item_data.get('comment', None)
                    items.append(TodoItem(text, level=level, done=done, skipped=skipped, comment=comment))

                    if 'children' in item_data:
                        parse_items(item_data['children'], level + 1)
                elif isinstance(item_data, str):
                    items.append(TodoItem(item_data, level=level))
        
        if 'tasks' in data:
            parse_items(data['tasks'])
        elif 'todo' in data:
            parse_items(data['todo'])
        elif isinstance(data, list):
            parse_items(data)
        
        self.items = items

    # Методы для обратной совместимости
    def _load_from_yaml(self) -> None:
        """Загрузка todo из YAML файла (для обратной совместимости)"""
        if self.todo_file:
            self.items = self._load_from_yaml_file(self.todo_file)

    def _load_from_markdown(self) -> None:
        """Загрузка todo из Markdown файла (для обратной совместимости)"""
        if self.todo_file:
            self.items = self._load_from_markdown_file(self.todo_file)

    def _load_from_text(self) -> None:
        """Загрузка todo из текстового файла (для обратной совместимости)"""
        if self.todo_file:
            self.items = self._load_from_text_file(self.todo_file)

    async def ensure_loaded(self) -> None:
        """Обеспечивает загрузку задач"""
        if not self.items:  # Загружаем только если еще не загружено
            await self._load_todos_async()
        """Асинхронная загрузка todo из всех найденных файлов с дедупликацией"""
        if not self.todo_files:
            self.items = []
            logger.debug(f"Файлы todo не найдены в {self.project_dir}, используем пустой список")
            return

        all_items = []
        loaded_files = []

        for todo_file in self.todo_files:
            try:
                # Проверка прав доступа на чтение
                if not os.access(todo_file, os.R_OK):
                    logger.warning(f"Нет прав на чтение файла todo: {todo_file}")
                    continue

                # Проверка размера файла
                try:
                    file_size = todo_file.stat().st_size
                    if file_size > self.max_file_size:
                        logger.error(
                            f"Файл todo слишком большой ({file_size} байт, максимум {self.max_file_size}): {todo_file}"
                        )
                        continue
                except OSError as e:
                    logger.error(f"Ошибка проверки размера файла todo: {todo_file}", exc_info=True)
                    continue

                # Определяем формат файла
                file_format = self._detect_file_format_for_file(todo_file)

                # Загружаем задачи из файла
                file_items = self._load_from_file(todo_file, file_format)
                all_items.extend(file_items)
                loaded_files.append(todo_file)

                logger.debug(f"Загружено {len(file_items)} задач из {todo_file}")

            except Exception as e:
                logger.error(
                    f"Ошибка при загрузке todo из файла {todo_file}",
                    exc_info=True,
                    extra={
                        "todo_file": str(todo_file),
                        "error_type": type(e).__name__
                    }
                )

        # Дедупликация задач
        self.items = await self._deduplicate_tasks(all_items)

        if loaded_files:
            logger.info(f"Загружено {len(self.items)} уникальных задач из {len(loaded_files)} файлов: {[str(f) for f in loaded_files]}")
        else:
            logger.warning("Не удалось загрузить ни один файл todo, используем пустой список задач")

    def get_pending_tasks(self) -> List[TodoItem]:
        """
        Получение непройденных задач

        Returns:
            Список невыполненных задач (исключая пропущенные)
        """
        return [item for item in self.items if not item.done and not item.skipped]
    
    def get_all_tasks(self) -> List[TodoItem]:
        """
        Получение всех задач
        
        Returns:
            Список всех задач
        """
        return self.items
    
    def mark_task_done(self, task_text: str, comment: Optional[str] = None) -> bool:
        """
        Отметка задачи как выполненной

        Args:
            task_text: Текст задачи для отметки
            comment: Комментарий к выполнению (опционально, дата/время добавляется автоматически)

        Returns:
            True если задача найдена и отмечена
        """
        from datetime import datetime

        for item in self.items:
            if item.text == task_text or item.text.startswith(task_text):
                item.done = True
                item.skipped = False  # Сбрасываем статус пропущенной
                # Добавляем комментарий с датой/временем
                if comment:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    item.comment = f"{comment} - {timestamp}"
                elif not item.comment:
                    # Если комментария нет, добавляем только дату/время
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    item.comment = f"Выполнено - {timestamp}"
                self._save_todos()
                return True
        return False

    def mark_task_skipped(self, task_text: str, comment: Optional[str] = None) -> bool:
        """
        Отметка задачи как пропущенной

        Args:
            task_text: Текст задачи для отметки
            comment: Комментарий к пропуску (опционально, дата/время добавляется автоматически)

        Returns:
            True если задача найдена и отмечена
        """
        from datetime import datetime

        for item in self.items:
            if item.text == task_text or item.text.startswith(task_text):
                item.done = False  # Пропущенная задача не считается выполненной
                item.skipped = True
                # Добавляем комментарий с датой/временем
                if comment:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    item.comment = f"{comment} - {timestamp}"
                elif not item.comment:
                    # Если комментария нет, добавляем только дату/время
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    item.comment = f"Пропущено - {timestamp}"
                self._save_todos()
                return True
        return False
    
    def _save_todos(self) -> None:
        """
        Сохранение todo в файл
        
        Сохраняет изменения статуса задач обратно в файл todo в соответствующем формате.
        """
        if not self.todo_file or not self.todo_file.exists():
            logger.debug(f"Файл todo не найден, пропускаем сохранение")
            return
        
        # Проверка прав доступа на запись
        if not os.access(self.todo_file, os.W_OK):
            logger.warning(f"Нет прав на запись файла todo: {self.todo_file}")
            return
        
        try:
            # Определяем формат файла
            file_format = self._detect_file_format()
            
            if file_format == "yaml":
                self._save_to_yaml()
            elif file_format == "md":
                self._save_to_markdown()
            else:
                self._save_to_text()
            
            logger.debug(f"Todo файл обновлен: {self.todo_file}")
        except Exception as e:
            logger.error(
                f"Ошибка при сохранении todo в файл {self.todo_file}",
                exc_info=True,
                extra={
                    "todo_file": str(self.todo_file),
                    "error_type": type(e).__name__
                }
            )
    
    def _save_to_text(self) -> None:
        """Сохранение todo в текстовый файл"""
        if not self.todo_file:
            return
        
        lines = []
        for item in self.items:
            indent = "  " * item.level
            # Определяем статус: [x] для выполненных, [-] для пропущенных, [ ] для невыполненных
            if item.done:
                status = "[x]"
            elif item.skipped:
                status = "[-]"
            else:
                status = "[ ]"
            # Добавляем комментарий если есть
            if item.comment:
                lines.append(f"{indent}{status} {item.text}  # {item.comment}")
            else:
                lines.append(f"{indent}{status} {item.text}")
        
        content = "\n".join(lines)
        if lines:
            content += "\n"
        
        self.todo_file.write_text(content, encoding='utf-8')
    
    def _save_to_markdown(self) -> None:
        """Сохранение todo в Markdown файл с чекбоксами"""
        if not self.todo_file:
            return
        
        lines = []
        for item in self.items:
            indent = "  " * item.level
            # Определяем чекбокс: [x] для выполненных, [-] для пропущенных, [ ] для невыполненных
            if item.done:
                checkbox = "[x]"
            elif item.skipped:
                checkbox = "[-]"
            else:
                checkbox = "[ ]"
            # Добавляем комментарий если есть
            if item.comment:
                lines.append(f"{indent}- {checkbox} {item.text} <!-- {item.comment} -->")
            else:
                lines.append(f"{indent}- {checkbox} {item.text}")
        
        content = "\n".join(lines)
        if lines:
            content += "\n"
        
        self.todo_file.write_text(content, encoding='utf-8')
    
    def _save_to_yaml(self) -> None:
        """Сохранение todo в YAML файл"""
        if not self.todo_file:
            return
        
        tasks = []
        for item in self.items:
            task_data = {
                "text": item.text,
                "done": item.done
            }
            if item.skipped:
                task_data["skipped"] = item.skipped
            if item.level > 0:
                task_data["level"] = item.level
            if item.comment:
                task_data["comment"] = item.comment
            tasks.append(task_data)
        
        data = {"tasks": tasks}
        content = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        self.todo_file.write_text(content, encoding='utf-8')
    
    def get_task_hierarchy(self) -> Dict[str, Any]:
        """
        Получение иерархии задач

        Returns:
            Словарь с иерархией задач, содержащий:
            - 'total': общее количество задач
            - 'pending': количество невыполненных задач
            - 'completed': количество выполненных задач
            - 'skipped': количество пропущенных задач
            - 'items': список словарей с информацией о каждой задаче
        """
        # Простая реализация - можно расширить для построения дерева
        return {
            'total': len(self.items),
            'pending': len(self.get_pending_tasks()),
            'completed': len([i for i in self.items if i.done]),
            'skipped': len([i for i in self.items if i.skipped]),
            'items': [{'text': item.text, 'level': item.level, 'done': item.done, 'skipped': item.skipped}
                     for item in self.items]
        }
