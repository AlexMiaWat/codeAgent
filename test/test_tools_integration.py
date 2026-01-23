"""
Интеграционные тесты для LearningTool и ContextAnalyzerTool
"""

import tempfile
import time
from pathlib import Path


class TestLearningToolContextAnalyzerIntegration:
    """Интеграционные тесты LearningTool + ContextAnalyzerTool"""

    def test_tools_shared_project_context(self):
        """Тест совместного использования контекста проекта"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем инструменты для одного проекта
            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Создаем тестовую структуру проекта
            self._create_test_project_structure(project_dir)

            # ContextAnalyzerTool анализирует структуру
            structure_analysis = context_tool.analyze_project_structure()
            assert "api.py" in structure_analysis or "docs" in structure_analysis

            # LearningTool сохраняет опыт анализа
            learning_tool.save_task_experience(
                task_id="structure_analysis",
                task_description="Анализ структуры проекта с API модулями",
                success=True,
                execution_time=0.8,
                patterns=["analysis", "api", "structure"]
            )

            # ContextAnalyzerTool находит зависимости файла
            deps = context_tool.find_file_dependencies("src/api.py")
            assert isinstance(deps, str)

            # LearningTool сохраняет опыт поиска зависимостей
            learning_tool.save_task_experience(
                task_id="dependency_analysis",
                task_description="Поиск зависимостей API модуля",
                success=True,
                execution_time=0.3,
                patterns=["dependencies", "api"]
            )

            # Проверяем накопленную статистику
            stats = learning_tool.get_statistics()
            assert "Всего задач: 2" in stats
            assert "Успешных задач: 2" in stats

    def test_tools_task_context_workflow(self):
        """Тест рабочего процесса получения контекста задачи"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Создаем проект с задачами тестирования
            self._create_test_project_with_tasks(project_dir)

            # 1. Получаем контекст для задачи тестирования
            task_context = context_tool.get_task_context("написать тесты для API")
            assert "📋 Контекст для задачи" in task_context

            # 2. Сохраняем опыт получения контекста
            learning_tool.save_task_experience(
                task_id="context_retrieval",
                task_description="Получение контекста для написания тестов API",
                success=True,
                patterns=["context", "testing", "api"]
            )

            # 3. Ищем связанные файлы
            related_files = context_tool.find_related_files("test")
            assert "📁 Файлы, связанные с запросом" in related_files

            # 4. Сохраняем опыт поиска
            learning_tool.save_task_experience(
                task_id="file_search",
                task_description="Поиск файлов связанных с тестированием",
                success=True,
                patterns=["search", "files", "testing"]
            )

            # 5. Получаем рекомендации для похожей задачи
            recommendations = learning_tool.get_recommendations("написать интеграционные тесты")
            assert "Рекомендации" in recommendations

    def test_tools_error_handling_integration(self):
        """Тест совместной обработки ошибок"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # 1. Попытка анализа несуществующего файла
            result1 = context_tool.find_file_dependencies("nonexistent.py")
            assert "не найден" in result1 or "not found" in result1

            # 2. Сохраняем опыт неудачного поиска
            learning_tool.save_task_experience(
                task_id="failed_dependency_search",
                task_description="Неудачный поиск зависимостей несуществующего файла",
                success=False,
                notes="Файл не найден в проекте"
            )

            # 3. Попытка анализа несуществующего компонента
            result2 = context_tool.analyze_component("nonexistent_component")
            assert "не найден" in result2 or "not found" in result2

            # 4. Сохраняем опыт неудачного анализа
            learning_tool.save_task_experience(
                task_id="failed_component_analysis",
                task_description="Неудачный анализ несуществующего компонента",
                success=False,
                notes="Компонент не найден"
            )

            # 5. Проверяем статистику ошибок
            stats = learning_tool.get_statistics()
            assert "Всего задач: 2" in stats
            assert "Неудачных задач: 2" in stats

            # 6. Тем не менее инструменты продолжают работать
            # Создаем существующий файл
            (project_dir / "existing.py").write_text("# Existing file")

            result3 = context_tool.analyze_component("existing.py")
            assert "existing.py" in result3

            # 7. Сохраняем успешный опыт
            learning_tool.save_task_experience(
                task_id="successful_recovery",
                task_description="Успешный анализ после предыдущих ошибок",
                success=True
            )

            final_stats = learning_tool.get_statistics()
            assert "Всего задач: 3" in final_stats
            assert "Успешных задач: 1" in final_stats

    def test_tools_performance_integration(self):
        """Тест производительности совместной работы инструментов"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Создаем большой проект для тестирования производительности
            self._create_large_test_project(project_dir)

            # Замеряем время анализа структуры
            start_time = time.time()
            structure_result = context_tool.analyze_project_structure()
            structure_time = time.time() - start_time

            assert structure_time < 5.0  # Должен выполниться за разумное время
            assert "Основные компоненты" in structure_result

            # Сохраняем опыт с замером времени
            learning_tool.save_task_experience(
                task_id="performance_test",
                task_description="Анализ структуры большого проекта",
                success=True,
                execution_time=structure_time,
                patterns=["performance", "large_project"]
            )

            # Проверяем что время сохранено корректно
            data = learning_tool._load_experience()
            saved_task = data['tasks'][0]
            assert abs(saved_task['execution_time'] - structure_time) < 0.01

    def test_tools_data_consistency(self):
        """Тест一致ности данных между инструментами"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Создаем файл с известным содержимым
            test_file = project_dir / "consistent_test.py"
            test_content = '''
"""Test module for consistency checking"""

import os
import sys
from pathlib import Path

class TestClass:
    """A test class"""

    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value

def test_function(param1, param2="default"):
    """Test function with parameters"""
    return param1 + param2
'''
            test_file.write_text(test_content)

            # ContextAnalyzerTool анализирует файл
            analysis = context_tool.analyze_component("consistent_test.py")
            assert "consistent_test.py" in analysis
            assert "Тип:" in analysis and "file" in analysis

            # LearningTool сохраняет опыт анализа этого файла
            learning_tool.save_task_experience(
                task_id="consistency_test",
                task_description="Анализ consistent_test.py",
                success=True,
                patterns=["consistency", "test"]
            )

            # Проверяем что оба инструмента ссылаются на один и тот же файл
            # ContextAnalyzerTool должен найти файл
            find_result = context_tool.find_related_files("TestClass")
            assert "consistent_test.py" in find_result

            # LearningTool должен показать задачу анализа
            similar = learning_tool.find_similar_tasks("consistent")
            assert "consistent_test.py" in similar

    def _create_test_project_structure(self, project_dir: Path):
        """Создание тестовой структуры проекта"""
        # Директории
        src_dir = project_dir / "src"
        src_dir.mkdir()

        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        # Файлы
        (src_dir / "__init__.py").write_text("")
        (src_dir / "api.py").write_text("""
