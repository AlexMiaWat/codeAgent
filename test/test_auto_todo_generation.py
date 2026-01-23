"""
Тесты для автоматической генерации TODO листов
"""

import pytest
import json
from src.session_tracker import SessionTracker
from src.config_loader import ConfigLoader


class TestSessionTracker:
    """Тесты для SessionTracker"""
    
    def test_session_tracker_initialization(self, tmp_path):
        """Тест инициализации трекера сессий"""
        tracker = SessionTracker(tmp_path, ".test_sessions.json")
        
        assert tracker.project_dir == tmp_path
        assert tracker.current_session_id is not None
        assert len(tracker.current_session_id) > 0
        
    def test_session_id_format(self, tmp_path):
        """Тест формата ID сессии"""
        tracker = SessionTracker(tmp_path, ".test_sessions.json")
        
        # Формат: YYYYMMDD_HHMMSS
        session_id = tracker.current_session_id
        assert len(session_id) == 15  # 8 цифр даты + _ + 6 цифр времени
        assert '_' in session_id
        
    def test_can_generate_todo_initial(self, tmp_path):
        """Тест проверки возможности генерации (начальное состояние)"""
        tracker = SessionTracker(tmp_path, ".test_sessions.json")
        
        # Изначально должно быть разрешено
        assert tracker.can_generate_todo(max_generations=5) is True
        assert tracker.get_current_session_generation_count() == 0
        
    def test_record_generation(self, tmp_path):
        """Тест записи информации о генерации"""
        tracker = SessionTracker(tmp_path, ".test_sessions.json")
        
        # Записываем генерацию
        result = tracker.record_generation(
            todo_file="todo/GENERATED_20260118_123456.md",
            task_count=7,
            metadata={"test": "data"}
        )
        
        assert result is not None
        assert result["session_id"] == tracker.current_session_id
        assert result["task_count"] == 7
        assert result["metadata"]["test"] == "data"
        
        # Проверяем, что счетчик увеличился
        assert tracker.get_current_session_generation_count() == 1
        
    def test_max_generations_limit(self, tmp_path):
        """Тест ограничения максимального количества генераций"""
        tracker = SessionTracker(tmp_path, ".test_sessions.json")
        max_gen = 3
        
        # Генерируем максимальное количество раз
        for i in range(max_gen):
            assert tracker.can_generate_todo(max_generations=max_gen) is True
            tracker.record_generation(
                todo_file=f"todo/GENERATED_{i}.md",
                task_count=5
            )
        
        # Проверяем, что достигнут лимит
        assert tracker.can_generate_todo(max_generations=max_gen) is False
        assert tracker.get_current_session_generation_count() == max_gen
        
    def test_session_persistence(self, tmp_path):
        """Тест сохранения данных сессии в файл"""
        tracker_file = ".test_sessions.json"
        
        # Создаем трекер и записываем генерацию
        tracker1 = SessionTracker(tmp_path, tracker_file)
        tracker1.record_generation("todo/test.md", 5)
        
        # Создаем новый трекер с тем же файлом
        tracker2 = SessionTracker(tmp_path, tracker_file)
        
        # Проверяем, что данные сохранились
        stats = tracker2.get_session_statistics()
        assert stats["total_generations_all_time"] >= 1
        
        # Проверяем, что файл существует
        tracker_path = tmp_path / tracker_file
        assert tracker_path.exists()
        
        # Проверяем содержимое файла
        with open(tracker_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert "sessions" in data
            assert "total_generations" in data
            assert data["total_generations"] >= 1
    
    def test_session_statistics(self, tmp_path):
        """Тест получения статистики по сессии"""
        tracker = SessionTracker(tmp_path, ".test_sessions.json")
        
        # Записываем несколько генераций
        tracker.record_generation("todo/gen1.md", 5)
        tracker.record_generation("todo/gen2.md", 7)
        
        stats = tracker.get_session_statistics()
        
        assert stats["session_id"] == tracker.current_session_id
        assert stats["generation_count"] == 2
        assert stats["total_generations_all_time"] == 2
        assert stats["last_generation_date"] is not None
        
    def test_reset_session_counter(self, tmp_path):
        """Тест сброса счетчика сессии"""
        tracker = SessionTracker(tmp_path, ".test_sessions.json")
        
        # Записываем генерации
        tracker.record_generation("todo/gen1.md", 5)
        tracker.record_generation("todo/gen2.md", 7)
        assert tracker.get_current_session_generation_count() == 2
        
        # Сбрасываем счетчик
        tracker.reset_session_counter()
        assert tracker.get_current_session_generation_count() == 0


class TestAutoTodoConfiguration:
    """Тесты конфигурации автоматической генерации TODO"""
    
    def test_auto_todo_config_loading(self):
        """Тест загрузки конфигурации автоматической генерации"""
        config = ConfigLoader("config/config.yaml")
        
        # Проверяем наличие настроек
        server_config = config.get('server', {})
        auto_todo_config = server_config.get('auto_todo_generation', {})
        
        assert 'enabled' in auto_todo_config
        assert 'max_generations_per_session' in auto_todo_config
        assert 'output_dir' in auto_todo_config
        assert 'session_tracker_file' in auto_todo_config
        
    def test_empty_todo_instructions_exist(self):
        """Тест наличия инструкций для empty_todo сценария"""
        config = ConfigLoader("config/config.yaml")
        
        instructions = config.get('instructions', {})
        assert 'empty_todo' in instructions
        
        empty_todo_instructions = instructions['empty_todo']
        assert len(empty_todo_instructions) >= 4  # Минимум 4 инструкции
        
        # Проверяем наличие ключевых полей в инструкциях
        for instruction in empty_todo_instructions:
            assert 'instruction_id' in instruction
            assert 'name' in instruction
            assert 'template' in instruction
            assert 'wait_for_file' in instruction
            assert 'control_phrase' in instruction
            
    def test_instruction_templates_have_placeholders(self):
        """Тест наличия плейсхолдеров в шаблонах инструкций"""
        config = ConfigLoader("config/config.yaml")
        
        instructions = config.get('instructions', {})
        empty_todo_instructions = instructions.get('empty_todo', [])
        
        # Проверяем первую инструкцию
        if empty_todo_instructions:
            instruction_1 = empty_todo_instructions[0]
            template = instruction_1.get('template', '')
            
            # Должны быть плейсхолдеры
            assert '{date}' in template or '{session_id}' in template
            
            wait_for_file = instruction_1.get('wait_for_file', '')
            assert '{session_id}' in wait_for_file


class TestAutoTodoIntegration:
    """Интеграционные тесты автоматической генерации TODO"""
    
    @pytest.mark.integration
    def test_empty_todo_detection(self, tmp_path):
        """Тест определения пустого TODO листа"""
        from src.todo_manager import TodoManager
        
        # Создаем пустой TODO файл
        todo_file = tmp_path / "todo.md"
        todo_file.write_text("# TODO\n\n", encoding='utf-8')
        
        manager = TodoManager(tmp_path, todo_format='md')
        pending_tasks = manager.get_pending_tasks()
        
        assert len(pending_tasks) == 0
        
    @pytest.mark.integration
    def test_session_tracker_in_server_context(self, tmp_path):
        """Тест работы трекера сессий в контексте сервера"""
        # Создаем минимальную конфигурацию
        config_content = """
project:
  base_dir: {tmp_path}
  docs_dir: docs
  status_file: status.md
  todo_format: md

server:
  check_interval: 60
  max_iterations: 1
  task_delay: 0
  auto_todo_generation:
    enabled: true
    max_generations_per_session: 5
    output_dir: "todo"
    session_tracker_file: ".test_sessions.json"
""".replace('{tmp_path}', str(tmp_path))
        
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content, encoding='utf-8')
        
        # Создаем трекер
        tracker = SessionTracker(tmp_path, ".test_sessions.json")
        
        # Проверяем, что трекер работает
        assert tracker.can_generate_todo(5) is True
        
        # Записываем генерацию
        tracker.record_generation("todo/test.md", 5)
        
        # Проверяем статистику
        stats = tracker.get_session_statistics()
        assert stats["generation_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
