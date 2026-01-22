"""
LearningTool - инструмент для обучения на предыдущих задачах
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from crewai.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


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
    experience_file: str = "experience.json"  # Будет переопределен в __init__

    def __init__(self, experience_dir: str = "smart_experience", max_experience_tasks: int = 1000, **kwargs):
        """
        Инициализация LearningTool

        Args:
            experience_dir: Директория для хранения опыта
            max_experience_tasks: Максимальное количество задач в опыте
        """
        super().__init__(**kwargs)
        self.experience_dir = Path(experience_dir)
        self.max_experience_tasks = max_experience_tasks
        self.experience_file = self.experience_dir / "experience.json"

        # Создаем директорию опыта если не существует
        self.experience_dir.mkdir(parents=True, exist_ok=True)

        # Инициализируем файл опыта если не существует
        if not self.experience_file.exists():
            self._init_experience_file()

    def _init_experience_file(self):
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

    def _load_experience(self) -> Dict[str, Any]:
        """Загрузка данных опыта"""
        try:
            with open(self.experience_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load experience: {e}")
            return {"version": "1.0", "tasks": [], "patterns": {}, "statistics": {}}

    def _save_experience(self, data: Dict[str, Any]):
        """Сохранение данных опыта"""
        try:
            with open(self.experience_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save experience: {e}")

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
            logger.error(f"Error in LearningTool._run: {e}")
            return f"Error: {str(e)}"

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
        data = self._load_experience()

        # Создаем запись о задаче
        task_record = {
            "task_id": task_id,
            "description": task_description,
            "success": success,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
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

        return f"Опыт задачи '{task_description}' сохранен. Статус: {'успешно' if success else 'неудачно'}"

    def find_similar_tasks(self, query: str, limit: int = 5) -> str:
        """
        Поиск похожих задач в истории

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов

        Returns:
            Список похожих задач
        """
        data = self._load_experience()
        query_lower = query.lower()

        similar_tasks = []
        for task in data["tasks"]:
            description_lower = task["description"].lower()
            if query_lower in description_lower:
                similar_tasks.append(task)

        # Ограничиваем количество результатов
        similar_tasks = similar_tasks[-limit:]

        if not similar_tasks:
            return f"Похожие задачи не найдены для запроса: '{query}'"

        result = f"Найдено {len(similar_tasks)} похожих задач:\n\n"
        for i, task in enumerate(similar_tasks, 1):
            result += f"{i}. **{task['description']}**\n"
            result += f"   Статус: {'✅ Успешно' if task['success'] else '❌ Неудачно'}\n"
            if task.get('execution_time'):
                result += f"   Время выполнения: {task['execution_time']:.1f} сек\n"
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

        # Ищем похожие успешные задачи
        successful_similar = [
            task for task in data["tasks"]
            if task["success"] and current_task.lower() in task["description"].lower()
        ]

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