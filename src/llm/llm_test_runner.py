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
import yaml

from .llm_manager import LLMManager, ModelConfig, ModelResponse

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
    
    async def test_all_models(
        self,
        simple_prompt: str = "Привет, это тестовое сообщение. Ответь кратко.",
        delay: float = 1.0
    ) -> Dict[str, Dict]:
        """
        Тестирование всех доступных моделей
        
        Args:
            simple_prompt: Текст тестового запроса
            delay: Задержка между тестами (секунды)
        
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
            
            # Тест 2: Простой запрос (если доступна)
            simple_response = None
            if available:
                await asyncio.sleep(delay)
                simple_response = await self.test_model_simple(model_config, simple_prompt)
            
            # Сохраняем результаты
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
            
            logger.info(f"Model {model_name}: available={available}, "
                       f"response_time={simple_response.response_time if simple_response else None}")
            
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
            
            simple_test = result.get('simple_test', {})
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
            if result.get('available', False) and result.get('simple_test', {}).get('success', False):
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
