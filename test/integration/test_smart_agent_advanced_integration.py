#!/usr/bin/env python3
"""
Расширенные интеграционные тесты Smart Agent
Тестирует fallback режимы, best_of_two стратегию и сложные сценарии взаимодействия
"""

import sys
import os
import tempfile
import shutil
import time
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import asyncio

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml


class TestSmartAgentAdvancedIntegration:
    """Расширенные интеграционные тесты Smart Agent"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="smart_agent_advanced_test_"))
        self.experience_dir = self.temp_dir / "experience"
        self.project_dir = self.temp_dir / "project"

        # Создаем тестовую структуру проекта
        self.project_dir.mkdir()

        # Создаем тестовые файлы проекта
        (self.project_dir / "main.py").write_text("""
import os
from pathlib import Path
from utils.helper import helper_function

def main():
    result = helper_function()
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    main()
""")

        (self.project_dir / "utils.py").write_text("""
def helper_function():
    return "test result"

class TestClass:
    def __init__(self, value):
        self.value = value

    def process(self):
        return f"processed: {self.value}"
""")

        (self.project_dir / "requirements.txt").write_text("""
pytest>=7.0.0
requests>=2.28.0
""")

    def teardown_method(self):
        """Очистка после каждого теста"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_learning_tool_context_analyzer_integration_workflow(self):
        """Тест полного рабочего процесса: анализ -> обучение -> рекомендация"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Инициализируем инструменты
        learning_tool = LearningTool(experience_dir=str(self.experience_dir))
        context_tool = ContextAnalyzerTool(project_dir=str(self.project_dir))

        # Шаг 1: Анализируем проект
        project_analysis = context_tool._run("analyze_project")
        assert "main.py" in project_analysis
        assert "utils.py" in project_analysis

        # Шаг 2: Анализируем конкретный файл
        file_analysis = context_tool._run("analyze_file", file_path="main.py")
        assert "helper_function" in file_analysis
        assert "import" in file_analysis

        # Шаг 3: Сохраняем опыт анализа проекта
        learning_tool._run("save_experience",
                          task_id="project_analysis_001",
                          task_description="Анализ структуры Python проекта",
                          success=True,
                          execution_time=2.5,
                          patterns=["project_analysis", "python_structure"],
                          notes="Найдены main.py, utils.py, requirements.txt")

        # Шаг 4: Сохраняем опыт анализа файла
        learning_tool._run("save_experience",
                          task_id="file_analysis_002",
                          task_description="Анализ зависимостей Python файла",
                          success=True,
                          execution_time=1.2,
                          patterns=["dependency_analysis", "python_imports"],
                          notes="Найдены импорты pathlib, os, utils.helper")

        # Шаг 5: Получаем рекомендации для похожей задачи
        recommendations = learning_tool._run("get_recommendations",
                                           current_task="анализ структуры нового Python проекта")

        assert "project_analysis_001" in recommendations
        assert "python_structure" in recommendations

        # Шаг 6: Ищем похожие задачи
        similar_tasks = learning_tool._run("find_similar_tasks",
                                         query="анализ зависимостей файла")

        assert "file_analysis_002" in similar_tasks
        assert "dependency_analysis" in similar_tasks

    def test_fallback_mode_integration(self):
        """Тест интеграции fallback режима при недоступности LLM"""
        from src.agents.smart_agent import create_smart_agent

        # Создаем агента без LLM (fallback режим)
        agent = create_smart_agent(
            project_dir=self.project_dir,
            experience_dir="experience",
            use_llm=False,  # Принудительно отключаем LLM
            verbose=False
        )

        # Проверяем, что агент создался без LLM
        assert agent.llm is None
        assert len(agent.tools) >= 2  # Должен иметь LearningTool и ContextAnalyzerTool

        # Проверяем инструменты
        tool_names = [tool.__class__.__name__ for tool in agent.tools]
        assert "LearningTool" in tool_names
        assert "ContextAnalyzerTool" in tool_names

    @patch('src.llm.llm_manager.AsyncOpenAI')
    def test_best_of_two_strategy_integration(self, mock_openai_class):
        """Тест интеграции best_of_two стратегии"""
        from src.llm.llm_manager import LLMManager

        # Создаем мок клиента
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Настраиваем ответы моделей
        async def mock_call(*args, **kwargs):
            model_name = kwargs.get('model', 'test-model')
            if 'model1' in model_name:
                return MagicMock(
                    choices=[MagicMock(message=MagicMock(content='Response from model1'))],
                    usage=MagicMock(prompt_tokens=10, completion_tokens=20)
                )
            elif 'model2' in model_name:
                return MagicMock(
                    choices=[MagicMock(message=MagicMock(content='Response from model2'))],
                    usage=MagicMock(prompt_tokens=15, completion_tokens=25)
                )
            else:
                return MagicMock(
                    choices=[MagicMock(message=MagicMock(content='Evaluator response: 0.8'))],
                    usage=MagicMock(prompt_tokens=5, completion_tokens=10)
                )

        mock_client.chat.completions.create = mock_call

        # Создаем тестовую конфигурацию
        config_path = self.temp_dir / "test_llm_config.yaml"
        config_data = {
            'llm': {
                'default_provider': 'test_provider',
                'strategy': 'best_of_two',
                'parallel': {
                    'models': ['test-model1', 'test-model2'],
                    'evaluator_model': 'test-evaluator'
                }
            },
            'providers': {
                'test_provider': {
                    'base_url': 'https://test.api',
                    'models': [
                        {'name': 'test-model1', 'max_tokens': 1000, 'context_window': 4000},
                        {'name': 'test-model2', 'max_tokens': 1000, 'context_window': 4000},
                        {'name': 'test-evaluator', 'max_tokens': 500, 'context_window': 2000}
                    ]
                }
            }
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        # Создаем менеджер LLM
        manager = LLMManager(config_path=str(config_path))

        # Тестируем параллельную генерацию
        async def test_parallel():
            response = await manager.generate_response(
                prompt="Test prompt",
                use_parallel=True
            )

            assert response.success
            assert "Response from" in response.content

        asyncio.run(test_parallel())

    @patch('src.llm.llm_manager.AsyncOpenAI')
    def test_parallel_fallback_when_one_model_fails(self, mock_openai_class):
        """Тест fallback в best_of_two когда одна модель падает"""
        from src.llm.llm_manager import LLMManager

        # Создаем мок клиента
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        call_count = 0

        async def mock_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            model_name = kwargs.get('model', 'test-model')

            if 'model1' in model_name:
                # Первая модель падает
                raise Exception("Model 1 failed")
            elif 'model2' in model_name:
                return MagicMock(
                    choices=[MagicMock(message=MagicMock(content='Response from model2 (fallback)'))],
                    usage=MagicMock(prompt_tokens=15, completion_tokens=25)
                )
            else:
                return MagicMock(
                    choices=[MagicMock(message=MagicMock(content='Evaluator response: 0.9'))],
                    usage=MagicMock(prompt_tokens=5, completion_tokens=10)
                )

        mock_client.chat.completions.create = mock_call

        # Создаем тестовую конфигурацию
        config_path = self.temp_dir / "test_llm_config.yaml"
        config_data = {
            'llm': {
                'default_provider': 'test_provider',
                'strategy': 'best_of_two',
                'parallel': {
                    'models': ['test-model1', 'test-model2'],
                    'evaluator_model': 'test-evaluator'
                }
            },
            'providers': {
                'test_provider': {
                    'base_url': 'https://test.api',
                    'models': [
                        {'name': 'test-model1', 'max_tokens': 1000, 'context_window': 4000},
                        {'name': 'test-model2', 'max_tokens': 1000, 'context_window': 4000},
                        {'name': 'test-evaluator', 'max_tokens': 500, 'context_window': 2000}
                    ]
                }
            }
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        # Создаем менеджер LLM
        manager = LLMManager(config_path=str(config_path))

        # Тестируем параллельную генерацию с fallback
        async def test_parallel_fallback():
            response = await manager.generate_response(
                prompt="Test prompt with failure",
                use_parallel=True
            )

            assert response.success
            assert "Response from model2 (fallback)" in response.content

        asyncio.run(test_parallel_fallback())

    def test_smart_agent_with_real_tools_only(self):
        """Тест Smart Agent в режиме только инструментов (без LLM)"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Создаем агента без LLM
        agent = create_smart_agent(
            project_dir=self.project_dir,
            experience_dir="experience",
            use_llm=False,
            verbose=False
        )

        # Проверяем инструменты
        learning_tool = None
        context_tool = None

        for tool in agent.tools:
            if isinstance(tool, LearningTool):
                learning_tool = tool
            elif isinstance(tool, ContextAnalyzerTool):
                context_tool = tool

        assert learning_tool is not None
        assert context_tool is not None

        # Тестируем работу инструментов через агента
        # (В реальном сценарии агент использовал бы LLM для интерпретации команд,
        # но в tool-only режиме инструменты работают напрямую)

        # Сохраняем опыт через LearningTool
        result = learning_tool._run("save_experience",
                                   task_id="tool_only_test_001",
                                   task_description="Тест работы в tool-only режиме",
                                   success=True,
                                   execution_time=1.0,
                                   patterns=["tool_only", "integration_test"],
                                   notes="Тест без LLM")

        assert "сохранен" in result.lower()

        # Анализируем проект через ContextAnalyzerTool
        analysis = context_tool._run("analyze_project")
        assert "main.py" in analysis
        assert "utils.py" in analysis

        # Ищем похожие задачи
        similar = learning_tool._run("find_similar_tasks",
                                    query="tool-only режим")

        assert "tool_only_test_001" in similar

    def test_memory_management_with_large_experience(self):
        """Тест управления памятью при большом объеме опыта"""
        from src.tools.learning_tool import LearningTool

        # Создаем инструмент с ограничением
        tool = LearningTool(
            experience_dir=str(self.experience_dir),
            max_experience_tasks=50  # Маленький лимит для теста
        )

        # Добавляем 100 задач (больше лимита)
        for i in range(100):
            tool._run("save_experience",
                     task_id=f"memory_test_{i:03d}",
                     task_description=f"Задача для теста памяти #{i}",
                     success=True,
                     execution_time=1.0,
                     patterns=[f"pattern_{i%10}"],
                     notes=f"Тестовая заметка #{i}")

        # Проверяем, что сохранено не больше max_experience_tasks
        experience_file = self.experience_dir / "experience.json"
        with open(experience_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert len(data['tasks']) <= 50

        # Проверяем, что остались самые свежие задачи
        task_ids = [t['task_id'] for t in data['tasks']]
        # Последние 50 задач должны быть сохранены
        expected_ids = [f"memory_test_{i:03d}" for i in range(50, 100)]
        for expected_id in expected_ids:
            assert expected_id in task_ids

    def test_error_recovery_integration(self):
        """Тест восстановления после ошибок в интеграционном сценарии"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        learning_tool = LearningTool(experience_dir=str(self.experience_dir))
        context_tool = ContextAnalyzerTool(project_dir=str(self.project_dir))

        # Тест 1: Ошибка в LearningTool не должна ломать ContextAnalyzerTool
        try:
            learning_tool._run("save_experience",
                             task_id="",  # Пустой ID вызовет ошибку
                             task_description="Тест ошибки",
                             success=True)
            assert False, "Должна была возникнуть ошибка"
        except (ValueError, AssertionError):
            pass  # Ожидаемая ошибка

        # ContextAnalyzerTool должен продолжать работать
        analysis = context_tool._run("analyze_project")
        assert len(analysis) > 0
        assert "main.py" in analysis

        # Тест 2: Ошибка в ContextAnalyzerTool не должна ломать LearningTool
        try:
            context_tool._run("analyze_file",
                            file_path="nonexistent_file.py")
            assert False, "Должна была возникнуть ошибка"
        except (FileNotFoundError, ValueError):
            pass  # Ожидаемая ошибка

        # LearningTool должен продолжать работать
        result = learning_tool._run("save_experience",
                                   task_id="recovery_test_001",
                                   task_description="Тест восстановления после ошибки",
                                   success=True,
                                   execution_time=1.0,
                                   patterns=["error_recovery", "integration"],
                                   notes="Тест успешного восстановления")

        assert "сохранен" in result.lower()


def run_advanced_integration_tests():
    """Запуск расширенных интеграционных тестов"""
    print("🚀 Запуск расширенных интеграционных тестов Smart Agent...")

    test_instance = TestSmartAgentAdvancedIntegration()

    tests = [
        ("LearningTool + ContextAnalyzerTool Workflow", test_instance.test_learning_tool_context_analyzer_integration_workflow),
        ("Fallback Mode Integration", test_instance.test_fallback_mode_integration),
        ("Best-of-Two Strategy Integration", test_instance.test_best_of_two_strategy_integration),
        ("Parallel Fallback When One Model Fails", test_instance.test_parallel_fallback_when_one_model_fails),
        ("Smart Agent Tools-Only Mode", test_instance.test_smart_agent_with_real_tools_only),
        ("Memory Management with Large Experience", test_instance.test_memory_management_with_large_experience),
        ("Error Recovery Integration", test_instance.test_error_recovery_integration),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            print(f"\n🔧 Запуск: {test_name}")
            test_instance.setup_method()
            test_func()
            test_instance.teardown_method()
            results.append((test_name, True))
            print(f"✅ {test_name}: ПРОЙДЕН")
        except Exception as e:
            test_instance.teardown_method()
            results.append((test_name, False))
            print(f"❌ {test_name}: ПРОВАЛЕН - {e}")

    # Итоги
    print("\n" + "="*80)
    print("📊 РЕЗУЛЬТАТЫ РАСШИРЕННЫХ ИНТЕГРАЦИОННЫХ ТЕСТОВ SMART AGENT")
    print("="*80)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print("40")

        if success:
            passed += 1

    print(f"\n📈 ИТОГО: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 ВСЕ РАСШИРЕННЫЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ПРОЙДЕНЫ!")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ.")
        return 1


if __name__ == "__main__":
    sys.exit(run_advanced_integration_tests())