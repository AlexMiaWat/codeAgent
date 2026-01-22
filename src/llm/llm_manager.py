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
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

import yaml
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

# Загружаем переменные окружения (с перезаписью для обновления ключа)
load_dotenv(override=True)

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
        # Модели, которые уже нарушали JSON mode в рамках текущего процесса.
        # Используем для ускорения и снижения шума в логах: повторно не пробуем их для json_object.
        self._json_mode_blacklist: Set[str] = set()
        # Модели с ошибками недостатка кредитов (402) в рамках текущего процесса.
        # Используем для ускорения: повторно не пробуем их в рамках одного запроса.
        self._credits_error_blacklist: Set[str] = set()
        # Время последней проверки работоспособности моделей
        self._last_health_check: Optional[float] = None
        # Интервал проверки работоспособности (секунды)
        self._health_check_interval: float = 300.0  # 5 минут по умолчанию
        
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
        """Инициализация моделей из конфигурации с автоматическим выбором"""
        llm_config = self.config.get('llm', {})
        providers_config = self.config.get('providers', {})
        model_roles = llm_config.get('model_roles', {})

        # Получаем конфигурацию провайдера
        default_provider = llm_config.get('default_provider', 'openrouter')
        provider_config = providers_config.get(default_provider, {})
        provider_models = provider_config.get('models', {})

        # Собираем все доступные модели из конфигурации провайдера
        all_available_models = self._collect_all_models(provider_models)

        # Создаем модели с ролями
        assigned_models = set()  # Отслеживаем назначенные модели

        for role_name, model_names in model_roles.items():
            role = ModelRole(role_name)

            if model_names:  # Явно указанные модели
                for model_name in model_names:
                    if model_name in assigned_models:
                        logger.warning(f"Model {model_name} already assigned to another role, skipping for {role_name}")
                        continue

                    model_config_dict = self._find_model_config(model_name, provider_models)
                    if model_config_dict:
                        config_dict = {k: v for k, v in model_config_dict.items() if k != 'name'}
                        model_config = ModelConfig(
                            name=model_name,
                            role=role,
                            **config_dict
                        )
                        self.models[model_name] = model_config
                        assigned_models.add(model_name)
                    else:
                        logger.warning(f"Model {model_name} not found in provider config")
            else:
                # Автоматический выбор моделей для роли
                auto_selected = self._auto_select_models_for_role(role_name, all_available_models, assigned_models)
                for model_name in auto_selected:
                    model_config_dict = self._find_model_config(model_name, provider_models)
                    if model_config_dict:
                        config_dict = {k: v for k, v in model_config_dict.items() if k != 'name'}
                        model_config = ModelConfig(
                            name=model_name,
                            role=role,
                            **config_dict
                        )
                        self.models[model_name] = model_config
                        assigned_models.add(model_name)

        logger.info(f"Initialized {len(self.models)} models with automatic selection")
        self._log_model_assignment()

    def _collect_all_models(self, provider_models: Dict) -> List[str]:
        """Собрать все доступные модели из конфигурации провайдера"""
        all_models = []
        for provider_name, models_list in provider_models.items():
            if isinstance(models_list, list):
                for model in models_list:
                    if isinstance(model, dict) and 'name' in model:
                        all_models.append(model['name'])
        return all_models

    def _auto_select_models_for_role(self, role_name: str, all_models: List[str], assigned: Set[str]) -> List[str]:
        """Автоматический выбор моделей для роли"""
        available_models = [m for m in all_models if m not in assigned]

        if not available_models:
            logger.warning(f"No available models for automatic selection in role {role_name}")
            return []

        if role_name == 'primary':
            # Для primary выбираем 2-3 самые производительные модели
            # Предпочитаем модели с "wizard", "gpt", "claude" в имени
            priority_patterns = ['wizard', 'gpt', 'claude', 'llama-3']
            priority_models = []
            other_models = []

            for model in available_models:
                if any(pattern in model.lower() for pattern in priority_patterns):
                    priority_models.append(model)
                else:
                    other_models.append(model)

            selected = priority_models[:3] + other_models[:2]  # 3 приоритетных + 2 других
            logger.info(f"Auto-selected PRIMARY models: {selected}")
            return selected[:5]  # Максимум 5 моделей

        elif role_name == 'duplicate':
            # Для duplicate выбираем модели среднего класса
            # Избегаем слишком маленьких моделей (1b, mini) и слишком больших
            suitable = [m for m in available_models
                       if not any(x in m.lower() for x in ['1b', 'mini', 'small'])
                       and not any(x in m.lower() for x in ['70b', '72b', '405b'])]
            selected = suitable[:3]
            logger.info(f"Auto-selected DUPLICATE models: {selected}")
            return selected

        elif role_name == 'reserve':
            # Для reserve выбираем надежные модели с "free" в имени или известные стабильные
            reserve_patterns = ['free', 'stable', 'reliable', 'phi-3', 'llama-3.2-3b']
            reserve_models = [m for m in available_models
                            if any(pattern in m.lower() for pattern in reserve_patterns)]
            if not reserve_models:
                # Fallback: любые доступные модели
                reserve_models = available_models[:2]
            logger.info(f"Auto-selected RESERVE models: {reserve_models}")
            return reserve_models[:3]

        elif role_name == 'fallback':
            # Для fallback выбираем все оставшиеся модели
            selected = available_models[:5]
            logger.info(f"Auto-selected FALLBACK models: {selected}")
            return selected

        return []

    def _log_model_assignment(self):
        """Логирование распределения моделей по ролям"""
        role_counts = {}
        for model in self.models.values():
            role_name = model.role.value
            role_counts[role_name] = role_counts.get(role_name, 0) + 1

        logger.info("Model role distribution: " + ", ".join(f"{role}: {count}" for role, count in role_counts.items()))

        # Детальное логирование по ролям
        for role_name in ['primary', 'duplicate', 'reserve', 'fallback']:
            role_models = [m.name for m in self.models.values() if m.role.value == role_name]
            if role_models:
                logger.info(f"{role_name.upper()} models: {', '.join(role_models)}")
    
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
        
        # Создаем клиент для всех моделей провайдера
        # Всегда создаем новый клиент с актуальным ключом
        client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        self.clients[default_provider] = client
        
        logger.debug(f"Initialized {default_provider} client with API key: {api_key[:20]}...{api_key[-10:]}")
        
        logger.info(f"Initialized client for provider: {default_provider}")
    
    def get_primary_models(self) -> List[ModelConfig]:
        """Получить рабочие модели"""
        return [m for m in self.models.values() 
                if m.role == ModelRole.PRIMARY and m.enabled]
    
    def get_fallback_models(self) -> List[ModelConfig]:
        """
        Получить резервные модели в правильном порядке приоритета.
        Порядок: reserve → duplicate → fallback
        (reserve модели обычно более надежны и имеют больше кредитов)
        """
        # Собираем модели по ролям в правильном порядке приоритета
        reserve_models = [m for m in self.models.values() 
                         if m.role == ModelRole.RESERVE and m.enabled]
        duplicate_models = [m for m in self.models.values() 
                            if m.role == ModelRole.DUPLICATE and m.enabled]
        fallback_models = [m for m in self.models.values() 
                           if m.role == ModelRole.FALLBACK and m.enabled]
        
        # Возвращаем в порядке приоритета: reserve → duplicate → fallback
        return reserve_models + duplicate_models + fallback_models
    
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
        use_parallel: bool = False,
        response_format: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        """
        Генерация ответа через модель.
        ВАЖНО: Всегда возвращает ответ, никогда не падает с исключением.
        
        Args:
            prompt: Текст запроса
            model_name: Имя модели (если None - выбирается автоматически)
            use_fastest: Использовать самую быструю модель
            use_parallel: Использовать параллельное выполнение (best_of_two)
            response_format: Формат ответа (например, {"type": "json_object"} для JSON mode)
        
        Returns:
            ModelResponse с ответом модели (всегда успешный или с error, но не исключение)
        """
        # Периодическая проверка работоспособности моделей
        await self._periodic_health_check()
        
        # Очищаем blacklist кредитов в начале каждого нового запроса
        # (модели могли получить кредиты или изменилась ситуация)
        self._credits_error_blacklist.clear()
        
        llm_config = self.config.get('llm', {})
        strategy = llm_config.get('strategy', 'single')
        
        # Определяем стратегию использования
        # Для критичных запросов (JSON mode) используем best_of_two по умолчанию
        if response_format and response_format.get("type") == "json_object":
            # JSON mode - критичный запрос, используем best_of_two для надежности
            if not use_parallel and strategy != 'best_of_two':
                logger.debug("JSON mode запрос - используем best_of_two для надежности")
                use_parallel = True
        
        # Определяем стратегию использования
        if use_parallel or strategy == 'best_of_two':
            try:
                return await self._generate_parallel(prompt, response_format=response_format)
            except Exception as e:
                logger.error(f"Ошибка в parallel режиме, fallback на single: {e}")
                # Fallback на single режим
                return await self._generate_single(prompt, model_name, use_fastest, response_format=response_format)
        else:
            return await self._generate_single(prompt, model_name, use_fastest, response_format=response_format)
    
    async def _generate_single(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        use_fastest: bool = True,
        response_format: Optional[Dict[str, Any]] = None
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
        return await self._generate_with_fallback(prompt, model_config, response_format=response_format)
    
    async def _generate_with_fallback(
        self,
        prompt: str,
        primary_model: ModelConfig,
        response_format: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        max_retries: int = 2
    ) -> ModelResponse:
        """
        Генерация с fallback на резервные модели.
        ВАЖНО: Всегда возвращает ответ, даже если все модели упали (возвращает последний ответ или дефолтный).
        
        Args:
            prompt: Текст запроса
            primary_model: Основная модель для использования
            response_format: Формат ответа (JSON mode и т.д.)
            retry_count: Текущее количество попыток
            max_retries: Максимальное количество повторных попыток для JSON mode
        """
        models_to_try = [primary_model] + self.get_fallback_models()

        # Пропускаем модели с ошибками недостатка кредитов (402)
        if self._credits_error_blacklist:
            original_count = len(models_to_try)
            models_to_try = [m for m in models_to_try if m.name not in self._credits_error_blacklist]
            skipped_count = original_count - len(models_to_try)
            if skipped_count > 0:
                logger.info(
                    f"Пропущено {skipped_count} моделей с ошибками кредитов (402) "
                    f"(осталось {len(models_to_try)} моделей для попытки)"
                )

        # Если включен JSON mode, не пробуем модели, которые уже возвращали невалидный JSON
        if response_format and response_format.get("type") == "json_object" and self._json_mode_blacklist:
            original_count = len(models_to_try)
            models_to_try = [m for m in models_to_try if m.name not in self._json_mode_blacklist]
            skipped_count = original_count - len(models_to_try)
            if skipped_count > 0:
                logger.info(
                    f"JSON mode: пропущено {skipped_count} моделей из blacklist "
                    f"(осталось {len(models_to_try)} моделей для попытки)"
                )
        
        # Для JSON mode - приоритет более качественным моделям (не самым быстрым)
        # Сортируем модели: сначала те, которые не в blacklist и имеют хорошую статистику
        if response_format and response_format.get("type") == "json_object":
            def model_priority(model: ModelConfig) -> tuple:
                # Приоритет: не в blacklist, высокая успешность, меньше ошибок
                in_blacklist = 1 if model.name in self._json_mode_blacklist else 0
                total = model.success_count + model.error_count
                success_rate = model.success_count / total if total > 0 else 0.5
                return (in_blacklist, -success_rate, model.error_count)
            
            models_to_try = sorted(models_to_try, key=model_priority)
            logger.debug(f"JSON mode: модели отсортированы по приоритету (лучшие первыми)")
        
        # Сохраняем последний ответ (даже если он failed) для fallback
        last_response: Optional[ModelResponse] = None
        invalid_json_responses: List[ModelResponse] = []  # Сохраняем ответы с невалидным JSON
        attempt_number = 0  # Счетчик попыток для наглядного логирования
        
        for model_config in models_to_try:
            attempt_number += 1
            total_attempts = len(models_to_try)
            
            # Логируем начало попытки
            logger.info(f"🔄 Попытка {attempt_number}/{total_attempts}: модель {model_config.name}")
            
            try:
                response = await self._call_model(prompt, model_config, response_format=response_format)
                last_response = response  # Сохраняем для возможного использования
                
                if response.success:
                    # Если запрашивался JSON mode, проверяем что ответ действительно JSON
                    if response_format and response_format.get("type") == "json_object":
                        if self._validate_json_response(response.content):
                            logger.info(
                                f"✅ Попытка {attempt_number}/{total_attempts} УСПЕШНА: "
                                f"модель {model_config.name} вернула валидный JSON "
                                f"(время: {response.response_time:.2f}s)"
                            )
                            # Очищаем blacklist кредитов после успешного запроса
                            # (модели могли получить кредиты или ситуация изменилась)
                            self._credits_error_blacklist.clear()
                            return response
                        else:
                            logger.warning(
                                f"❌ Попытка {attempt_number}/{total_attempts} НЕУДАЧНА: "
                                f"модель {model_config.name} вернула невалидный JSON в JSON mode. "
                                f"Content: {response.content[:200]}... Пробуем следующую модель."
                            )
                            # Запоминаем модель как проблемную для JSON mode
                            self._json_mode_blacklist.add(model_config.name)
                            logger.info(
                                f"⚠️ Модель {model_config.name} добавлена в JSON mode blacklist "
                                f"(всего в blacklist: {len(self._json_mode_blacklist)} моделей: {', '.join(self._json_mode_blacklist)})"
                            )
                            model_config.error_count += 1
                            invalid_json_responses.append(response)  # Сохраняем для возможного использования
                            continue
                    else:
                        # Не JSON mode - просто возвращаем успешный ответ
                        logger.info(
                            f"✅ Попытка {attempt_number}/{total_attempts} УСПЕШНА: "
                            f"модель {model_config.name} вернула успешный ответ "
                            f"(время: {response.response_time:.2f}s)"
                        )
                        # Очищаем blacklist кредитов после успешного запроса
                        # (модели могли получить кредиты или ситуация изменилась)
                        self._credits_error_blacklist.clear()
                        return response
                else:
                    # Проверяем, является ли это ошибкой недостатка кредитов (402)
                    error_str = str(response.error) if response.error else ""
                    is_credits_error = "402" in error_str or "credits" in error_str.lower() or "afford" in error_str.lower()
                    
                    if is_credits_error:
                        logger.warning(
                            f"❌ Попытка {attempt_number}/{total_attempts} НЕУДАЧНА: "
                            f"модель {model_config.name} failed: недостаток кредитов (402). "
                            f"Добавляем в blacklist для этого запроса."
                        )
                        self._credits_error_blacklist.add(model_config.name)
                    else:
                        logger.warning(
                            f"❌ Попытка {attempt_number}/{total_attempts} НЕУДАЧНА: "
                            f"модель {model_config.name} failed: {response.error}"
                        )
                    model_config.error_count += 1
            except Exception as e:
                error_str = str(e)
                is_credits_error = "402" in error_str or "credits" in error_str.lower() or "afford" in error_str.lower()
                
                if is_credits_error:
                    logger.error(
                        f"❌ Попытка {attempt_number}/{total_attempts} ОШИБКА: "
                        f"модель {model_config.name} - недостаток кредитов (402): {e}. "
                        f"Добавляем в blacklist для этого запроса."
                    )
                    self._credits_error_blacklist.add(model_config.name)
                else:
                    logger.error(
                        f"❌ Попытка {attempt_number}/{total_attempts} ОШИБКА: "
                        f"ошибка вызова модели {model_config.name}: {e}"
                    )
                model_config.error_count += 1
                # Создаем failed response для этого исключения
                last_response = ModelResponse(
                    model_name=model_config.name,
                    content="",
                    response_time=0.0,
                    success=False,
                    error=str(e)
                )
                continue
        
        # КРИТИЧНО: Если это JSON mode и все модели вернули невалидный JSON - используем агрессивную стратегию
        if response_format and response_format.get("type") == "json_object" and invalid_json_responses:
            logger.error(
                f"🚨 КРИТИЧЕСКАЯ СИТУАЦИЯ: Все {len(invalid_json_responses)} модели вернули невалидный JSON в JSON mode! "
                f"Используем агрессивную стратегию восстановления..."
            )
            
            # Стратегия 1: Попробовать best_of_two с другими моделями
            if retry_count < max_retries:
                logger.info(f"Попытка {retry_count + 1}/{max_retries}: Переключаемся на best_of_two режим...")
                try:
                    parallel_response = await self._generate_parallel(prompt, response_format=response_format)
                    if parallel_response.success and self._validate_json_response(parallel_response.content):
                        logger.info(f"✓ Best_of_two режим успешно вернул валидный JSON от {parallel_response.model_name}")
                        return parallel_response
                except Exception as e:
                    logger.warning(f"Best_of_two режим также не помог: {e}")
            
            # Стратегия 2: Попробовать извлечь JSON из лучшего ответа с невалидным JSON
            if invalid_json_responses:
                logger.info("Пытаемся извлечь JSON из ответов с невалидным JSON...")
                for invalid_resp in invalid_json_responses[:3]:  # Пробуем первые 3
                    extracted_json = self._extract_json_from_text(invalid_resp.content)
                    if extracted_json:
                        logger.info(f"✓ Удалось извлечь JSON из ответа модели {invalid_resp.model_name}")
                        return ModelResponse(
                            model_name=invalid_resp.model_name,
                            content=extracted_json,
                            response_time=invalid_resp.response_time,
                            success=True
                        )
        
        # Все модели провалились - возвращаем последний ответ или создаем дефолтный
        if last_response:
            logger.warning(
                f"⚠️ Все модели провалились для JSON mode, возвращаем последний ответ от {last_response.model_name}. "
                f"Ошибка: {last_response.error or 'Invalid JSON'}"
            )
            # Пытаемся извлечь хоть какой-то контент из последнего ответа (даже если он failed)
            if last_response.content:
                logger.info(f"Используем контент из последнего ответа: {last_response.content[:200]}...")
                # Если это JSON mode, пытаемся извлечь JSON из текста
                if response_format and response_format.get("type") == "json_object":
                    extracted_json = self._extract_json_from_text(last_response.content)
                    if extracted_json:
                        logger.info(f"✓ Удалось извлечь JSON из текстового ответа модели {last_response.model_name}")
                        # Возвращаем успешный ответ с извлеченным JSON
                        return ModelResponse(
                            model_name=last_response.model_name,
                            content=extracted_json,
                            response_time=last_response.response_time,
                            success=True
                        )
                    # Если не нашли JSON, пытаемся создать дефолтный на основе текста
                    logger.warning(
                        f"Не удалось извлечь JSON из ответа модели {last_response.model_name}. "
                        f"Используем дефолтный ответ."
                    )
                else:
                    # Не JSON mode - возвращаем как есть
                    return last_response
        
        # Если даже последнего ответа нет - создаем дефолтный ответ
        logger.error(
            f"КРИТИЧЕСКАЯ СИТУАЦИЯ: Все модели провалились и нет даже последнего ответа. "
            f"Пробовали {len(models_to_try)} моделей. JSON mode blacklist: {len(self._json_mode_blacklist)} моделей"
        )
        fallback_response = ModelResponse(
            model_name="fallback",
            content='{"error": "Все модели недоступны", "matches": false, "reason": "Техническая ошибка"}',
            response_time=0.0,
            success=False,
            error="All models failed to generate response"
        )
        logger.info(f"Возвращаем дефолтный fallback ответ: {fallback_response.content}")
        return fallback_response
    
    def _validate_json_response(self, content: str) -> bool:
        """
        Проверяет что ответ является валидным JSON объектом
        
        Args:
            content: Содержимое ответа модели
        
        Returns:
            True если ответ валидный JSON объект, False иначе
        """
        if not content or not content.strip():
            return False
        
        import json
        import re
        
        text = content.strip()
        
        # Убираем markdown code fences если есть
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()
        
        # Пытаемся распарсить как JSON
        try:
            decoder = json.JSONDecoder()
            # Ищем первый валидный JSON объект
            for i, ch in enumerate(text):
                if ch not in "{[":
                    continue
                try:
                    obj, _end = decoder.raw_decode(text[i:])
                    # Проверяем что это объект (dict), а не массив
                    if isinstance(obj, dict):
                        return True
                except json.JSONDecodeError:
                    continue
            
            # Последняя попытка - прямой парсинг всего текста
            obj = json.loads(text)
            return isinstance(obj, dict)
        except json.JSONDecodeError:
            return False
    
    async def _generate_parallel(
        self, 
        prompt: str,
        response_format: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
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
            return await self._generate_single(prompt, response_format=response_format)
        
        # Используем первые две модели
        model1, model2 = parallel_models[0], parallel_models[1]
        
        # Таймаут для параллельной обработки
        parallel_timeout = parallel_config.get('parallel_timeout', 90)  # 90 секунд по умолчанию

        try:
            # Генерируем ответы параллельно с таймаутом
            responses = await asyncio.wait_for(
                asyncio.gather(
                    self._call_model(prompt, model1, response_format=response_format),
                    self._call_model(prompt, model2, response_format=response_format),
                    return_exceptions=True
                ),
                timeout=parallel_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Parallel generation timeout after {parallel_timeout}s")
            # Fallback на single режим
            return await self._generate_single(prompt, response_format=response_format)
        
        # Обрабатываем результаты
        valid_responses = []
        for resp in responses:
            if isinstance(resp, Exception):
                logger.error(f"Parallel generation error: {resp}")
                continue
            if resp.success:
                # Если запрашивался JSON mode, проверяем что ответ действительно JSON
                if response_format and response_format.get("type") == "json_object":
                    if self._validate_json_response(resp.content):
                        valid_responses.append(resp)
                    else:
                        logger.warning(
                            f"Model {resp.model_name} returned invalid JSON in parallel mode. "
                            f"Content: {resp.content[:200]}..."
                        )
                        # Запоминаем модель как проблемную для JSON mode
                        self._json_mode_blacklist.add(resp.model_name)
                else:
                    # Не JSON mode - просто добавляем успешный ответ
                    valid_responses.append(resp)
        
        if not valid_responses:
            # Обе модели провалились или вернули невалидный JSON - используем fallback
            # Fallback теперь гарантированно вернет ответ (не упадет)
            return await self._generate_with_fallback(prompt, model1, response_format=response_format)
        
        if len(valid_responses) == 1:
            # Только одна модель сработала и вернула валидный ответ
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
            logger.warning(f"Evaluator model '{evaluator_model_name}' not found, using fallback selection")
            # Fallback: возвращаем ответ с минимальным временем ответа
            return min(responses, key=lambda r: r.response_time)

        evaluator_config = self.models[evaluator_model_name]

        # Оцениваем каждый ответ с таймаутом и обработкой ошибок
        evaluation_timeout = parallel_config.get('evaluation_timeout', 30)  # 30 секунд по умолчанию
        scores = []

        for i, response in enumerate(responses):
            try:
                # Добавляем таймаут для оценки
                import asyncio
                score = await asyncio.wait_for(
                    self._evaluate_response(prompt, response.content, evaluator_config),
                    timeout=evaluation_timeout
                )
                response.score = score
                scores.append(score)
                logger.debug(f"Response {i+1} from {response.model_name} scored: {score}")
            except asyncio.TimeoutError:
                logger.warning(f"Evaluation timeout for response {i+1} from {response.model_name}")
                response.score = 3.0  # Низкая оценка при таймауте
                scores.append(3.0)
            except Exception as e:
                logger.error(f"Evaluation error for response {i+1} from {response.model_name}: {e}")
                response.score = 3.0  # Низкая оценка при ошибке
                scores.append(3.0)

        # Проверяем на противоречивые оценки
        if len(scores) >= 2:
            score_range = max(scores) - min(scores)
            selection_criteria = parallel_config.get('selection_criteria', ['quality'])

            if score_range < 1.0 and 'quality' in selection_criteria:
                # Оценки близкие - используем дополнительные критерии
                logger.info(f"Scores are close (range: {score_range}), using additional criteria")

                # Критерий 1: Время ответа (быстрее = лучше, если качество сопоставимое)
                if 'efficiency' in selection_criteria:
                    best_response = min(responses, key=lambda r: r.response_time)
                    logger.info(f"Selected by efficiency: {best_response.model_name} ({best_response.response_time:.2f}s)")
                    return best_response

                # Критерий 2: Длина ответа (более полный ответ, если качество сопоставимое)
                if 'completeness' in selection_criteria:
                    best_response = max(responses, key=lambda r: len(r.content))
                    logger.info(f"Selected by completeness: {best_response.model_name} ({len(best_response.content)} chars)")
                    return best_response

        # Стандартный выбор: максимальный score
        best_response = max(responses, key=lambda r: r.score or 0.0)

        logger.info(f"Selected best response from {best_response.model_name} (score: {best_response.score})")
        return best_response
    
    async def _evaluate_response(
        self,
        prompt: str,
        response: str,
        evaluator_model: ModelConfig
    ) -> float:
        """Оценка ответа моделью-оценщиком с улучшенной обработкой ошибок"""
        # Валидация входных данных
        if not prompt or not response:
            logger.warning("Empty prompt or response for evaluation")
            return 3.0  # Низкая оценка для пустых ответов

        if len(response) < 10:
            logger.warning(f"Response too short for evaluation: {len(response)} chars")
            return 2.0  # Низкая оценка для слишком коротких ответов

        evaluation_prompt = f"""Оцени качество ответа на запрос.

Запрос: {prompt}

Ответ: {response}

Оцени ответ по шкале от 0 до 10, где:
- 0-3: Плохой ответ (не релевантный, неполный, содержит ошибки)
- 4-6: Средний ответ (частично релевантный, неполный)
- 7-9: Хороший ответ (релевантный, полный, без грубых ошибок)
- 10: Отличный ответ (полностью релевантный, полный, качественный, полезный)

Требования к оценке:
- Фокус на релевантности, полноте и качестве
- Штраф за неточности, нерелевантную информацию
- Бонус за полезность и практичность

Ответь только числом от 0 до 10."""

        try:
            eval_response = await self._call_model(evaluation_prompt, evaluator_model)

            if not eval_response.success:
                logger.warning(f"Evaluation model call failed: {eval_response.error}")
                return 4.0  # Средняя оценка при неудаче вызова

            if not eval_response.content or len(eval_response.content.strip()) < 1:
                logger.warning("Empty evaluation response")
                return 4.0  # Средняя оценка при пустом ответе оценщика

            # Извлекаем число из ответа с улучшенной логикой
            import re
            # Ищем числа в начале строки или после двоеточия
            content = eval_response.content.strip()

            # Паттерн 1: число в начале строки
            start_number = re.match(r'^(\d+\.?\d*)', content)
            if start_number:
                try:
                    score = float(start_number.group(1))
                    return min(max(score, 0.0), 10.0)
                except ValueError:
                    pass

            # Паттерн 2: число после "оценка:", "score:" и т.п.
            colon_pattern = re.search(r'(?:оценка|score|rating)[\s:]*(\d+\.?\d*)', content, re.IGNORECASE)
            if colon_pattern:
                try:
                    score = float(colon_pattern.group(1))
                    return min(max(score, 0.0), 10.0)
                except ValueError:
                    pass

            # Паттерн 3: любое число от 0 до 10
            all_numbers = re.findall(r'\b(\d+\.?\d*)\b', content)
            valid_scores = [float(n) for n in all_numbers if 0 <= float(n) <= 10]
            if valid_scores:
                return max(valid_scores)  # Берем максимальную валидную оценку

            # Если не нашли число, анализируем текстовый ответ
            content_lower = content.lower()
            if any(word in content_lower for word in ['отлично', 'excellent', 'perfect', '10']):
                return 10.0
            elif any(word in content_lower for word in ['хорошо', 'good', 'great', '8', '9']):
                return 8.0
            elif any(word in content_lower for word in ['удовлетворительно', 'satisfactory', 'ok', '5', '6', '7']):
                return 6.0
            elif any(word in content_lower for word in ['плохо', 'bad', 'poor', '1', '2', '3']):
                return 2.0

            logger.warning(f"Could not parse evaluation response: '{content[:100]}...'")
            return 5.0  # Средняя оценка при неудаче парсинга

        except Exception as e:
            logger.error(f"Error evaluating response: {e}", exc_info=True)
            return 5.0  # Средняя оценка по умолчанию при ошибке
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Агрессивное извлечение JSON из текста.
        Использует несколько методов для поиска JSON объекта.
        
        Args:
            text: Текст для извлечения JSON
            
        Returns:
            JSON строка если найден, None иначе
        """
        if not text:
            return None
        
        import json
        import re
        
        # Метод 1: Стандартное извлечение через _validate_json_response логику
        text_clean = text.strip()
        if text_clean.startswith("```"):
            text_clean = re.sub(r"^```(?:json)?\s*", "", text_clean, flags=re.IGNORECASE)
            text_clean = re.sub(r"\s*```$", "", text_clean)
            text_clean = text_clean.strip()
        
        # Метод 2: Поиск JSON объекта через regex
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Простой объект
            r'\{"usefulness_percent"[^}]*\}',  # Специфичный паттерн для usefulness
            r'\{"matches"[^}]*\}',  # Специфичный паттерн для matches
        ]
        
        for pattern in json_patterns:
            matches = re.finditer(pattern, text_clean, re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group()
                    # Пытаемся распарсить
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        # Возвращаем валидный JSON
                        return json.dumps(parsed, ensure_ascii=False)
                except json.JSONDecodeError:
                    continue
        
        # Метод 3: Прямой парсинг всего текста
        try:
            parsed = json.loads(text_clean)
            if isinstance(parsed, dict):
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        
        return None
    
    async def _periodic_health_check(self):
        """
        Периодическая проверка работоспособности моделей.
        Вызывается автоматически перед каждым запросом, но выполняет проверку только раз в интервал.
        """
        current_time = time.time()
        
        # Проверяем, нужно ли выполнять health check
        if self._last_health_check is None:
            self._last_health_check = current_time
            # Первый запуск - выполняем проверку
            await self._health_check_models()
            return
        
        # Проверяем интервал
        if current_time - self._last_health_check >= self._health_check_interval:
            self._last_health_check = current_time
            await self._health_check_models()
    
    async def _health_check_models(self):
        """
        Проверка работоспособности всех моделей.
        Отключает модели с высоким процентом ошибок.
        """
        logger.debug("Выполняется проверка работоспособности моделей...")
        
        total_models = len(self.models)
        disabled_count = 0
        
        for model_name, model_config in self.models.items():
            if not model_config.enabled:
                continue
            
            # Вычисляем процент успешности
            total_requests = model_config.success_count + model_config.error_count
            if total_requests == 0:
                continue  # Модель еще не использовалась
            
            success_rate = model_config.success_count / total_requests if total_requests > 0 else 0.0
            
            # Если процент успешности ниже 30% и было больше 5 запросов - отключаем модель
            if success_rate < 0.3 and total_requests >= 5:
                logger.warning(
                    f"Модель {model_name} отключена из-за низкой успешности: "
                    f"{success_rate*100:.1f}% ({model_config.success_count}/{total_requests})"
                )
                model_config.enabled = False
                disabled_count += 1
            # Если процент успешности выше 70% и модель была отключена - включаем обратно
            elif success_rate >= 0.7 and not model_config.enabled and total_requests >= 3:
                logger.info(
                    f"Модель {model_name} включена обратно: "
                    f"успешность {success_rate*100:.1f}% ({model_config.success_count}/{total_requests})"
                )
                model_config.enabled = True
        
        if disabled_count > 0:
            logger.info(f"Проверка завершена: отключено {disabled_count} из {total_models} моделей")
        
        # Проверяем что осталась хотя бы одна рабочая модель
        enabled_models = [m for m in self.models.values() if m.enabled]
        if not enabled_models:
            logger.error("КРИТИЧЕСКАЯ СИТУАЦИЯ: Все модели отключены! Включаем все обратно...")
            for model_config in self.models.values():
                model_config.enabled = True
                model_config.error_count = 0  # Сбрасываем счетчик ошибок
    
    async def _call_model(
        self, 
        prompt: str, 
        model_config: ModelConfig,
        response_format: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        """Вызов модели для генерации ответа"""
        start_time = time.time()
        
        try:
            # Получаем клиент (пока только openrouter)
            client = list(self.clients.values())[0]
            
            # Формируем параметры запроса
            request_params = {
                "model": model_config.name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": model_config.max_tokens,
                "temperature": model_config.temperature,
                "top_p": model_config.top_p
            }
            
            # Добавляем response_format если указан (для JSON mode)
            if response_format:
                request_params["response_format"] = response_format
            
            response = await client.chat.completions.create(**request_params)
            
            response_time = time.time() - start_time
            
            # Проверяем что ответ содержит choices
            if not response.choices or len(response.choices) == 0:
                raise ValueError("Empty choices in API response")
            
            # Некоторые провайдеры/модели могут вернуть None в message.content
            message = response.choices[0].message
            if message is None:
                raise ValueError("Message is None in API response")
            
            content = (message.content or "").strip()
            
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
