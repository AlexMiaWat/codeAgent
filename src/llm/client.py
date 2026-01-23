"""
ClientManager - управление API клиентами провайдеров

Ответственность:
- Инициализация клиентов (OpenRouter, OpenAI, etc.)
- Управление ключами API
- Connection pooling
- Обработка сетевых ошибок
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

from .types import ModelConfig, ModelResponse, IClientManager, IConfigLoader, ProviderConfig

logger = logging.getLogger(__name__)


class ClientManager(IClientManager):
    """
    Менеджер клиентов API - управляет подключениями к провайдерам LLM

    Предоставляет:
    - Инициализацию клиентов для разных провайдеров
    - Управление API ключами
    - Пул соединений
    - Обработку сетевых ошибок
    """

    def __init__(self, config_loader: IConfigLoader, config_path: str = "config/llm_settings.yaml"):
        """
        Инициализация менеджера клиентов

        Args:
            config_loader: Загрузчик конфигурации
            config_path: Путь к файлу конфигурации
        """
        self.config_loader = config_loader
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.clients: Dict[str, AsyncOpenAI] = {}
        self.providers: Dict[str, ProviderConfig] = {}

        self._load_config()
        self._init_clients()

    def _load_config(self):
        """Загрузка конфигурации"""
        self.config = self.config_loader.load_config(self.config_path)

    def _init_clients(self):
        """Инициализация клиентов для провайдеров"""
        llm_config = self.config.get('llm', {})
        providers_config = self.config.get('providers', {})
        default_provider = llm_config.get('default_provider', 'openrouter')
        provider_config = providers_config.get(default_provider, {})

        base_url = provider_config.get('base_url')

        # API ключ должен быть в переменной окружения, а не в конфиге
        # Приоритет: переменная окружения > конфиг (для обратной совместимости)
        # Перезагружаем переменные окружения для получения актуального ключа
        load_dotenv(override=True)
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            # Fallback на конфиг (для обратной совместимости, но не рекомендуется)
            api_key = provider_config.get('api_key')
            if api_key:
                logger.warning("API key found in config file. Please move it to OPENROUTER_API_KEY environment variable or .env file for security.")

        if not api_key:
            raise ValueError(
                f"API key not found for provider '{default_provider}'. "
                f"Please set OPENROUTER_API_KEY environment variable or add it to .env file."
            )

        timeout = llm_config.get('timeout', 200)

        # Создаем провайдер конфиг
        self.providers[default_provider] = ProviderConfig(
            name=default_provider,
            base_url=base_url,
            api_key=api_key,
            models=provider_config.get('models', []),
            timeout=timeout
        )

        # Создаем клиент для всех моделей провайдера
        self.clients[default_provider] = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )

        logger.info(f"Initialized client for provider '{default_provider}'")

    def _get_provider_for_model(self, model_name: str) -> str:
        """Определить провайдера для модели"""
        # Пока поддерживается только один провайдер (openrouter)
        # В будущем можно расширить для поддержки multiple провайдеров
        return list(self.providers.keys())[0]

    def _get_client_for_model(self, model_name: str) -> AsyncOpenAI:
        """Получить клиент для модели"""
        provider_name = self._get_provider_for_model(model_name)
        if provider_name not in self.clients:
            raise ValueError(f"No client available for provider '{provider_name}'")
        return self.clients[provider_name]

    # Реализация интерфейса IClientManager

    async def call_model(
        self,
        model_config: ModelConfig,
        prompt: str,
        response_format: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        """
        Вызвать модель через соответствующий клиент

        Args:
            model_config: Конфигурация модели
            prompt: Текст запроса
            response_format: Формат ответа (JSON mode и т.д.)

        Returns:
            ModelResponse с результатом вызова
        """
        import time
        start_time = time.time()

        try:
            client = self._get_client_for_model(model_config.name)

            # Подготавливаем параметры запроса
            request_params = {
                "model": model_config.name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": model_config.max_tokens,
                "temperature": model_config.temperature,
                "top_p": model_config.top_p,
            }

            # Добавляем response_format если указан
            if response_format:
                request_params["response_format"] = response_format

            # Выполняем запрос
            response = await client.chat.completions.create(**request_params)

            response_time = time.time() - start_time
            content = response.choices[0].message.content

            return ModelResponse(
                model_name=model_config.name,
                content=content,
                response_time=response_time,
                success=True
            )

        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Model call failed: {str(e)}"

            logger.error(f"Error calling model {model_config.name}: {error_msg}")

            return ModelResponse(
                model_name=model_config.name,
                content="",
                response_time=response_time,
                success=False,
                error=error_msg
            )