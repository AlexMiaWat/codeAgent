"""
LearningTool - инструмент для обучения на предыдущих задачах
"""

import json
import logging
import unicodedata
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    fcntl = None # type: ignore
    HAS_FCNTL = False
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import hashlib
from crewai.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


def normalize_unicode_text(text: Optional[str]) -> str:
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


class LearningTool(BaseTool):
    """
    Инструмент для обучения на предыдущих задачах и опыте.

    Позволяет:
    - Сохранять опыт выполнения задач
    - Искать похожие задачи в истории
    - Предоставлять рекомендации на основе предыдущего опыта
    """

    name: str = "LearningTool"
    description: str = """
    Инструмент для обучения на предыдущих задачах.
    Позволяет сохранять опыт, искать похожие задачи и давать рекомендации.
    """
    experience_dir: str = "smart_experience"
    max_experience_tasks: int = 1000
    experience_file: str = "experience.json"
    cache_file: str = "cache.json"
    lock_file: str = ""


    # Настройки индексации и кеширования
    enable_indexing: bool = True
    cache_size: int = 1000
    cache_ttl_seconds: int = 3600  # 1 час
    enable_cache_persistence: bool = False  # Сохранять кэш на диск

    def __init__(self, experience_dir: str = "smart_experience", max_experience_tasks: int = 1000,
                 enable_indexing: bool = True, cache_size: int = 1000, cache_ttl_seconds: int = 3600,
                 enable_cache_persistence: bool = False, **kwargs):
        """
        Инициализация LearningTool

        Args:
            experience_dir: Директория для хранения опыта
            max_experience_tasks: Максимальное количество задач в опыте
            enable_indexing: Включить индексацию для быстрого поиска
            cache_size: Максимальный размер кэша
            cache_ttl_seconds: Время жизни кэша в секундах
            enable_cache_persistence: Сохранять кэш на диск для persistence между запусками
        """
        super().__init__(**kwargs)
        self.experience_dir = Path(experience_dir)
        self.max_experience_tasks = max_experience_tasks
        self.enable_indexing = enable_indexing
        self.cache_size = cache_size
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_cache_persistence = enable_cache_persistence
        self.experience_file = self.experience_dir / "experience.json"

        # Создаем директорию опыта если не существует
        self.experience_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = str(self.experience_dir / (self.experience_file.name + ".lock"))
        # Инициализируем структуры индексации и кеширования
        self._search_index: Dict[str, Set[str]] = {}
        self._pattern_index: Dict[str, List[str]] = {}
        self._query_cache: Dict[str, Dict[str, Any]] = {}  # {query_hash: {result, timestamp}}
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }

        # Инициализируем файл опыта если не существует
        if not self.experience_file.exists():
            self._init_experience_file()
        else:
            # Загружаем существующий опыт и строим индексы
            self._load_and_index_experience()

        # Загружаем персистентный кэш если включено
        if self.enable_cache_persistence:
            self._load_persistent_cache()

    def _init_experience_file(self) -> None:
        """Инициализация файла опыта"""
        initial_data = {
            "version": "1.0",
            "tasks": [],
            "patterns": {},
            "statistics": {
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "average_execution_time": 0
            }
        }

        with open(self.experience_file, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)

    def _load_and_index_experience(self) -> None:
        """Загрузка опыта и построение индексов для быстрого поиска"""
        data = self._load_experience()
        tasks = data.get("tasks", [])

        if self.enable_indexing:
            # Строим индекс для поиска по словам
            self._search_index = {}
            self._pattern_index = {}

            for task in tasks:
                task_id = task.get("task_id", "")
                description = normalize_unicode_text(task.get("description", ""))
                patterns = task.get("patterns", [])

                # Индексируем слова из описания
                words = set(description.split())
                for word in words:
                    if word not in self._search_index:
                        self._search_index[word] = set()
                    self._search_index[word].add(task_id)

                # Индексируем паттерны
                for pattern in patterns:
                    if pattern not in self._pattern_index:
                        self._pattern_index[pattern] = []
                    self._pattern_index[pattern].append(task_id)

            logger.debug(f"Built search index with {len(self._search_index)} words and {len(self._pattern_index)} patterns")

    def _load_experience(self) -> Dict[str, Any]:
        """Загрузка данных опыта"""
        try:
                with open(self.experience_file, 'r', encoding='utf-8') as f:
                    if HAS_FCNTL:
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                        data = json.load(f)
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    else:
                        # Fallback for systems without fcntl (e.g., Windows)
                        # Используем временный файл блокировки
                        # В реальном приложении здесь нужна более сложная логика с таймаутом
                        # Для smoke-тестов достаточно простой проверки и задержки
                        retries = 5
                        lock_path = Path(self.lock_file)
                        while lock_path.exists() and retries > 0:
                            time.sleep(0.05)
                            retries -= 1
                        if lock_path.exists():
                            logger.warning(f"Could not acquire lock for reading {self.experience_file}. Proceeding without lock.")
                        data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"Failed to load experience from {self.experience_file}: {e}", exc_info=True)
            return {"version": "1.0", "tasks": [], "patterns": {}, "statistics": {}}

    def _save_experience(self, data: Dict[str, Any]):
        """Сохранение данных опыта"""
        try:
            with open(self.experience_file, 'w', encoding='utf-8') as f:
                if HAS_FCNTL:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                else:
                    # Fallback for systems without fcntl (e.g., Windows)
                    lock_path = Path(self.lock_file)
                    lock_path.touch()
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    if lock_path.exists():
                        lock_path.unlink() # Удаляем файл блокировки после записи
        except Exception as e:
            logger.error(f"Failed to save experience to {self.experience_file}: {e}", exc_info=True)

    def _run(self, action: str, **kwargs) -> str:
        """
        Выполнение действия с инструментом обучения

        Args:
            action: Действие (save_experience, find_similar, get_recommendations)
            **kwargs: Параметры действия

        Returns:
            Результат выполнения действия
        """
        try:
            if action == "save_experience":
                return self.save_task_experience(**kwargs)
            elif action == "find_similar":
                return self.find_similar_tasks(**kwargs)
            elif action == "get_recommendations":
                return self.get_recommendations(**kwargs)
            elif action == "get_statistics":
                return self.get_statistics()
            else:
                return f"Unknown action: {action}"

        except Exception as e:
            logger.error(f"Error in LearningTool._run with action '{action}': {e}", exc_info=True)
            return f"Error executing action '{action}': {str(e)}"

    def save_task_experience(self, task_id: str, task_description: str,
                           success: bool, execution_time: Optional[float] = None,
                           notes: str = "", patterns: List[str] = None) -> str:
        """
        Сохранение опыта выполнения задачи

        Args:
            task_id: ID задачи
            task_description: Описание задачи
            success: Успешность выполнения
            execution_time: Время выполнения в секундах
            notes: Дополнительные заметки
            patterns: Паттерны/шаблоны задачи

        Returns:
            Сообщение о сохранении
        """
        # Валидация входных параметров
        if not task_id or not isinstance(task_id, str):
            raise ValueError("task_id must be a non-empty string")

        if not task_description or not isinstance(task_description, str):
            raise ValueError("task_description must be a non-empty string")

        if not isinstance(success, bool):
            raise ValueError("success must be a boolean")

        if execution_time is not None and (not isinstance(execution_time, (int, float)) or execution_time < 0):
            raise ValueError("execution_time must be a non-negative number or None")

        if patterns is not None and not isinstance(patterns, list):
            raise ValueError("patterns must be a list or None")

        if patterns is not None:
            for pattern in patterns:
                if not isinstance(pattern, str):
                    raise ValueError("all patterns must be strings")

        data = self._load_experience()

        # Создаем запись о задаче
        task_record = {
            "task_id": task_id,
            "description": task_description,
            "success": success,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "notes": notes,
            "patterns": patterns or []
        }

        # Добавляем задачу в список
        data["tasks"].append(task_record)

        # Ограничиваем количество задач
        if len(data["tasks"]) > self.max_experience_tasks:
            data["tasks"] = data["tasks"][-self.max_experience_tasks:]

        # Обновляем паттерны
        if patterns:
            for pattern in patterns:
                if pattern not in data["patterns"]:
                    data["patterns"][pattern] = []
                data["patterns"][pattern].append(task_id)

        # Обновляем статистику
        data["statistics"]["total_tasks"] = len(data["tasks"])
        data["statistics"]["successful_tasks"] = sum(1 for t in data["tasks"] if t["success"])
        data["statistics"]["failed_tasks"] = data["statistics"]["total_tasks"] - data["statistics"]["successful_tasks"]

        if execution_time and data["statistics"]["total_tasks"] > 0:
            # Простое среднее (можно улучшить)
            total_time = sum(t.get("execution_time", 0) for t in data["tasks"] if t.get("execution_time"))
            data["statistics"]["average_execution_time"] = total_time / data["statistics"]["total_tasks"]

        self._save_experience(data)

        # Обновляем индексы после сохранения
        if self.enable_indexing:
            self._update_indexes(task_record)

        # Очищаем кэш, так как данные изменились
        self._clear_query_cache()

        return f"Опыт задачи '{task_description}' сохранен. Статус: {'успешно' if success else 'неудачно'}"

    def _update_indexes(self, task_record: Dict[str, Any]) -> None:
        """Обновление индексов при добавлении новой задачи"""
        if not self.enable_indexing:
            return

        task_id = task_record.get("task_id", "")
        description = normalize_unicode_text(task_record.get("description", ""))
        patterns = task_record.get("patterns", [])

        # Обновляем поисковый индекс
        words = set(description.split())
        for word in words:
            if word not in self._search_index:
                self._search_index[word] = set()
            self._search_index[word].add(task_id)

        # Обновляем индекс паттернов
        for pattern in patterns:
            if pattern not in self._pattern_index:
                self._pattern_index[pattern] = []
            if task_id not in self._pattern_index[pattern]:
                self._pattern_index[pattern].append(task_id)

    def _get_query_hash(self, query: str, limit: int = 5) -> str:
        """Генерация хэша для ключа кэша запросов"""
        key_data = f"find_similar:{query}:{limit}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()

    def _get_cache_entry(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Получение записи из кэша с проверкой TTL"""
        if cache_key not in self._query_cache:
            self._cache_stats['misses'] += 1
            return None

        entry = self._query_cache[cache_key]
        cache_time = entry.get('timestamp', datetime.min)

        # Проверяем TTL
        if datetime.now() - cache_time >= timedelta(seconds=self.cache_ttl_seconds):
            # Кэш просрочен, удаляем
            del self._query_cache[cache_key]
            self._cache_stats['evictions'] += 1
            self._cache_stats['misses'] += 1
            return None

        self._cache_stats['hits'] += 1
        return entry

    def _set_cache_entry(self, cache_key: str, result: List[Dict[str, Any]]) -> None:
        """Сохранение записи в кэше"""
        # Проверяем лимит размера кэша
        if len(self._query_cache) >= self.cache_size:
            # Удаляем самую старую запись (простая стратегия LRU)
            oldest_key = min(self._query_cache.keys(),
                           key=lambda k: self._query_cache[k].get('timestamp', datetime.min))
            del self._query_cache[oldest_key]
            self._cache_stats['evictions'] += 1

        self._query_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        self._cache_stats['size'] = len(self._query_cache)

    def _clear_query_cache(self) -> None:
        """Очистка кэша запросов"""
        self._query_cache.clear()
        self._cache_stats = {'hits': 0, 'misses': 0, 'evictions': 0, 'size': 0}

        # Сохраняем пустой кэш на диск если включена персистентность
        if self.enable_cache_persistence:
            self._save_persistent_cache()

    def _load_persistent_cache(self) -> None:
        """Загрузка персистентного кэша с диска"""
        cache_file_path = self.experience_dir / self.cache_file
        if not cache_file_path.exists():
            return

        try:
            with open(cache_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Восстанавливаем кэш с проверкой TTL
            current_time = datetime.now()
            valid_entries = {}

            for key, entry in cache_data.get('query_cache', {}).items():
                entry_time = datetime.fromisoformat(entry.get('timestamp', ''))
                if current_time - entry_time < timedelta(seconds=self.cache_ttl_seconds):
                    valid_entries[key] = {
                        'result': entry.get('result', []),
                        'timestamp': entry_time
                    }

            self._query_cache = valid_entries
            self._cache_stats['size'] = len(self._query_cache)

            logger.debug(f"Loaded {len(self._query_cache)} valid cache entries from disk")

        except Exception as e:
            logger.warning(f"Failed to load persistent cache: {e}")

    def _save_persistent_cache(self) -> None:
        """Сохранение персистентного кэша на диск"""
        if not self.enable_cache_persistence:
            return

        try:
            cache_file_path = self.experience_dir / self.cache_file
            cache_data = {
                'query_cache': self._query_cache,
                'stats': self._cache_stats,
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'cache_size': self.cache_size,
                    'ttl_seconds': self.cache_ttl_seconds
                }
            }

            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False, default=str)

            logger.debug(f"Saved {len(self._query_cache)} cache entries to disk")

        except Exception as e:
            logger.error(f"Failed to save persistent cache: {e}")

    def _find_similar_tasks_uncached(self, query_normalized: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Не кешированная версия поиска похожих задач"""
        data = self._load_experience()

        if self.enable_indexing and self._search_index:
            # Используем индекс для быстрого поиска
            query_words = set(query_normalized.split())
            candidate_task_ids = set()

            # Находим все задачи, содержащие хотя бы одно слово из запроса
            for word in query_words:
                if word in self._search_index:
                    candidate_task_ids.update(self._search_index[word])

            # Фильтруем задачи по точному совпадению запроса
            similar_tasks = []
            for task in data["tasks"]:
                if task.get("task_id") in candidate_task_ids:
                    description_normalized = normalize_unicode_text(task["description"])
                    if query_normalized in description_normalized:
                        similar_tasks.append(task)
        else:
            # Fallback для случаев без индексации
            similar_tasks = []
            for task in data["tasks"]:
                description_normalized = normalize_unicode_text(task["description"])
                if query_normalized in description_normalized:
                    similar_tasks.append(task)

        # Ограничиваем количество результатов
        return similar_tasks[-limit:]

    def find_similar_tasks(self, query: str, limit: int = 5) -> str:
        """
        Поиск похожих задач в истории

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов

        Returns:
            Список похожих задач
        """
        query_normalized = normalize_unicode_text(query)
        cache_key = self._get_query_hash(query_normalized, limit)

        # Проверяем кэш
        cache_entry = self._get_cache_entry(cache_key)
        if cache_entry is not None:
            similar_tasks = cache_entry['result']
        else:
            # Выполняем поиск и кэшируем результат
            similar_tasks = self._find_similar_tasks_uncached(query_normalized, limit)
            self._set_cache_entry(cache_key, similar_tasks)

        if not similar_tasks:
            return f"Похожие задачи не найдены для запроса: '{query}'"

        result = f"Найдено {len(similar_tasks)} похожих задач:\n\n"
        for i, task in enumerate(similar_tasks, 1):
            result += f"{i}. **{task['description']}**\n"
            result += f"   Статус: {'✅ Успешно' if task['success'] else '❌ Неудачно'}\n"
            execution_time = task.get('execution_time')
            if execution_time is not None:
                result += f"   Время выполнения: {execution_time:.1f} сек\n"
            if task.get('notes'):
                result += f"   Заметки: {task['notes']}\n"
            result += "\n"

        return result

    def get_recommendations(self, current_task: str) -> str:
        """
        Получение рекомендаций на основе предыдущего опыта

        Args:
            current_task: Описание текущей задачи

        Returns:
            Рекомендации по выполнению
        """
        data = self._load_experience()

        # Ищем похожие успешные задачи с улучшенной Unicode обработкой
        current_task_normalized = normalize_unicode_text(current_task)
        current_task_words = set(current_task_normalized.split())
        successful_similar = []
        for task in data["tasks"]:
            if task["success"]:
                description_normalized = normalize_unicode_text(task["description"])
                description_words = set(description_normalized.split())
                # Проверяем, что все слова текущей задачи есть в описании похожей задачи
                if current_task_words.issubset(description_words):
                    successful_similar.append(task)

        if not successful_similar:
            return f"Рекомендации для задачи '{current_task}': Данные о похожих задачах отсутствуют. Рекомендуется следовать стандартным практикам разработки."

        # Анализируем успешные задачи
        recommendations = f"Рекомендации для задачи '{current_task}' на основе {len(successful_similar)} успешных похожих задач:\n\n"

        # Среднее время выполнения
        avg_time = sum(task.get("execution_time", 0) for task in successful_similar) / len(successful_similar)
        if avg_time > 0:
            recommendations += f"• Ожидаемое время выполнения: ~{avg_time:.1f} секунд\n"

        # Общие паттерны
        all_patterns = []
        for task in successful_similar:
            all_patterns.extend(task.get("patterns", []))

        if all_patterns:
            from collections import Counter
            pattern_counts = Counter(all_patterns)
            top_patterns = pattern_counts.most_common(3)
            if top_patterns:
                recommendations += "• Рекомендуемые паттерны решения:\n"
                for pattern, count in top_patterns:
                    recommendations += f"  - {pattern} (использовался {count} раз)\n"

        # Заметки из успешных задач
        useful_notes = [task["notes"] for task in successful_similar if task.get("notes")]
        if useful_notes:
            recommendations += "• Полезные замечания из предыдущих выполнений:\n"
            for note in useful_notes[:3]:  # Ограничиваем до 3 заметок
                recommendations += f"  - {note}\n"

        return recommendations

    def get_statistics(self) -> str:
        """
        Получение статистики обучения

        Returns:
            Статистика использования инструмента
        """
        data = self._load_experience()
        stats = data.get("statistics", {})

        result = "📊 Статистика LearningTool:\n\n"
        result += f"• Всего задач: {stats.get('total_tasks', 0)}\n"
        result += f"• Успешных задач: {stats.get('successful_tasks', 0)}\n"
        result += f"• Неудачных задач: {stats.get('failed_tasks', 0)}\n"

        if stats.get('average_execution_time', 0) > 0:
            result += f"• Среднее время выполнения: {stats['average_execution_time']:.1f} сек\n"

        patterns_count = len(data.get("patterns", {}))
        result += f"• Изученных паттернов: {patterns_count}\n"

        if stats.get('total_tasks', 0) > 0:
            success_rate = (stats.get('successful_tasks', 0) / stats['total_tasks']) * 100
            result += f"• Процент успешности: {success_rate:.1f}%\n"

        return result

    def get_cache_stats(self) -> str:
        """
        Получение статистики кеширования

        Returns:
            Статистика использования кэша
        """
        # Статистика кэша поиска похожих задач
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = (self._cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        result = "📊 Статистика кеширования LearningTool:\n\n"
        result += "**Кэш поиска похожих задач:**\n"
        result += f"• Всего запросов: {total_requests}\n"
        result += f"• Попаданий в кэш: {self._cache_stats['hits']}\n"
        result += f"• Промахов кэша: {self._cache_stats['misses']}\n"
        result += f"• Выселений из кэша: {self._cache_stats['evictions']}\n"
        result += f"• Текущий размер кэша: {self._cache_stats['size']}/{self.cache_size}\n"
        result += f"• Процент попаданий: {hit_rate:.1f}%\n"
        result += f"• TTL кэша: {self.cache_ttl_seconds} сек\n"
        result += f"• Персистентность кэша: {'включена' if self.enable_cache_persistence else 'отключена'}\n"

        return result