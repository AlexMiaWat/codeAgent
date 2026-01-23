"""
Модуль тестирования LLM моделей

Используется для проверки работоспособности моделей,
измерения времени отклика и выбора оптимальных моделей.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from .manager import LLMManager
from .types import ModelConfig, ModelResponse

logger = logging.getLogger(__name__)


class LLMTestRunner:
    """
    Класс для тестирования LLM моделей
    
    Основные функции:
    - Тестирование доступности моделей
    - Измерение времени отклика
    - Проверка работоспособности моделей
    - Экспорт результатов тестирования
    """
    
    def __init__(self, llm_manager: Optional[LLMManager] = None):
        """
        Инициализация тестера моделей
        
        Args:
            llm_manager: Экземпляр LLMManager (если None - создается новый)
        """
        if llm_manager is None:
            self.llm_manager = LLMManager()
        else:
            self.llm_manager = llm_manager
        
        self.test_results: List[Dict] = []
    
    async def test_model_availability(self, model_config: ModelConfig) -> Tuple[bool, str]:
        """
        Быстрая проверка доступности модели
        
        Args:
            model_config: Конфигурация модели для тестирования
        
        Returns:
            Кортеж (доступна, сообщение)
        """
        try:
            response = await self.llm_manager._call_model("test", model_config)
            if response.success:
                return True, "Available"
            else:
                return False, response.error or "Unknown error"
        except Exception as e:
            return False, str(e)
    
    async def test_model_simple(
        self,
        model_config: ModelConfig,
        prompt: str = "Привет, это тестовое сообщение. Ответь кратко."
    ) -> ModelResponse:
        """
        Простой тест модели
        
        Args:
            model_config: Конфигурация модели
            prompt: Текст тестового запроса
        
        Returns:
            ModelResponse с результатом
        """
        return await self.llm_manager._call_model(prompt, model_config)
    
    async def test_model_usefulness_check(
        self,
        model_config: ModelConfig,
        test_todo_text: str = "Добавить обработку ошибок в API",
        project_docs: str = "Проект Code Agent - система автоматизации задач через LLM"
    ) -> ModelResponse:
        """
        Тест модели на реальном промпте проверки полезности задачи (JSON mode)
        
        Это критичный тест, который проверяет способность модели:
        - Работать в JSON mode
        - Правильно обрабатывать структурированные запросы
        - Возвращать валидный JSON
        
        Args:
            model_config: Конфигурация модели
            test_todo_text: Текст тестового TODO пункта
            project_docs: Контекст проекта для промпта
        
        Returns:
            ModelResponse с результатом (должен содержать валидный JSON)
        """
        check_prompt = f"""Оцени полезность этого пункта из TODO списка проекта.

КОНТЕКСТ ПРОЕКТА (документация):
{project_docs[:2000] if len(project_docs) > 2000 else project_docs}

ПУНКТ TODO:
{test_todo_text}

Оцени полезность задачи в процентах от 0% до 100%:
- 0-15% - это мусор/шум, не является реальной задачей (случайный текст, личные заметки, дубликаты, пустые строки)
- 16-50% - слабая полезность, возможно неполная или неясная задача
- 51-80% - средняя полезность, задача понятна но может быть улучшена
- 81-100% - высокая полезность, четкая и конкретная техническая задача

Учитывай контекст проекта из документации при оценке. Технические задачи, связанные с проектом, должны иметь высокую полезность.

