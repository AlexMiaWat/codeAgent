"""
Общие типы и интерфейсы для LLM модулей

Этот модуль содержит:
- Перечисления и типы данных
- Абстрактные интерфейсы для компонентов
- Общие структуры данных
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Protocol
from pathlib import Path


class ModelRole(Enum):
    """Роли моделей"""
    PRIMARY = "primary"      # Рабочие модели
    DUPLICATE = "duplicate"  # Дублирующие модели
    RESERVE = "reserve"      # Резервные модели
    FALLBACK = "fallback"    # Модели на случай полного отказа


@dataclass
class ModelConfig:
    """Конфигурация модели"""
    name: str
    max_tokens: int
    context_window: int
    temperature: float = 0.7
    top_p: float = 1.0
    role: ModelRole = ModelRole.PRIMARY
    enabled: bool = True
    last_response_time: float = 0.0
    error_count: int = 0
    success_count: int = 0


@dataclass
class ModelResponse:
    """Ответ модели"""
    model_name: str
    content: str
    response_time: float
    success: bool
    error: Optional[str] = None
    score: Optional[float] = None


@dataclass
class ProviderConfig:
    """Конфигурация провайдера"""
    name: str
    base_url: str
    api_key: str
    models: List[Dict[str, Any]]
    timeout: int = 200


@dataclass
class GenerationRequest:
    """Запрос на генерацию"""
    prompt: str
    model_name: Optional[str] = None
    response_format: Optional[Dict[str, Any]] = None
    use_parallel: bool = False
    use_fastest: bool = True


@dataclass
class EvaluationResult:
    """Результат оценки ответа"""
    score: float
    reasoning: Optional[str] = None


# Интерфейсы компонентов

class IModelRegistry(Protocol):
    """Интерфейс реестра моделей"""

    def get_models_by_role(self, role: ModelRole) -> List[ModelConfig]:
        """Получить модели по роли"""
        ...

    def get_model(self, name: str) -> Optional[ModelConfig]:
        """Получить модель по имени"""
        ...

    def get_all_models(self) -> List[ModelConfig]:
        """Получить все модели"""
        ...

    def update_model_stats(self, model_name: str, success: bool, response_time: float) -> None:
        """Обновить статистику модели"""
        ...

    def get_fastest_model(self, role: ModelRole = ModelRole.PRIMARY) -> Optional[ModelConfig]:
        """Получить самую быструю модель"""
        ...

    def disable_model(self, model_name: str) -> None:
        """Отключить модель"""
        ...

    def enable_model(self, model_name: str) -> None:
        """Включить модель"""
        ...


class IClientManager(Protocol):
    """Интерфейс менеджера клиентов"""

    async def call_model(
        self,
        model_config: ModelConfig,
        prompt: str,
        response_format: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        """Вызвать модель"""
        ...


class IStrategyManager(Protocol):
    """Интерфейс менеджера стратегий генерации"""

    async def generate(
        self,
        request: GenerationRequest,
        registry: IModelRegistry,
        client_manager: IClientManager
    ) -> ModelResponse:
        """Выполнить генерацию по стратегии"""
        ...


class IResponseEvaluator(Protocol):
    """Интерфейс оценщика ответов"""

    async def evaluate_response(
        self,
        prompt: str,
        response: str,
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> EvaluationResult:
        """Оценить ответ"""
        ...

    async def compare_responses(
        self,
        prompt: str,
        responses: List[str],
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> List[EvaluationResult]:
        """Сравнить несколько ответов"""
        ...

    async def select_best_response(
        self,
        prompt: str,
        responses: List[str],
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> tuple[int, EvaluationResult]:
        """Выбрать лучший ответ"""
        ...


class IJsonValidator(Protocol):
    """Интерфейс валидатора JSON"""

    def validate_json(self, content: str) -> bool:
        """Проверить валидность JSON"""
        ...

    def extract_json_from_text(self, text: str) -> Optional[str]:
        """Извлечь JSON из текста"""
        ...

    def validate_and_extract(self, content: str) -> tuple[bool, Optional[str]]:
        """Проверить и извлечь JSON из контента"""
        ...


class IHealthMonitor(Protocol):
    """Интерфейс монитора здоровья"""

    async def check_health(self) -> Dict[str, bool]:
        """Проверить здоровье моделей"""
        ...

    def disable_model(self, model_name: str) -> None:
        """Отключить модель"""
        ...

    def enable_model(self, model_name: str) -> None:
        """Включить модель"""
        ...


class IConfigLoader(Protocol):
    """Интерфейс загрузчика конфигурации"""

    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """Загрузить конфигурацию"""
        ...

    def substitute_env_vars(self, obj: Any) -> Any:
        """Подставить переменные окружения"""
        ...