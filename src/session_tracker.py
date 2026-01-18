"""
Модуль отслеживания сессий генерации TODO листов
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionTracker:
    """Отслеживание сессий генерации TODO листов"""
    
    def __init__(self, project_dir: Path, tracker_file: str = ".codeagent_sessions.json"):
        """
        Инициализация трекера сессий
        
        Args:
            project_dir: Директория проекта
            tracker_file: Имя файла для хранения данных о сессиях
        """
        self.project_dir = Path(project_dir)
        self.tracker_file = self.project_dir / tracker_file
        self.session_data = self._load_session_data()
        
        # ID текущей сессии сервера
        self.current_session_id = self._generate_session_id()
        
        logger.info(f"Session Tracker инициализирован. Сессия: {self.current_session_id}")
    
    def _generate_session_id(self) -> str:
        """
        Генерация уникального ID сессии
        
        Returns:
            ID сессии в формате YYYYMMDD_HHMMSS
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _load_session_data(self) -> Dict[str, Any]:
        """
        Загрузка данных о сессиях из файла
        
        Returns:
            Словарь с данными о сессиях
        """
        default_data: Dict[str, Any] = {
            "sessions": [],
            "total_generations": 0,
            "last_generation_date": None
        }
        
        if not self.tracker_file.exists():
            return default_data
        
        try:
            with open(self.tracker_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else default_data
        except Exception as e:
            logger.warning(f"Ошибка загрузки данных сессий: {e}")
            return default_data
    
    def _save_session_data(self):
        """Сохранение данных о сессиях в файл"""
        try:
            with open(self.tracker_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных сессий: {e}")
    
    def get_current_session_generation_count(self) -> int:
        """
        Получить количество генераций в текущей сессии
        
        Returns:
            Количество генераций TODO в текущей сессии
        """
        # Ищем текущую сессию в списке
        sessions = self.session_data.get("sessions", [])
        if not isinstance(sessions, list):
            return 0
            
        for session in sessions:
            if isinstance(session, dict) and session.get("session_id") == self.current_session_id:
                count = session.get("generation_count", 0)
                return int(count) if isinstance(count, (int, float)) else 0
        
        return 0
    
    def can_generate_todo(self, max_generations: int = 5) -> bool:
        """
        Проверка, можно ли генерировать новый TODO лист
        
        Args:
            max_generations: Максимальное количество генераций за сессию
        
        Returns:
            True если можно генерировать, False иначе
        """
        current_count = self.get_current_session_generation_count()
        can_generate = current_count < max_generations
        
        if not can_generate:
            logger.warning(
                f"Достигнут лимит генераций TODO для сессии {self.current_session_id}: "
                f"{current_count}/{max_generations}"
            )
        
        return can_generate
    
    def record_generation(self, todo_file: str, task_count: int, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Записать информацию о новой генерации TODO
        
        Args:
            todo_file: Путь к сгенерированному файлу TODO
            task_count: Количество задач в TODO
            metadata: Дополнительные метаданные
        
        Returns:
            Словарь с информацией о генерации
        """
        generation_info = {
            "session_id": self.current_session_id,
            "timestamp": datetime.now().isoformat(),
            "todo_file": str(todo_file),
            "task_count": task_count,
            "metadata": metadata or {}
        }
        
        # Обновляем данные текущей сессии
        session_found = False
        for session in self.session_data.get("sessions", []):
            if session.get("session_id") == self.current_session_id:
                session["generation_count"] = session.get("generation_count", 0) + 1
                session["generations"] = session.get("generations", [])
                session["generations"].append(generation_info)
                session_found = True
                break
        
        # Если сессия не найдена, создаем новую
        if not session_found:
            new_session = {
                "session_id": self.current_session_id,
                "start_time": datetime.now().isoformat(),
                "generation_count": 1,
                "generations": [generation_info]
            }
            if "sessions" not in self.session_data:
                self.session_data["sessions"] = []
            self.session_data["sessions"].append(new_session)
        
        # Обновляем общую статистику
        self.session_data["total_generations"] = self.session_data.get("total_generations", 0) + 1
        self.session_data["last_generation_date"] = datetime.now().isoformat()
        
        # Сохраняем данные
        self._save_session_data()
        
        logger.info(
            f"Записана генерация TODO: сессия={self.current_session_id}, "
            f"файл={todo_file}, задач={task_count}"
        )
        
        return generation_info
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Получить статистику по текущей сессии
        
        Returns:
            Словарь со статистикой
        """
        current_count = self.get_current_session_generation_count()
        
        # Ищем текущую сессию
        current_session = None
        for session in self.session_data.get("sessions", []):
            if session.get("session_id") == self.current_session_id:
                current_session = session
                break
        
        return {
            "session_id": self.current_session_id,
            "generation_count": current_count,
            "total_generations_all_time": self.session_data.get("total_generations", 0),
            "last_generation_date": self.session_data.get("last_generation_date"),
            "current_session_data": current_session
        }
    
    def reset_session_counter(self):
        """Сброс счетчика генераций для текущей сессии (для тестирования)"""
        for session in self.session_data.get("sessions", []):
            if session.get("session_id") == self.current_session_id:
                session["generation_count"] = 0
                session["generations"] = []
                break
        
        self._save_session_data()
        logger.info(f"Счетчик генераций сброшен для сессии {self.current_session_id}")