Верни JSON объект со следующей структурой:
{{
  "usefulness_percent": число от 0 до 100,
  "comment": "краткий комментарий о полезности задачи"
}}"""
        
        json_response_format = {"type": "json_object"}
        return await self.llm_manager._call_model(check_prompt, model_config, response_format=json_response_format)
    
    async def test_all_models(
        self,
        simple_prompt: str = "Привет, это тестовое сообщение. Ответь кратко.",
        delay: float = 1.0,
        use_usefulness_test: bool = False,
        test_todo_text: str = "Добавить обработку ошибок в API",
        project_docs: str = "Проект Code Agent - система автоматизации задач через LLM"
    ) -> Dict[str, Dict]:
        """
        Тестирование всех доступных моделей
        
        Args:
            simple_prompt: Текст тестового запроса
            delay: Задержка между тестами (секунды)
            use_usefulness_test: Использовать реальный тест проверки полезности (JSON mode) вместо простого
            test_todo_text: Текст тестового TODO пункта (если use_usefulness_test=True)
            project_docs: Контекст проекта для промпта (если use_usefulness_test=True)
        
        Returns:
            Словарь с результатами тестирования по моделям
        """
        results = {}
        
        # Тестируем все модели
        all_models = list(self.llm_manager.models.values())
        
        for model_config in all_models:
            if not model_config.enabled:
                continue
            
            model_name = model_config.name
            logger.info(f"Testing model: {model_name}")
            
            # Тест 1: Проверка доступности
            available, avail_msg = await self.test_model_availability(model_config)
            
            # Тест 2: Простой запрос или тест проверки полезности (если доступна)
            simple_response = None
            usefulness_response = None
            json_valid = False
            if available:
                await asyncio.sleep(delay)
                if use_usefulness_test:
                    # Используем реальный тест проверки полезности (JSON mode)
                    usefulness_response = await self.test_model_usefulness_check(
                        model_config, test_todo_text, project_docs
                    )
                    # Проверяем валидность JSON
                    if usefulness_response.success:
                        import json
                        try:
                            json.loads(usefulness_response.content)
                            json_valid = True
                        except json.JSONDecodeError:
                            json_valid = False
                else:
                    # Простой тест
                    simple_response = await self.test_model_simple(model_config, simple_prompt)
            
            # Сохраняем результаты
            if use_usefulness_test and usefulness_response:
                # Используем результаты теста проверки полезности
                results[model_name] = {
                    'available': available,
                    'availability_message': avail_msg,
                    'usefulness_test': {
                        'success': usefulness_response.success and json_valid,
                        'response_time': usefulness_response.response_time if usefulness_response else None,
                        'content_length': len(usefulness_response.content) if usefulness_response and usefulness_response.success else 0,
                        'error': usefulness_response.error if usefulness_response and not usefulness_response.success else None,
                        'json_valid': json_valid
                    },
                    'simple_test': {
                        'success': False,  # Не использовался
                        'response_time': None,
                        'content_length': 0,
                        'error': None
                    },
                    'model_config': {
                        'role': model_config.role.value,
                        'max_tokens': model_config.max_tokens,
                        'context_window': model_config.context_window,
                        'last_response_time': model_config.last_response_time,
                        'success_count': model_config.success_count,
                        'error_count': model_config.error_count
                    }
                }
            else:
                # Используем результаты простого теста
                results[model_name] = {
                    'available': available,
                    'availability_message': avail_msg,
                    'simple_test': {
                        'success': simple_response.success if simple_response else False,
                    'response_time': simple_response.response_time if simple_response else None,
                    'content_length': len(simple_response.content) if simple_response and simple_response.success else 0,
                    'error': simple_response.error if simple_response and not simple_response.success else None
                },
                'model_config': {
                    'role': model_config.role.value,
                    'max_tokens': model_config.max_tokens,
                    'context_window': model_config.context_window,
                    'last_response_time': model_config.last_response_time,
                    'success_count': model_config.success_count,
                    'error_count': model_config.error_count
                }
            }
            
            response_time = (usefulness_response.response_time if usefulness_response else simple_response.response_time) if (usefulness_response or simple_response) else None
            logger.info(f"Model {model_name}: available={available}, "
                       f"response_time={response_time}")
            
            await asyncio.sleep(delay)
        
        self.test_results = results
        return results
    
    def get_fastest_models(self, min_available: bool = True) -> List[Tuple[str, float]]:
        """
        Получить список моделей отсортированных по скорости
        
        Args:
            min_available: Только доступные модели
        
        Returns:
            Список кортежей (имя_модели, время_отклика)
        """
        fastest = []
        
        for model_name, result in self.test_results.items():
            if min_available and not result.get('available', False):
                continue
            
            # Проверяем либо simple_test, либо usefulness_test
            simple_test = result.get('simple_test', {})
            usefulness_test = result.get('usefulness_test', {})
            
            # Используем время отклика из теста проверки полезности, если он есть и успешен
            if usefulness_test and usefulness_test.get('success', False) and usefulness_test.get('json_valid', False):
                response_time = usefulness_test.get('response_time')
            else:
                response_time = simple_test.get('response_time')
            
            if response_time is not None:
                fastest.append((model_name, response_time))
        
        # Сортируем по времени отклика (быстрее = меньше)
        fastest.sort(key=lambda x: x[1])
        
        return fastest
    
    def get_working_models(self) -> List[str]:
        """
        Получить список работающих моделей
        
        Returns:
            Список имен работающих моделей
        """
        working = []
        
        for model_name, result in self.test_results.items():
            # Проверяем либо simple_test, либо usefulness_test
            simple_test = result.get('simple_test', {})
            usefulness_test = result.get('usefulness_test', {})
            
            if result.get('available', False):
                # Если есть тест проверки полезности - используем его (более строгий критерий)
                if usefulness_test:
                    if usefulness_test.get('success', False) and usefulness_test.get('json_valid', False):
                        working.append(model_name)
                # Иначе используем простой тест
                elif simple_test.get('success', False):
                    working.append(model_name)
        
        return working
    
    def export_results_markdown(self, output_path: Optional[Path] = None) -> Path:
        """
        Экспорт результатов тестирования в Markdown
        
        Args:
            output_path: Путь для сохранения (если None - генерируется автоматически)
        
        Returns:
            Path к сохраненному файлу
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"logs/llm_test_results_{timestamp}.md")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Генерируем Markdown
        lines = [
            "# LLM Models Test Results",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            f"**Total models tested:** {len(self.test_results)}",
            f"**Working models:** {len(self.get_working_models())}",
            "",
            "## Fastest Models",
            "",
            "| Model | Response Time | Available | Status |",
            "|-------|---------------|-----------|--------|"
        ]
        
        fastest = self.get_fastest_models()
        for model_name, response_time in fastest[:10]:  # Топ-10
            result = self.test_results[model_name]
            available = "✓" if result.get('available') else "✗"
            simple_test = result.get('simple_test', {})
            status = "OK" if simple_test.get('success') else "FAILED"
            lines.append(f"| {model_name} | {response_time:.2f}s | {available} | {status} |")
        
        lines.extend([
            "",
            "## Detailed Results",
            ""
        ])
        
        for model_name, result in self.test_results.items():
            available = result.get('available', False)
            simple_test = result.get('simple_test', {})
            model_config = result.get('model_config', {})
            
            lines.extend([
                f"### {model_name}",
                "",
                f"**Role:** {model_config.get('role', 'unknown')}",
                f"**Available:** {available}",
                f"**Availability Message:** {result.get('availability_message', 'N/A')}",
                "",
                "#### Simple Test",
                f"- **Success:** {simple_test.get('success', False)}",
                f"- **Response Time:** {simple_test.get('response_time', 'N/A')}s",
                f"- **Content Length:** {simple_test.get('content_length', 0)} chars",
            ])
            
            if simple_test.get('error'):
                lines.append(f"- **Error:** {simple_test.get('error')}")
            
            lines.extend([
                "",
                "#### Statistics",
                f"- **Last Response Time:** {model_config.get('last_response_time', 0)}s",
                f"- **Success Count:** {model_config.get('success_count', 0)}",
                f"- **Error Count:** {model_config.get('error_count', 0)}",
                "",
                "---",
                ""
            ])
        
        # Сохраняем файл
        output_path.write_text('\n'.join(lines), encoding='utf-8')
        logger.info(f"Test results exported to: {output_path}")
        
        return output_path
