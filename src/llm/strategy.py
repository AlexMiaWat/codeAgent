"""
StrategyManager - стратегии генерации ответов

Ответственность:
- Single model generation
- Parallel generation (best_of_two)
- Fallback chains
- Retry logic с exponential backoff
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from .types import (
    ModelConfig, ModelResponse, ModelRole,
    GenerationRequest, IStrategyManager,
    IModelRegistry, IClientManager, IResponseEvaluator, IJsonValidator
)

logger = logging.getLogger(__name__)


class StrategyManager(IStrategyManager):
    """
    Менеджер стратегий - управляет различными стратегиями генерации ответов

    Предоставляет:
    - Single model generation
    - Parallel generation (best_of_two)
    - Fallback chains с retry logic
    - Обработку ошибок и таймаутов
    """

    def __init__(
        self,
        registry: IModelRegistry,
        client_manager: IClientManager,
        evaluator: IResponseEvaluator,
        json_validator: IJsonValidator
    ):
        """
        Инициализация менеджера стратегий

        Args:
            registry: Реестр моделей
            client_manager: Менеджер клиентов
            evaluator: Оценщик ответов
            json_validator: Валидатор JSON
        """
        self.registry = registry
        self.client_manager = client_manager
        self.evaluator = evaluator
        self.json_validator = json_validator

    async def generate(self, request: GenerationRequest) -> ModelResponse:
        """
        Выполнить генерацию по выбранной стратегии

        Args:
            request: Запрос на генерацию

        Returns:
            Ответ модели
        """
        if request.use_parallel:
            return await self._generate_parallel(request)
        else:
            return await self._generate_single(request)

    async def _generate_single(self, request: GenerationRequest) -> ModelResponse:
        """Генерация через одну модель"""
        # Выбираем модель
        if request.model_name and request.model_name in [m.name for m in self.registry.get_models_by_role(ModelRole.PRIMARY)]:
            model_config = self.registry.get_model(request.model_name)
        elif request.use_fastest:
            model_config = self.registry.get_fastest_model()
            if not model_config:
                raise ValueError("No available primary models")
        else:
            primary_models = self.registry.get_models_by_role(ModelRole.PRIMARY)
            if not primary_models:
                raise ValueError("No available primary models")
            model_config = primary_models[0]

        # Пробуем с fallback
        return await self._generate_with_fallback(request, model_config)

    async def _generate_with_fallback(
        self,
        request: GenerationRequest,
        primary_model: ModelConfig,
        retry_count: int = 0,
        max_retries: int = 2
    ) -> ModelResponse:
        """
        Генерация с fallback на резервные модели

        Args:
            request: Запрос на генерацию
            primary_model: Основная модель
            retry_count: Текущий счетчик повторных попыток
            max_retries: Максимальное количество повторных попыток

        Returns:
            ModelResponse - всегда возвращает ответ
        """
        models_to_try = [primary_model] + self.registry.get_models_by_role(ModelRole.FALLBACK)

        # Сохраняем последний ответ для fallback
        last_response: Optional[ModelResponse] = None

        for model_config in models_to_try:
            logger.info(f"Trying model {model_config.name} (attempt {retry_count + 1})")

            try:
                response = await self.client_manager.call_model(
                    model_config=model_config,
                    prompt=request.prompt,
                    response_format=request.response_format
                )

                last_response = response

                if response.success:
                    # Если запрашивался JSON mode, проверяем валидность
                    if request.response_format and request.response_format.get("type") == "json_object":
                        is_valid, _ = self.json_validator.validate_and_extract(response.content)
                        if not is_valid:
                            logger.warning(f"Model {model_config.name} returned invalid JSON, trying next model")
                            continue

                    # Успешный ответ
                    self.registry.update_model_stats(model_config.name, True, response.response_time)
                    return response
                else:
                    # Ошибка модели
                    self.registry.update_model_stats(model_config.name, False, response.response_time)
                    logger.warning(f"Model {model_config.name} failed: {response.error}")

            except Exception as e:
                logger.error(f"Unexpected error with model {model_config.name}: {e}")
                # Создаем failed response
                if last_response:
                    response_time = last_response.response_time
                else:
                    response_time = 0.0
                last_response = ModelResponse(
                    model_name=model_config.name,
                    content="",
                    response_time=response_time,
                    success=False,
                    error=str(e)
                )

        # Все модели провалились - возвращаем последний ответ или дефолтный
        if last_response:
            logger.error("All models failed, returning last response")
            return last_response
        else:
            # Абсолютный fallback
            logger.error("Complete failure - no models available")
            return ModelResponse(
                model_name="unknown",
                content="Service temporarily unavailable",
                response_time=0.0,
                success=False,
                error="All models failed"
            )

    async def _generate_parallel(self, request: GenerationRequest) -> ModelResponse:
        """Параллельная генерация через две модели с выбором лучшего ответа"""
        # Получаем модели для параллельного использования
        primary_models = self.registry.get_models_by_role(ModelRole.PRIMARY)

        if len(primary_models) < 2:
            logger.warning("Not enough primary models for parallel generation, falling back to single")
            return await self._generate_single(request)

        # Используем две самые быстрые модели
        model1 = self.registry.get_fastest_model(ModelRole.PRIMARY)
        remaining = [m for m in primary_models if m.name != model1.name]
        model2 = self.registry.get_fastest_model(ModelRole.PRIMARY) if remaining else model1

        # Таймаут для параллельной обработки (90 секунд по умолчанию)
        parallel_timeout = 90.0

        try:
            # Генерируем ответы параллельно
            responses = await asyncio.wait_for(
                asyncio.gather(
                    self.client_manager.call_model(model1, request.prompt, request.response_format),
                    self.client_manager.call_model(model2, request.prompt, request.response_format),
                    return_exceptions=True
                ),
                timeout=parallel_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Parallel generation timeout after {parallel_timeout}s")
            return await self._generate_single(request)

        # Обрабатываем результаты
        valid_responses = []
        for resp in responses:
            if isinstance(resp, Exception):
                logger.error(f"Parallel generation error: {resp}")
                continue
            if resp.success:
                # Проверяем JSON mode если нужно
                if request.response_format and request.response_format.get("type") == "json_object":
                    is_valid, _ = self.json_validator.validate_and_extract(resp.content)
                    if not is_valid:
                        logger.warning(f"Model {resp.model_name} returned invalid JSON in parallel mode")
                        continue
                valid_responses.append(resp)

        if not valid_responses:
            # Fallback на single режим
            logger.warning("All parallel models failed or returned invalid JSON")
            return await self._generate_single(request)

        if len(valid_responses) == 1:
            # Только одна модель сработала
            return valid_responses[0]

        # Обе модели сработали - выбираем лучший ответ
        return await self._select_best_response(valid_responses, request)

    async def _select_best_response(
        self,
        responses: List[ModelResponse],
        request: GenerationRequest
    ) -> ModelResponse:
        """Выбор лучшего ответа из нескольких"""
        if len(responses) == 1:
            return responses[0]

        # Оцениваем каждый ответ
        evaluation_timeout = 30.0  # 30 секунд на оценку
        scores = []

        for response in responses:
            try:
                evaluation_result = await asyncio.wait_for(
                    self.evaluator.evaluate_response(
                        prompt=request.prompt,
                        response=response.content,
                        client_manager=self.client_manager
                    ),
                    timeout=evaluation_timeout
                )
                response.score = evaluation_result.score
                scores.append(evaluation_result.score)
            except Exception as e:
                logger.warning(f"Evaluation failed for response from {response.model_name}: {e}")
                response.score = 3.0  # Низкая оценка при ошибке
                scores.append(3.0)

        # Выбираем ответ с максимальным score
        best_response = max(responses, key=lambda r: r.score or 0.0)

        logger.info(f"Selected best response from {best_response.model_name} (score: {best_response.score})")
        return best_response