# API module
from .utils import validate_input

def get_user(user_id):
    if validate_input(user_id):
        return {"id": user_id, "name": "User"}
    return None
""")

        (src_dir / "utils.py").write_text("""
# Utility functions
def validate_input(value):
    return isinstance(value, (int, str)) and len(str(value)) > 0
""")

        (docs_dir / "api.md").write_text("""
# API Documentation

## Functions
- get_user(user_id): Get user by ID
""")

    def _create_test_project_with_tasks(self, project_dir: Path):
        """Создание проекта с задачами для тестирования"""
        # Директории
        src_dir = project_dir / "src"
        src_dir.mkdir()

        test_dir = project_dir / "test"
        test_dir.mkdir()

        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        # Исходный код
        (src_dir / "api.py").write_text("""
# API module
def create_user(name, email):
    return {"name": name, "email": email}

def get_user(user_id):
    return {"id": user_id}
""")

        # Тесты
        (test_dir / "test_api.py").write_text("""
# API tests
import pytest
from src.api import create_user, get_user

def test_create_user():
    user = create_user("Test", "test@example.com")
    assert user["name"] == "Test"

def test_get_user():
    user = get_user(1)
    assert user["id"] == 1
""")

        # Документация
        (docs_dir / "testing.md").write_text("""
# Testing Guide

