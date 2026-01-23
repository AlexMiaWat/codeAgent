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
    GenerationRequest, EvaluationResult, RoutingDecision
)
from .registry import ModelRegistry
from .client import ClientManager
from .strategy import StrategyManager
from .evaluator import ResponseEvaluator
from .intelligent_evaluator import IntelligentEvaluator
from .validator import JsonValidator
from .monitor import HealthMonitor
from .intelligent_router import IntelligentRouter
from .adaptive_strategy import AdaptiveStrategyManager
from .error_learning_system import ErrorLearningSystem
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
        self.intelligent_evaluator = IntelligentEvaluator()
        self.intelligent_router = IntelligentRouter(self.registry)
        self.strategy_manager = StrategyManager(
            self.registry,
            self.client_manager,
            self.evaluator,
            self.json_validator
        )
        self.adaptive_strategy_manager = AdaptiveStrategyManager(
            self.registry,
            self.client_manager,
            self.evaluator,
            self.json_validator,
            self.intelligent_router
        )
        self.error_learning_system = ErrorLearningSystem(
            self.registry,
            self.intelligent_router,
            self.adaptive_strategy_manager,
            self.intelligent_evaluator
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
        response_format: Optional[Dict[str, Any]] = None,
        use_intelligent_routing: bool = True
    ) -> ModelResponse:
        """
        Генерация ответа (основной метод)

        Args:
            prompt: Текст запроса
            model_name: Имя модели (опционально)
            use_fastest: Использовать самую быструю модель
            use_parallel: Использовать параллельную генерацию
            response_format: Формат ответа (JSON mode и т.д.)
            use_intelligent_routing: Использовать интеллектуальный роутинг

        Returns:
            ModelResponse с результатом
        """
        # Создаем запрос на генерацию
        request = GenerationRequest(
            prompt=prompt,
            model_name=model_name,
            use_fastest=use_fastest,
            use_parallel=use_parallel,
            response_format=response_format
        )

        # Используем интеллектуальный роутинг если включен и не указана конкретная модель
        if use_intelligent_routing and not model_name:
            routing_decision = self.intelligent_router.route_request(request)
            logger.debug(f"Intelligent routing decision: {routing_decision.reasoning}")

            # Применяем решение роутера
            if routing_decision.model_name:
                request.model_name = routing_decision.model_name

            if routing_decision.strategy == "parallel":
                request.use_parallel = True
            elif routing_decision.strategy == "single":
                request.use_parallel = False
        else:
            # Используем legacy логику для обратной совместимости
            llm_config = self.config.get('llm', {})
            strategy = llm_config.get('strategy', 'single')

            # Для JSON mode приоритетно используем best_of_two
            if response_format and response_format.get("type") == "json_object":
                if not use_parallel and strategy != 'best_of_two':
                    logger.debug("JSON mode request - using best_of_two strategy")
                    use_parallel = True

        # Выполняем генерацию
        response = await self.strategy_manager.generate(request)

        # Обучаемся на результате (асинхронно, не блокируя ответ)
        asyncio.create_task(self._learn_from_response_async(request, response))

        return response

    async def generate_adaptive(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        use_intelligent_routing: bool = True
    ) -> ModelResponse:
        """
        Адаптивная генерация - автоматически выбирает оптимальную стратегию

        Args:
            prompt: Текст запроса
            model_name: Имя модели (опционально, для совместимости)
            response_format: Формат ответа (JSON mode и т.д.)
            use_intelligent_routing: Использовать интеллектуальный роутинг

        Returns:
            ModelResponse с результатом
        """
        # Создаем запрос на генерацию
        request = GenerationRequest(
            prompt=prompt,
            model_name=model_name,
            response_format=response_format
        )

        # Используем адаптивный менеджер стратегий
        response = await self.adaptive_strategy_manager.generate_adaptive(request)

        # Обучаемся на результате
        asyncio.create_task(self._learn_from_response_async(request, response))

        return response

    async def _learn_from_response_async(self, request: GenerationRequest, response: ModelResponse):
        """Асинхронное обучение на ответе"""
        try:
            # Определяем тип задачи
            analysis = self.intelligent_router.analyze_request(request)
            task_type = analysis.task_type.value

            # Пытаемся оценить ответ для обучения
            evaluation_score = None
            if response.success and len(response.content.strip()) > 10:
                try:
                    evaluation = await self.evaluate_response(
                        prompt=request.prompt,
                        response=response.content
                    )
                    evaluation_score = evaluation.score
                except Exception as e:
                    logger.debug(f"Could not evaluate response for learning: {e}")

            # Обучаемся через роутер
            self.intelligent_router.learn_from_result(request, response, evaluation_score)

            # Анализируем ошибки через систему обучения
            if not response.success or (evaluation_score is not None and evaluation_score < 3.0):
                error_message = response.error or "Low quality response"
                await self.error_learning_system.analyze_and_learn_from_error(
                    request_prompt=request.prompt,
                    model_name=response.model_name,
                    response=response,
                    error_message=error_message,
                    task_type=task_type
                )

        except Exception as e:
            logger.debug(f"Error during learning from response: {e}")

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

    async def evaluate_response_intelligent(
        self,
        prompt: str,
        response: str,
        task_type: str = "unknown",
        use_detailed_evaluation: bool = True
    ) -> Any:
        """
        Интеллектуальная оценка ответа

        Args:
            prompt: Исходный запрос
            response: Ответ для оценки
            task_type: Тип задачи для контекстной оценки
            use_detailed_evaluation: Использовать детальную оценку

        Returns:
            DetailedEvaluation или EvaluationResult
        """
        if use_detailed_evaluation:
            return await self.intelligent_evaluator.evaluate_intelligent(
                prompt=prompt,
                response=response,
                client_manager=self.client_manager,
                task_type=task_type
            )
        else:
            # Используем старый метод для обратной совместимости
            return await self.evaluator.evaluate_response(
                prompt=prompt,
                response=response,
                client_manager=self.client_manager
            )

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

    # Методы для интеллектуального роутинга

    def analyze_request(self, prompt: str, **kwargs) -> Any:
        """Анализировать запрос с помощью интеллектуального роутера"""
        from .types import GenerationRequest
        request = GenerationRequest(prompt=prompt, **kwargs)
        return self.intelligent_router.analyze_request(request)

    def get_routing_decision(self, prompt: str, **kwargs) -> RoutingDecision:
        """Получить решение о маршрутизации для запроса"""
        from .types import GenerationRequest
        request = GenerationRequest(prompt=prompt, **kwargs)
        return self.intelligent_router.route_request(request)

    def get_intelligent_routing_stats(self) -> Dict[str, Any]:
        """Получить статистику интеллектуального роутинга"""
        return self.intelligent_router.get_routing_stats()

    def reset_routing_learning(self):
        """Сбросить данные обучения роутера"""
        self.intelligent_router.reset_learning_data()

    def enable_routing_learning(self, enabled: bool = True):
        """Включить/выключить обучение роутера"""
        self.intelligent_router.enable_learning(enabled)

    def get_adaptive_strategy_stats(self) -> Dict[str, Any]:
        """Получить статистику адаптивного менеджера стратегий"""
        return self.adaptive_strategy_manager.get_adaptive_stats()

    def get_strategy_recommendations(self, task_type: str) -> List[Dict[str, Any]]:
        """Получить рекомендации по стратегиям для типа задач"""
        return self.adaptive_strategy_manager.get_strategy_recommendations(task_type)

    def reset_adaptive_learning(self):
        """Сбросить данные обучения адаптивного менеджера стратегий"""
        self.adaptive_strategy_manager.reset_adaptive_learning()

    def get_intelligent_evaluation_stats(self) -> Dict[str, Any]:
        """Получить статистику интеллектуального оценщика"""
        return self.intelligent_evaluator.get_evaluation_stats()

    def reset_evaluation_history(self):
        """Сбросить историю оценок"""
        self.intelligent_evaluator.reset_evaluation_history()

    def get_error_learning_stats(self) -> Dict[str, Any]:
        """Получить статистику системы обучения на ошибках"""
        return self.error_learning_system.get_learning_stats()

    def get_error_prevention_recommendations(self, prompt: str, task_type: str = "unknown") -> List[str]:
        """Получить рекомендации по предотвращению ошибок"""
        return self.error_learning_system.get_error_prevention_recommendations(prompt, task_type)

    def reset_error_learning(self):
        """Сбросить данные обучения на ошибках"""
        self.error_learning_system.reset_learning_data()

    def enable_error_learning(self, enabled: bool = True):
        """Включить/выключить обучение на ошибках"""
        self.error_learning_system.enable_auto_learning(enabled)

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
            'intelligent_router': self.intelligent_router.get_routing_stats(),
            'adaptive_strategy': self.adaptive_strategy_manager.get_adaptive_stats(),
            'intelligent_evaluator': self.intelligent_evaluator.get_evaluation_stats(),
            'error_learning': self.error_learning_system.get_learning_stats(),
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