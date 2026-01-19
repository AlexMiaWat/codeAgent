"""
Менеджер управления несколькими LLM моделями

Реализует:
- Выбор самой быстрой модели
- Fallback на резервные модели при ошибках
- Синхронное использование двух моделей с выбором лучшего ответа
- Оценку ответов моделями
"""

import os
import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

import yaml
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)


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


class LLMManager:
    """
    Менеджер управления несколькими LLM моделями
    
    Поддерживает:
    - Выбор самой быстрой модели
    - Fallback на резервные модели при ошибках
    - Синхронное использование двух моделей с выбором лучшего ответа
    - Оценку ответов моделями
    """
    
    def __init__(self, config_path: str = "config/llm_settings.yaml"):
        """
        Инициализация менеджера LLM
        
        Args:
            config_path: Путь к файлу конфигурации LLM
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.models: Dict[str, ModelConfig] = {}
        self.clients: Dict[str, AsyncOpenAI] = {}
        
        self._load_config()
        self._init_models()
        self._init_clients()
    
    def _load_config(self):
        """Загрузка конфигурации из YAML"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"LLM config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}
        
        # Подстановка переменных окружения
        self.config = self._substitute_env_vars(self.config)
    
    def _substitute_env_vars(self, obj: Any) -> Any:
        """Рекурсивная подстановка переменных окружения"""
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            var_expr = obj[2:-1]
            env_value = os.getenv(var_expr.strip())
            if env_value is None:
                raise ValueError(f"Environment variable not found: {var_expr}")
            return env_value
        return obj
    
    def _init_models(self):
        """Инициализация моделей из конфигурации"""
        llm_config = self.config.get('llm', {})
        providers_config = self.config.get('providers', {})
        model_roles = llm_config.get('model_roles', {})
        
        # Получаем конфигурацию провайдера
        default_provider = llm_config.get('default_provider', 'openrouter')
        provider_config = providers_config.get(default_provider, {})
        provider_models = provider_config.get('models', {})
        
        # Создаем модели с ролями
        for role_name, model_names in model_roles.items():
            role = ModelRole(role_name)
            for model_name in model_names:
                # Находим конфигурацию модели
                model_config_dict = self._find_model_config(model_name, provider_models)
                if model_config_dict:
                    # Убираем 'name' из словаря, т.к. передаем его отдельно
                    config_dict = {k: v for k, v in model_config_dict.items() if k != 'name'}
                    model_config = ModelConfig(
                        name=model_name,
                        role=role,
                        **config_dict
                    )
                    self.models[model_name] = model_config
        
        logger.info(f"Initialized {len(self.models)} models")
    
    def _find_model_config(self, model_name: str, provider_models: Dict) -> Optional[Dict]:
        """Поиск конфигурации модели в структуре провайдера"""
        # Модель может быть в разных вложенных структурах
        for provider_name, models_list in provider_models.items():
            if isinstance(models_list, list):
                for model in models_list:
                    if isinstance(model, dict) and model.get('name') == model_name:
                        return model
        return None
    
    def _init_clients(self):
        """Инициализация клиентов для провайдеров"""
        llm_config = self.config.get('llm', {})
        providers_config = self.config.get('providers', {})
        default_provider = llm_config.get('default_provider', 'openrouter')
        provider_config = providers_config.get(default_provider, {})
        
        base_url = provider_config.get('base_url')
        
        # API ключ должен быть в переменной окружения, а не в конфиге
        # Приоритет: переменная окружения > конфиг (для обратной совместимости)
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
        
        # Создаем клиент для всех моделей провайдера
        client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        self.clients[default_provider] = client
        
        logger.info(f"Initialized client for provider: {default_provider}")
    
    def get_primary_models(self) -> List[ModelConfig]:
        """Получить рабочие модели"""
        return [m for m in self.models.values() 
                if m.role == ModelRole.PRIMARY and m.enabled]
    
    def get_fallback_models(self) -> List[ModelConfig]:
        """Получить резервные модели (duplicate + reserve + fallback)"""
        return [m for m in self.models.values() 
                if m.role in [ModelRole.DUPLICATE, ModelRole.RESERVE, ModelRole.FALLBACK] 
                and m.enabled]
    
    def get_fastest_model(self) -> Optional[ModelConfig]:
        """Получить самую быструю модель (по last_response_time)"""
        primary_models = self.get_primary_models()
        if not primary_models:
            return None
        
        # Сортируем по времени ответа (быстрее = меньше)
        # Если время не измерено (0), считаем модель быстрой
        sorted_models = sorted(
            primary_models,
            key=lambda m: m.last_response_time if m.last_response_time > 0 else 0.0
        )
        
        return sorted_models[0]
    
    async def generate_response(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        use_fastest: bool = True,
        use_parallel: bool = False
    ) -> ModelResponse:
        """
        Генерация ответа через модель
        
        Args:
            prompt: Текст запроса
            model_name: Имя модели (если None - выбирается автоматически)
            use_fastest: Использовать самую быструю модель
            use_parallel: Использовать параллельное выполнение (best_of_two)
        
        Returns:
            ModelResponse с ответом модели
        """
        llm_config = self.config.get('llm', {})
        strategy = llm_config.get('strategy', 'single')
        
        # Определяем стратегию использования
        if use_parallel or strategy == 'best_of_two':
            return await self._generate_parallel(prompt)
        else:
            return await self._generate_single(prompt, model_name, use_fastest)
    
    async def _generate_single(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        use_fastest: bool = True
    ) -> ModelResponse:
        """Генерация ответа через одну модель"""
        # Выбираем модель
        if model_name and model_name in self.models:
            model_config = self.models[model_name]
        elif use_fastest:
            model_config = self.get_fastest_model()
            if not model_config:
                raise ValueError("No available primary models")
        else:
            primary_models = self.get_primary_models()
            if not primary_models:
                raise ValueError("No available primary models")
            model_config = primary_models[0]
        
        # Пробуем с fallback
        return await self._generate_with_fallback(prompt, model_config)
    
    async def _generate_with_fallback(
        self,
        prompt: str,
        primary_model: ModelConfig
    ) -> ModelResponse:
        """Генерация с fallback на резервные модели"""
        models_to_try = [primary_model] + self.get_fallback_models()
        
        for model_config in models_to_try:
            try:
                response = await self._call_model(prompt, model_config)
                if response.success:
                    return response
                else:
                    logger.warning(f"Model {model_config.name} failed: {response.error}")
                    model_config.error_count += 1
            except Exception as e:
                logger.error(f"Error calling model {model_config.name}: {e}")
                model_config.error_count += 1
                continue
        
        # Все модели провалились
        raise RuntimeError("All models failed to generate response")
    
    async def _generate_parallel(self, prompt: str) -> ModelResponse:
        """Параллельная генерация через две модели с выбором лучшего ответа"""
        llm_config = self.config.get('llm', {})
        parallel_config = llm_config.get('parallel', {})
        
        # Получаем модели для параллельного использования
        parallel_models_names = parallel_config.get('models', [])
        parallel_models = [
            self.models[name] for name in parallel_models_names 
            if name in self.models
        ]
        
        if len(parallel_models) < 2:
            # Недостаточно моделей для параллельного использования
            return await self._generate_single(prompt)
        
        # Используем первые две модели
        model1, model2 = parallel_models[0], parallel_models[1]
        
        # Генерируем ответы параллельно
        responses = await asyncio.gather(
            self._call_model(prompt, model1),
            self._call_model(prompt, model2),
            return_exceptions=True
        )
        
        # Обрабатываем результаты
        valid_responses = []
        for resp in responses:
            if isinstance(resp, Exception):
                logger.error(f"Parallel generation error: {resp}")
                continue
            if resp.success:
                valid_responses.append(resp)
        
        if not valid_responses:
            # Обе модели провалились - используем fallback
            return await self._generate_with_fallback(prompt, model1)
        
        if len(valid_responses) == 1:
            # Только одна модель сработала
            return valid_responses[0]
        
        # Обе модели сработали - выбираем лучший ответ
        return await self._select_best_response(valid_responses, prompt, parallel_config)
    
    async def _select_best_response(
        self,
        responses: List[ModelResponse],
        prompt: str,
        parallel_config: Dict
    ) -> ModelResponse:
        """Выбор лучшего ответа из нескольких через оценку моделью"""
        evaluator_model_name = parallel_config.get('evaluator_model')
        if not evaluator_model_name or evaluator_model_name not in self.models:
            # Нет модели-оценщика - возвращаем первый успешный ответ
            return responses[0]
        
        evaluator_config = self.models[evaluator_model_name]
        
        # Оцениваем каждый ответ
        for response in responses:
            score = await self._evaluate_response(
                prompt, response.content, evaluator_config
            )
            response.score = score
        
        # Выбираем ответ с максимальным score
        best_response = max(responses, key=lambda r: r.score or 0.0)
        
        logger.info(f"Selected best response from {best_response.model_name} (score: {best_response.score})")
        return best_response
    
    async def _evaluate_response(
        self,
        prompt: str,
        response: str,
        evaluator_model: ModelConfig
    ) -> float:
        """Оценка ответа моделью-оценщиком"""
        evaluation_prompt = f"""Оцени качество ответа на запрос.

Запрос: {prompt}

Ответ: {response}

Оцени ответ по шкале от 0 до 10, где:
- 0-3: Плохой ответ (не релевантный, неполный)
- 4-6: Средний ответ (частично релевантный, неполный)
- 7-9: Хороший ответ (релевантный, полный)
- 10: Отличный ответ (полностью релевантный, полный, качественный)

Ответь только числом от 0 до 10."""
        
        try:
            eval_response = await self._call_model(evaluation_prompt, evaluator_model)
            if eval_response.success:
                # Извлекаем число из ответа
                import re
                numbers = re.findall(r'\d+\.?\d*', eval_response.content)
                if numbers:
                    score = float(numbers[0])
                    return min(max(score, 0.0), 10.0)  # Ограничиваем 0-10
        except Exception as e:
            logger.error(f"Error evaluating response: {e}")
        
        return 5.0  # Средняя оценка по умолчанию
    
    async def _call_model(self, prompt: str, model_config: ModelConfig) -> ModelResponse:
        """Вызов модели для генерации ответа"""
        start_time = time.time()
        
        try:
            # Получаем клиент (пока только openrouter)
            client = list(self.clients.values())[0]
            
            response = await client.chat.completions.create(
                model=model_config.name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature,
                top_p=model_config.top_p
            )
            
            response_time = time.time() - start_time
            content = response.choices[0].message.content.strip()
            
            # Обновляем статистику модели
            model_config.last_response_time = response_time
            model_config.success_count += 1
            
            return ModelResponse(
                model_name=model_config.name,
                content=content,
                response_time=response_time,
                success=True
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            model_config.error_count += 1
            
            return ModelResponse(
                model_name=model_config.name,
                content="",
                response_time=response_time,
                success=False,
                error=error_msg
            )