## Writing Tests
1. Create test files in test/ directory
2. Use pytest framework
3. Follow naming convention: test_*.py
""")

    def _create_large_test_project(self, project_dir: Path):
        """Создание большого проекта для тестирования производительности"""
        # Создаем много директорий и файлов
        for i in range(10):
            dir_name = f"module_{i}"
            module_dir = project_dir / dir_name
            module_dir.mkdir()

            # Создаем файлы в каждой директории
            for j in range(5):
                file_name = f"file_{j}.py"
                file_path = module_dir / file_name

                # Создаем файл с некоторым содержимым
                content = f"""
# {dir_name}/{file_name}
def function_{j}():
    return {j}

class Class{j}:
    pass
"""
                file_path.write_text(content)

        # Создаем документацию
        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        for i in range(20):
            doc_file = docs_dir / f"doc_{i}.md"
            doc_file.write_text(f"# Documentation {i}\n\nThis is doc {i}.")


class TestToolsPatternRecognition:
    """Тесты распознавания паттернов в совместной работе инструментов"""

    def test_learning_patterns_from_context(self):
        """Тест обучения на паттернах из контекста"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Создаем проект с различными типами задач
            self._create_pattern_project(project_dir)

            # Анализируем различные компоненты и сохраняем паттерны
            patterns_data = [
                ("src/api.py", ["api", "rest", "endpoints"]),
                ("src/database.py", ["database", "sql", "models"]),
                ("src/auth.py", ["authentication", "security", "jwt"]),
                ("test/test_api.py", ["testing", "unit_tests", "api"]),
                ("docs/api.md", ["documentation", "api_docs"])
            ]

            for file_path, patterns in patterns_data:
                # Анализируем компонент
                analysis = context_tool.analyze_component(file_path)
                assert file_path in analysis

                # Сохраняем опыт с паттернами
                learning_tool.save_task_experience(
                    task_id=f"analyze_{file_path.replace('/', '_').replace('.', '_')}",
                    task_description=f"Анализ {file_path}",
                    success=True,
                    patterns=patterns
                )

            # Проверяем распознавание паттернов
            api_recommendations = learning_tool.get_recommendations("разработать новый API endpoint")
            assert "Рекомендации" in api_recommendations

            # Ищем задачи по паттернам
            learning_tool.find_similar_tasks("api")
            assert len([t for t in learning_tool._load_experience()['tasks'] if 'api' in t.get('patterns', [])]) > 0

    def test_context_driven_learning(self):
        """Тест обучения на основе контекстного анализа"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Создаем задачу разработки
            task_desc = "добавить функцию поиска пользователей по email"

            # Получаем контекст для задачи
            context = context_tool.get_task_context(task_desc)
            assert "📋 Контекст" in context

            # Ищем связанные файлы
            related = context_tool.find_related_files("user")
            assert "Файлы" in related

            # Сохраняем опыт выполнения задачи
            learning_tool.save_task_experience(
                task_id="implement_user_search",
                task_description=task_desc,
                success=True,
                execution_time=2.5,
                patterns=["search", "users", "email", "database"]
            )

            # Проверяем что можем найти похожие задачи
            similar = learning_tool.find_similar_tasks("пользователей")
            # Проверяем что поиск вернул результаты (не "Похожие задачи не найдены")
            assert "найдено" in similar.lower() or "похожих задач" in similar.lower()
            # Проверяем что в результате есть информация о задаче
            assert "добавить функцию поиска пользователей" in similar.lower()

            # Получаем рекомендации для похожей задачи
            recommendations = learning_tool.get_recommendations("добавить функцию поиска по имени")
            assert "Рекомендации" in recommendations

    def _create_pattern_project(self, project_dir: Path):
        """Создание проекта с различными паттернами разработки"""
        # API модуль
        api_file = project_dir / "src" / "api.py"
        api_file.parent.mkdir(parents=True, exist_ok=True)
        api_file.write_text("""
# REST API endpoints
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/users', methods=['GET'])
def get_users():
    return jsonify({"users": []})

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    return jsonify({"id": user_id})
""")

        # Database модуль
        db_file = project_dir / "src" / "database.py"
        db_file.write_text("""
# Database models and connections
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)

engine = create_engine('sqlite:///test.db')
""")

        # Auth модуль
        auth_file = project_dir / "src" / "auth.py"
        auth_file.write_text("""
