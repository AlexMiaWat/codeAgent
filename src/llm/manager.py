"""
Новый LLMManager - фасад для всех компонентов LLM модуля

Обеспечивает:
- Единый интерфейс для всех операций
- Управление жизненным циклом компонентов
- Dependency injection
- Логирование и мониторинг
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from .types import (
    ModelConfig, ModelResponse, ModelRole,
    GenerationRequest, EvaluationResult
)
from .registry import ModelRegistry
from .client import ClientManager
from .strategy import StrategyManager
from .evaluator import ResponseEvaluator
from .validator import JsonValidator
from .monitor import HealthMonitor
from .config_loader import ConfigLoader

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Новый LLM Manager - фасад для модульной архитектуры LLM компонентов

    Предоставляет единый интерфейс для:
    - Генерации ответов
    - Управления моделями
    - Мониторинга здоровья
    - Оценки качества ответов
    """

    def __init__(self, config_path: str = "config/llm_settings.yaml"):
        """
        Инициализация LLM Manager

        Args:
            config_path: Путь к конфигурационному файлу
        """
        self.config_path = Path(config_path)

        # Инициализируем компоненты
        self.config_loader = ConfigLoader()

        # Загружаем конфигурацию
        self.config = self.config_loader.load_config(self.config_path)

        # Создаем компоненты
        self.registry = ModelRegistry(self.config_loader, str(self.config_path))
        self.client_manager = ClientManager(self.config_loader, str(self.config_path))
        self.json_validator = JsonValidator()

        # Компоненты, зависящие от других
        self.evaluator = ResponseEvaluator()
        self.strategy_manager = StrategyManager(
            self.registry,
            self.client_manager,
            self.evaluator,
            self.json_validator
        )
        self.health_monitor = HealthMonitor(self.registry, self.client_manager)

        # Настраиваем evaluator модель
        self._setup_evaluator_model()

        logger.info("LLMManager initialized with modular architecture")

    def _setup_evaluator_model(self):
        """Настроить модель-оценщик"""
        llm_config = self.config.get('llm', {})
        parallel_config = llm_config.get('parallel', {})
        evaluator_model_name = parallel_config.get('evaluator_model')

        if evaluator_model_name:
            evaluator_model = self.registry.get_model(evaluator_model_name)
            if evaluator_model:
                self.evaluator.set_evaluator_model(evaluator_model)
                logger.info(f"Set evaluator model: {evaluator_model_name}")
            else:
                logger.warning(f"Evaluator model '{evaluator_model_name}' not found")

    async def initialize(self):
        """Асинхронная инициализация компонентов"""
        # Запускаем мониторинг здоровья
        await self.health_monitor.start_monitoring()
        logger.info("LLMManager fully initialized")

    async def shutdown(self):
        """Корректное завершение работы"""
        await self.health_monitor.stop_monitoring()
        logger.info("LLMManager shut down")

    # Основные публичные методы (совместимые со старым API)

    async def generate_response(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        use_fastest: bool = True,
        use_parallel: bool = False,
        response_format: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        """
        Генерация ответа (основной метод)

        Args:
            prompt: Текст запроса
            model_name: Имя модели (опционально)
            use_fastest: Использовать самую быструю модель
            use_parallel: Использовать параллельную генерацию
            response_format: Формат ответа (JSON mode и т.д.)

        Returns:
            ModelResponse с результатом
        """
        # Определяем стратегию генерации
        llm_config = self.config.get('llm', {})
        strategy = llm_config.get('strategy', 'single')

        # Для JSON mode приоритетно используем best_of_two
        if response_format and response_format.get("type") == "json_object":
            if not use_parallel and strategy != 'best_of_two':
                logger.debug("JSON mode request - using best_of_two strategy")
                use_parallel = True

        # Создаем запрос на генерацию
        request = GenerationRequest(
            prompt=prompt,
            model_name=model_name,
            use_fastest=use_fastest,
            use_parallel=use_parallel,
            response_format=response_format
        )

        # Выполняем генерацию
        return await self.strategy_manager.generate(request)

    # Методы для работы с моделями

    def get_primary_models(self) -> List[ModelConfig]:
        """Получить список первичных моделей"""
        return self.registry.get_models_by_role(ModelRole.PRIMARY)

    def get_fallback_models(self) -> List[ModelConfig]:
        """Получить список резервных моделей"""
        return self.registry.get_models_by_role(ModelRole.FALLBACK)

    def get_fastest_model(self) -> Optional[ModelConfig]:
        """Получить самую быструю модель"""
        return self.registry.get_fastest_model()

    def get_model(self, name: str) -> Optional[ModelConfig]:
        """Получить модель по имени"""
        return self.registry.get_model(name)

    # Методы для оценки ответов

    async def evaluate_response(
        self,
        prompt: str,
        response: str,
        evaluator_model: Optional[ModelConfig] = None
    ) -> EvaluationResult:
        """Оценить качество ответа"""
        return await self.evaluator.evaluate_response(prompt, response, self.client_manager, evaluator_model)

    async def compare_responses(
        self,
        prompt: str,
        responses: List[str],
        evaluator_model: Optional[ModelConfig] = None
    ) -> List[EvaluationResult]:
        """Сравнить несколько ответов"""
        return await self.evaluator.compare_responses(prompt, responses, self.client_manager, evaluator_model)

    # Методы для валидации JSON

    def validate_json(self, content: str) -> bool:
        """Проверить валидность JSON"""
        return self.json_validator.validate_json(content)

    def extract_json_from_text(self, text: str) -> Optional[str]:
        """Извлечь JSON из текста"""
        return self.json_validator.extract_json_from_text(text)

    # Методы для мониторинга здоровья

    async def check_health(self) -> Dict[str, bool]:
        """Проверить здоровье всех моделей"""
        return await self.health_monitor.check_health()

    def disable_model(self, model_name: str) -> None:
        """Отключить модель"""
        self.health_monitor.disable_model(model_name)

    def enable_model(self, model_name: str) -> None:
        """Включить модель"""
        self.health_monitor.enable_model(model_name)

    # Служебные методы

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику компонентов"""
        return {
            'models': {
                'total': len(self.registry.models),
                'primary': len(self.registry.get_models_by_role(ModelRole.PRIMARY)),
                'fallback': len(self.registry.get_models_by_role(ModelRole.FALLBACK)),
                'disabled': len([m for m in self.registry.models.values() if not m.enabled])
            },
            'health_monitor': self.health_monitor.get_health_stats(),
            'config': {
                'path': str(self.config_path),
                'default_provider': self.config.get('llm', {}).get('default_provider')
            }
        }

    # Backward compatibility методы

    def _validate_json_response(self, content: str) -> bool:
        """Старый метод для совместимости"""
        return self.validate_json(content)

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """Старый метод для совместимости"""
        return self.extract_json_from_text(text)