# Authentication and security
import jwt
import datetime

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, 'secret', algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
""")

        # Тесты
        test_file = project_dir / "test" / "test_api.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("""
# Unit tests for API
import pytest
from src.api import app

def test_get_users():
    with app.test_client() as client:
        response = client.get('/users')
        assert response.status_code == 200

def test_get_user():
    with app.test_client() as client:
        response = client.get('/users/1')
        assert response.status_code == 200
""")

        # Документация
        docs_dir = project_dir / "docs"
        docs_dir.mkdir(exist_ok=True)
        api_doc = docs_dir / "api.md"
        api_doc.write_text("""
# API Documentation

## Endpoints

### GET /users
Get all users

### GET /users/{id}
Get user by ID

## Authentication
Use JWT tokens for authenticated requests
""")


class TestToolsDataPersistenceIntegration:
    """Тесты персистентности данных в совместной работе"""

    def test_experience_persistence_across_sessions(self):
        """Тест сохранения опыта между сессиями"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            experience_dir = str(project_dir / "experience")

            # Первая сессия
            learning_tool1 = LearningTool(experience_dir=experience_dir)
            context_tool1 = ContextAnalyzerTool(project_dir=str(project_dir))

            # Создаем файл для анализа
            test_file = project_dir / "persistent_test.py"
            test_file.write_text("# Persistent test file\ndef test(): pass")

            # Анализируем и сохраняем опыт
            analysis1 = context_tool1.analyze_component("persistent_test.py")
            assert "persistent_test.py" in analysis1

            learning_tool1.save_task_experience(
                task_id="session1_task",
                task_description="Task from first session",
                success=True,
                patterns=["persistence", "session1"]
            )

            # Проверяем что данные сохранены
            data1 = learning_tool1._load_experience()
            assert len(data1['tasks']) == 1

            # Вторая сессия (новые экземпляры инструментов)
            learning_tool2 = LearningTool(experience_dir=experience_dir)
            context_tool2 = ContextAnalyzerTool(project_dir=str(project_dir))

            # Проверяем что опыт из первой сессии доступен
            data2 = learning_tool2._load_experience()
            assert len(data2['tasks']) == 1
            assert data2['tasks'][0]['task_id'] == "session1_task"

            # Анализируем тот же файл второй раз
            analysis2 = context_tool2.analyze_component("persistent_test.py")
            assert "persistent_test.py" in analysis2

            # Добавляем опыт из второй сессии
            learning_tool2.save_task_experience(
                task_id="session2_task",
                task_description="Task from second session",
                success=True,
                patterns=["persistence", "session2"]
            )

            # Проверяем что оба опыта сохранены
            final_data = learning_tool2._load_experience()
            assert len(final_data['tasks']) == 2
            task_ids = [t['task_id'] for t in final_data['tasks']]
            assert "session1_task" in task_ids
            assert "session2_task" in task_ids

    def test_shared_experience_between_tools(self):
        """Тест общего опыта между несколькими инструментами"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            experience_dir = str(Path(tmp_dir) / "shared_experience")

            # Создаем несколько LearningTool с общей директорией опыта
            tool1 = LearningTool(experience_dir=experience_dir)
            tool2 = LearningTool(experience_dir=experience_dir)
            tool3 = LearningTool(experience_dir=experience_dir)

            # Каждый инструмент добавляет свой опыт
            tool1.save_task_experience("tool1_task", "Task from tool 1", True, patterns=["tool1"])
            tool2.save_task_experience("tool2_task", "Task from tool 2", True, patterns=["tool2"])
            tool3.save_task_experience("tool3_task", "Task from tool 3", True, patterns=["tool3"])

            # Все инструменты должны видеть общий опыт
            for tool in [tool1, tool2, tool3]:
                data = tool._load_experience()
                assert len(data['tasks']) == 3
                task_ids = [t['task_id'] for t in data['tasks']]
                assert "tool1_task" in task_ids
                assert "tool2_task" in task_ids
                assert "tool3_task" in task_ids

                stats = tool.get_statistics()
                assert "Всего задач: 3" in stats
                assert "Успешных задач: 3" in stats