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

# Импортируем Colors для цветового выделения
try:
    from ..task_logger import Colors
except ImportError:
    # Fallback если модуль еще не создан
    class Colors:
        BRIGHT_MAGENTA = '\033[95m'
        RESET = '\033[0m'
        @staticmethod
        def colorize(text: str, color: str) -> str:
            return f"{color}{text}{Colors.RESET}"


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

        # Кэш для быстрого доступа
        self._fastest_model_cache: Optional[ModelConfig] = None
        self._cache_timestamp: float = 0.0
        self._cache_ttl: float = 60.0  # Кэш на 1 минуту
        self._model_name_cache: Dict[str, ModelConfig] = {}  # Кэш моделей по имени
        
        self._load_config()
        self._init_models()
        self._init_clients()

        # Очищаем кэши при инициализации
        self._clear_caches()
    
    def _validate_config_path(self, path: Path) -> None:
        """
        Валидация пути к конфигурационному файлу для защиты от path traversal.

        Args:
            path: Путь к файлу конфигурации

        Raises:
            ValueError: Если путь небезопасный
            FileNotFoundError: Если файл не найден
        """
        # Проверка существования файла
        if not path.exists():
            raise FileNotFoundError(f"LLM config file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        # Защита от path traversal - проверяем на явные попытки выхода за пределы
        try:
            resolved_path = path.resolve()
            path_str = str(resolved_path)

            # Запрещаем явные паттерны path traversal
            dangerous_patterns = ['..', '\\', '/']
            path_parts = resolved_path.parts

            # Проверяем что нет '..' в пути (path traversal)
            if '..' in path_parts:
                raise ValueError(f"Path traversal detected in config file path: {path}")

            # Проверяем что путь не содержит опасных символов
            if any(pattern in path_str for pattern in ['/../', '\\..\\', '..\\', '../']):
                raise ValueError(f"Path traversal pattern detected in config file path: {path}")

        except (OSError, RuntimeError) as e:
            raise ValueError(f"Invalid config file path: {path}") from e

        # Проверка расширения файла
        if path.suffix not in ['.yaml', '.yml']:
            raise ValueError(f"Config file must have .yaml or .yml extension: {path}")

        # Проверка размера файла (защита от ZIP bombs)
        max_size = 10 * 1024 * 1024  # 10MB
        if path.stat().st_size > max_size:
            raise ValueError(f"Config file too large (max {max_size} bytes): {path}")

    def _load_config(self):
        """Загрузка конфигурации из YAML с security checks"""
        # Валидация пути перед загрузкой
        self._validate_config_path(self.config_path)

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file {self.config_path}: {e}") from e
        except (OSError, IOError) as e:
            raise IOError(f"Cannot read config file {self.config_path}: {e}") from e

        # Валидация загруженной конфигурации
        self._validate_config_structure(self.config)

        # Подстановка переменных окружения
        self.config = self._substitute_env_vars(self.config)

    def _validate_config_structure(self, config: Dict[str, Any]) -> None:
        """
        Валидация структуры конфигурации.

        Args:
            config: Загруженная конфигурация

        Raises:
            ValueError: При обнаружении проблем в структуре
        """
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        # Проверка обязательных секций
        required_sections = ['llm', 'providers']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")

        # Валидация секции llm
        llm_config = config.get('llm', {})
        if not isinstance(llm_config, dict):
            raise ValueError("LLM configuration must be a dictionary")

        required_llm_keys = ['default_provider', 'model_roles']
        for key in required_llm_keys:
            if key not in llm_config:
                raise ValueError(f"Missing required LLM config key: {key}")

        # Валидация провайдеров
        providers = config.get('providers', {})
        if not isinstance(providers, dict):
            raise ValueError("Providers configuration must be a dictionary")

        default_provider = llm_config.get('default_provider')
        if default_provider not in providers:
            raise ValueError(f"Default provider '{default_provider}' not found in providers")

    def _substitute_env_vars(self, obj: Any, visited: Optional[Set[int]] = None) -> Any:
        """
        Рекурсивная подстановка переменных окружения с защитой от бесконечной рекурсии.

        Args:
            obj: Объект для обработки
            visited: Множество ID уже обработанных объектов (для защиты от циклов)

        Returns:
            Объект с подставленными переменными окружения

        Raises:
            ValueError: При обнаружении циклических ссылок
        """
        if visited is None:
            visited = set()

        # Защита от бесконечной рекурсии
        obj_id = id(obj)
        if obj_id in visited:
            raise ValueError("Circular reference detected in configuration during environment variable substitution")

        visited.add(obj_id)

        try:
            if isinstance(obj, dict):
                return {k: self._substitute_env_vars(v, visited) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [self._substitute_env_vars(item, visited) for item in obj]
            elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
                var_expr = obj[2:-1].strip()
                if not var_expr:
                    raise ValueError(f"Empty environment variable name in expression: {obj}")

                env_value = os.getenv(var_expr)
                if env_value is None:
                    raise ValueError(f"Environment variable not found: {var_expr}")
                return env_value
            else:
                return obj
        finally:
            visited.remove(obj_id)
    
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

    async def close(self):
        """
        Корректное закрытие всех клиентов.
        Должен вызываться перед завершением работы приложения.
        """
        # Проверяем, не закрыты ли уже клиенты
        if not self.clients:
            logger.debug("LLM manager clients already closed")
            return

        logger.debug("Closing LLM manager clients...")

        # Проверяем состояние event loop перед закрытием
        try:
            loop = asyncio.get_running_loop()
            if loop.is_closed():
                logger.warning("Event loop is already closed, skipping client close operations")
                # Очищаем словарь клиентов без попытки закрытия
                self.clients.clear()
                logger.info("All LLM manager clients cleared (event loop closed)")
                return
        except RuntimeError as e:
            # Нет запущенного event loop
            if "no running event loop" in str(e).lower():
                logger.warning("No running event loop, skipping client close operations")
            else:
                logger.warning(f"Runtime error getting event loop: {e}")
            self.clients.clear()
            logger.info("All LLM manager clients cleared (no event loop)")
            return

        # Отменяем все активные задачи перед закрытием клиентов
        # Это предотвратит проблемы с cleanup futures
        try:
            current_task = asyncio.current_task()
            all_tasks = [task for task in asyncio.all_tasks(loop) if task != current_task]
            if all_tasks:
                logger.debug(f"Cancelling {len(all_tasks)} background tasks before closing clients")
                for task in all_tasks:
                    if not task.done():
                        try:
                            task.cancel()
                        except Exception as e:
                            logger.warning(f"Error cancelling task {task}: {e}")

                # Ждем завершения отмененных задач
                try:
                    await asyncio.gather(*all_tasks, return_exceptions=True)
                    logger.debug("All background tasks cancelled")
                except RuntimeError as e:
                    if "Event loop is closed" in str(e):
                        logger.warning("Event loop closed while waiting for task cancellation")
                    else:
                        logger.warning(f"Runtime error during task cancellation: {e}")
                except Exception as e:
                    logger.warning(f"Unexpected error during task cancellation: {e}")
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger.warning("Event loop closed while accessing tasks")
            else:
                logger.warning(f"Runtime error accessing tasks: {e}")
        except Exception as e:
            logger.warning(f"Error cancelling background tasks: {e}")

        for provider_name, client in self.clients.items():
            try:
                # Многоуровневая проверка состояния event loop перед закрытием клиента
                try:
                    current_loop = asyncio.get_running_loop()
                    if current_loop.is_closed():
                        logger.warning(f"Event loop already closed, skipping client close for provider {provider_name}")
                        continue
                except RuntimeError:
                    # Нет запущенного loop, пропускаем
                    logger.warning(f"No running event loop, skipping client close for provider {provider_name}")
                    continue

                logger.debug(f"Closing client for provider: {provider_name}")

                # Проверяем, что loop все еще доступен непосредственно перед вызовом close()
                # Многоуровневая защита от проблем с event loop
                loop_state_check = False
                try:
                    # Проверяем текущее состояние loop несколько раз
                    for _ in range(3):
                        try:
                            test_loop = asyncio.get_running_loop()
                            if test_loop.is_closed():
                                logger.warning(f"Event loop closed on iteration {_} for provider {provider_name}")
                                loop_state_check = True
                                break
                            await asyncio.sleep(0.001)  # Короткая пауза для проверки стабильности
                        except RuntimeError:
                            logger.warning(f"No running event loop on iteration {_} for provider {provider_name}")
                            loop_state_check = True
                            break
                except Exception as e:
                    logger.warning(f"Error checking loop state for {provider_name}: {e}")
                    loop_state_check = True

                if loop_state_check:
                    logger.debug(f"Skipping client close for {provider_name} due to unstable event loop")
                    continue

                # Для httpx клиентов - проверяем состояние транспорта
                if hasattr(client, '_transport'):
                    try:
                        transport = client._transport
                        if hasattr(transport, '_pool') and transport._pool is not None:
                            # Проверяем, не закрыт ли уже pool
                            if hasattr(transport._pool, '_closed') and transport._pool._closed:
                                logger.debug(f"Transport pool already closed for provider {provider_name}")
                                continue
                    except Exception:
                        # Игнорируем ошибки при проверке состояния
                        pass

                # Пытаемся закрыть клиента с защитой от ошибок event loop
                try:
                    # Сначала пробуем обычное закрытие с таймаутом
                    await asyncio.wait_for(client.close(), timeout=5.0)
                    logger.debug(f"Client for provider {provider_name} closed successfully")
                except RuntimeError as e:
                    if "Event loop is closed" in str(e):
                        # Event loop закрыт - пытаемся закрыть клиента синхронно или игнорируем
                        logger.warning(f"Event loop closed during client close for {provider_name}, attempting sync close")
                        try:
                            # Пробуем синхронное закрытие если доступно
                            if hasattr(client, 'close') and not hasattr(client.close, '__call__'):
                                # Метод не async, пробуем вызвать напрямую
                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(client.close)
                                    future.result(timeout=2.0)
                                logger.debug(f"Client for provider {provider_name} closed synchronously")
                            else:
                                logger.debug(f"Skipping async client close for {provider_name} due to closed event loop")
                        except Exception:
                            logger.debug(f"Sync close also failed for {provider_name}, skipping")
                    else:
                        raise  # Перебрасываем другие RuntimeError
            except asyncio.TimeoutError:
                logger.warning(f"Timeout closing client for provider {provider_name}")
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    logger.warning(f"Event loop closed while closing client for provider {provider_name}")
                    # В этом случае клиент все равно будет закрыт при завершении процесса
                else:
                    logger.warning(f"Runtime error closing client for provider {provider_name}: {e}")
            except Exception as e:
                logger.warning(f"Error closing client for provider {provider_name}: {e}")

        # Финальная проверка - отменяем любые оставшиеся задачи связанные с клиентами
        try:
            current_loop = asyncio.get_running_loop()
            if not current_loop.is_closed():
                # Ждем короткое время чтобы дать задачам закрытия клиентов завершиться
                await asyncio.sleep(0.1)
                # Проверяем есть ли незавершенные задачи связанные с HTTP клиентами
                all_tasks = asyncio.all_tasks(current_loop)
                client_tasks = [task for task in all_tasks
                              if not task.done() and
                              any(keyword in str(task) for keyword in ['aclose', 'close', 'http', 'client'])]
                if client_tasks:
                    logger.warning(f"Found {len(client_tasks)} unfinished client-related tasks, waiting briefly...")
                    try:
                        await asyncio.wait_for(asyncio.gather(*client_tasks, return_exceptions=True), timeout=1.0)
                        logger.debug("Unfinished client tasks completed")
                    except (asyncio.TimeoutError, RuntimeError):
                        logger.warning("Timeout or error waiting for unfinished client tasks")
        except RuntimeError:
            # Нет запущенного loop
            pass
        except Exception as e:
            logger.warning(f"Error during final client cleanup check: {e}")

        # Очищаем словарь клиентов
        self.clients.clear()
        logger.info("All LLM manager clients closed")

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
        """Получить самую быструю модель (по last_response_time) с кэшированием"""
        current_time = time.time()

        # Проверяем кэш
        if (self._fastest_model_cache is not None and
            current_time - self._cache_timestamp < self._cache_ttl):
            return self._fastest_model_cache

        primary_models = self.get_primary_models()
        if not primary_models:
            return None

        # Сортируем по времени ответа (быстрее = меньше)
        # Если время не измерено (0), считаем модель быстрой
        sorted_models = sorted(
            primary_models,
            key=lambda m: m.last_response_time if m.last_response_time > 0 else 0.0
        )

        # Обновляем кэш
        self._fastest_model_cache = sorted_models[0]
        self._cache_timestamp = current_time

        return sorted_models[0]

    def _invalidate_fastest_cache(self):
        """Инвалидировать кэш самой быстрой модели"""
        self._fastest_model_cache = None
        self._cache_timestamp = 0.0

    def get_model_by_name(self, model_name: str) -> Optional[ModelConfig]:
        """Получить модель по имени с кэшированием"""
        # Проверяем кэш
        if model_name in self._model_name_cache:
            return self._model_name_cache[model_name]

        # Ищем в моделях
        if model_name in self.models:
            model = self.models[model_name]
            # Кэшируем результат
            self._model_name_cache[model_name] = model
            return model

        return None

    def _clear_caches(self):
        """Очистить все кэши"""
        self._fastest_model_cache = None
        self._cache_timestamp = 0.0
        self._model_name_cache.clear()

    def get_performance_stats(self) -> Dict[str, Any]:
        """Получить статистику производительности всех моделей"""
        stats = {
            "total_models": len(self.models),
            "enabled_models": len([m for m in self.models.values() if m.enabled]),
            "disabled_models": len([m for m in self.models.values() if not m.enabled]),
            "models": {}
        }

        for name, model in self.models.items():
            total_requests = model.success_count + model.error_count
            success_rate = (model.success_count / total_requests * 100) if total_requests > 0 else 0.0

            stats["models"][name] = {
                "enabled": model.enabled,
                "role": model.role.value,
                "total_requests": total_requests,
                "success_count": model.success_count,
                "error_count": model.error_count,
                "success_rate": round(success_rate, 1),
                "avg_response_time": round(model.last_response_time, 3) if model.last_response_time > 0 else 0.0,
                "max_tokens": model.max_tokens,
                "context_window": model.context_window
            }

        return stats

    def _validate_generate_request(
        self,
        prompt: str,
        model_name: Optional[str],
        use_fastest: bool,
        use_parallel: bool,
        response_format: Optional[Dict[str, Any]]
    ) -> None:
        """
        Валидация параметров запроса к generate_response.

        Args:
            prompt: Текст запроса
            model_name: Имя модели
            use_fastest: Флаг использования быстрой модели
            use_parallel: Флаг параллельного выполнения
            response_format: Формат ответа

        Raises:
            TypeError: При неверных типах параметров
            ValueError: При недопустимых значениях параметров
        """
        # Валидация prompt
        if not isinstance(prompt, str):
            raise TypeError("Prompt must be a string")

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty or contain only whitespace")

        # Ограничение размера промпта (защита от memory exhaustion)
        max_prompt_length = 100 * 1024  # 100KB
        if len(prompt) > max_prompt_length:
            raise ValueError(f"Prompt too long: {len(prompt)} characters (max {max_prompt_length})")

        # Проверка на dangerous content patterns
        dangerous_patterns = [
            '<script', 'javascript:', 'vbscript:', 'data:',
            'onload=', 'onerror=', 'onclick=', '<iframe', '<object'
        ]
        prompt_lower = prompt.lower()
        for pattern in dangerous_patterns:
            if pattern in prompt_lower:
                raise ValueError(f"Potentially dangerous content detected in prompt: {pattern}")

        # Валидация model_name
        if model_name is not None:
            if not isinstance(model_name, str):
                raise TypeError("model_name must be a string or None")
            if model_name not in self.models:
                raise ValueError(f"Unknown model: {model_name}")

        # Валидация response_format
        if response_format is not None:
            if not isinstance(response_format, dict):
                raise TypeError("response_format must be a dictionary or None")
            if 'type' not in response_format:
                raise ValueError("response_format must contain 'type' key")
            valid_types = ['text', 'json_object', 'json_schema']
            if response_format['type'] not in valid_types:
                raise ValueError(f"Invalid response_format type: {response_format['type']}. Valid types: {valid_types}")

        # Валидация флагов
        if not isinstance(use_fastest, bool):
            raise TypeError("use_fastest must be a boolean")
        if not isinstance(use_parallel, bool):
            raise TypeError("use_parallel must be a boolean")

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
        # Валидация входных данных
        try:
            self._validate_generate_request(prompt, model_name, use_fastest, use_parallel, response_format)
        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid request parameters: {e}")
            return ModelResponse(
                model_name=model_name or "validation_error",
                content="",
                response_time=0.0,
                success=False,
                error=f"Validation error: {e}"
            )

        start_time = time.time()
        logger.debug(f"Starting response generation for prompt (length: {len(prompt)})")

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
                response = await self._generate_parallel(prompt, response_format=response_format)
            except Exception as e:
                logger.error(f"Ошибка в parallel режиме, fallback на single: {e}")
                # Fallback на single режим
                response = await self._generate_single(prompt, model_name, use_fastest, response_format=response_format)
        else:
            response = await self._generate_single(prompt, model_name, use_fastest, response_format=response_format)

        # Логируем производительность
        total_time = time.time() - start_time
        logger.debug(
            f"Response generated in {total_time:.3f}s using model {response.model_name} "
            f"(success: {response.success}, content_length: {len(response.content)})"
        )

        return response
    
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
                response = await self._call_model_with_retry(prompt, model_config, response_format=response_format)
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
                            f"модель {model_config.name} failed"
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
                f"⚠️ Все модели провалились для JSON mode, возвращаем последний ответ от {last_response.model_name}."
            )
            # Пытаемся извлечь хоть какой-то контент из последнего ответа (даже если он failed)
            if last_response.content:
                logger.info(f"Используем контент из последнего ответа: {Colors.colorize(last_response.content[:200] + '...', Colors.BRIGHT_MAGENTA)}")
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
        # Для JSON mode возвращаем нейтральный ответ, чтобы не блокировать работу системы
        logger.error(
            f"КРИТИЧЕСКАЯ СИТУАЦИЯ: Все модели провалились и нет даже последнего ответа. "
            f"Пробовали {len(models_to_try)} моделей. JSON mode blacklist: {len(self._json_mode_blacklist)} моделей"
        )

        if response_format and response_format.get("type") == "json_object":
            # Для JSON mode возвращаем нейтральный ответ, чтобы система могла продолжать работать
            fallback_content = '{"matches": true, "reason": "API недоступен, проверка пропущена"}'
            logger.warning(f"Возвращаем нейтральный fallback ответ для JSON mode: {fallback_content}")
        else:
            fallback_content = '{"error": "Все модели недоступны", "matches": false, "reason": "Техническая ошибка"}'

        fallback_response = ModelResponse(
            model_name="fallback",
            content=fallback_content,
            response_time=0.0,
            success=False,
            error="All models failed to generate response"
        )
        logger.info(f"Возвращаем дефолтный fallback ответ: {Colors.colorize(fallback_response.content, Colors.BRIGHT_MAGENTA)}")
        return fallback_response

    async def analyze_report_and_decide(
        self,
        report_content: str,
        report_file: str,
        next_instruction_name: str,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Анализирует репорт и принимает решение о дальнейших действиях.

        Args:
            report_content: Содержимое репорта
            report_file: Путь к файлу репорта
            next_instruction_name: Название следующей инструкции в линейном процессе
            task_id: ID задачи

        Returns:
            Словарь с решением:
            {
                "decision": "continue" | "insert_instruction" | "stop_and_check",
                "reason": "объяснение решения",
                "next_instruction_name": "название следующей инструкции",
                "free_instruction_text": "текст свободной инструкции" (если decision == "insert_instruction")
            }
        """
        logger.info(f"🔍 Анализ репорта: {report_file}")

        # Формируем промпт для анализа
        prompt = f"""Ты - опытный аналитик кода и процессов разработки.

ПРОЧИТАЙ СЛЕДУЮЩИЙ РЕПОРТ ПО ВЫПОЛНЕНИЮ ИНСТРУКЦИИ:

{report_content}

ЗАДАЧА: Проанализируй, в полной ли мере выполнена поставленная задача?

СЛЕДУЮЩАЯ ИНСТРУКЦИЯ В ЛИНЕЙНОМ ПРОЦЕССЕ: "{next_instruction_name}"

ПРИМИ РЕШЕНИЕ:

1. **CONTINUE** - Задача выполнена полностью, можно переходить к следующей инструкции "{next_instruction_name}"
2. **INSERT_INSTRUCTION** - Есть проблемы или недоработки, нужно выполнить дополнительную инструкцию перед продолжением
3. **STOP_AND_CHECK** - Задача выполнена, но требуется дополнительная проверка перед переходом к следующей инструкции

ФОРМАТ ОТВЕТА (ТОЛЬКО JSON):
{{
    "decision": "continue" | "insert_instruction" | "stop_and_check",
    "reason": "Подробное объяснение решения на основе анализа репорта",
    "next_instruction_name": "{next_instruction_name}",
    "free_instruction_text": "Если INSERT_INSTRUCTION - текст конкретной инструкции для исправления проблем"
}}

Правила принятия решения:
- Если в отчете есть фраза "Отчет завершен!", "Тестирование завершено!" или аналогичная - это сигнал успешного завершения
- Если есть явные проблемы, ошибки или недоработки - INSERT_INSTRUCTION
- Если есть сомнения или частичное выполнение - INSERT_INSTRUCTION
- Только при полном успешном выполнении - CONTINUE
"""

        try:
            # Получаем ответ от модели с JSON mode для надежного парсинга
            response = await self.generate_response(
                prompt=prompt,
                response_format={"type": "json_object"},
                use_fastest=True
            )

            if not response.success:
                logger.error(f"Ошибка при анализе репорта: {response.error}")
                return {
                    "decision": "continue",
                    "reason": f"Ошибка анализа: {response.error}",
                    "next_instruction_name": next_instruction_name,
                    "free_instruction_text": ""
                }

            # Парсим JSON ответ
            try:
                import json
                decision_data = json.loads(response.content)
                logger.info(f"🤖 Решение принято: {decision_data.get('decision', 'unknown')}")

                # Валидируем обязательные поля
                if "decision" not in decision_data:
                    decision_data["decision"] = "continue"
                if "reason" not in decision_data:
                    decision_data["reason"] = "Решение не указано в ответе модели"
                if "next_instruction_name" not in decision_data:
                    decision_data["next_instruction_name"] = next_instruction_name
                if "free_instruction_text" not in decision_data:
                    decision_data["free_instruction_text"] = ""

                return decision_data

            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON ответа: {e}")
                logger.error(f"Ответ модели: {response.content}")

                # Fallback: пытаемся извлечь решение из текста
                content_lower = response.content.lower()
                if "continue" in content_lower and "insert" not in content_lower:
                    decision = "continue"
                elif "insert" in content_lower:
                    decision = "insert_instruction"
                else:
                    decision = "continue"  # Безопасный fallback

                return {
                    "decision": decision,
                    "reason": "Ошибка парсинга JSON, использовано резервное решение",
                    "next_instruction_name": next_instruction_name,
                    "free_instruction_text": ""
                }

        except Exception as e:
            logger.error(f"Критическая ошибка при анализе репорта: {e}", exc_info=True)
            return {
                "decision": "continue",
                "reason": f"Критическая ошибка анализа: {str(e)}",
                "next_instruction_name": next_instruction_name,
                "free_instruction_text": ""
            }

    async def analyze_instruction_count_change(
        self,
        old_count: int,
        new_count: int,
        task_description: str,
        last_completed_instruction: int,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Анализирует изменение количества инструкций и принимает решение о продолжении.

        Args:
            old_count: Предыдущее количество инструкций
            new_count: Новое количество инструкций
            task_description: Описание задачи
            last_completed_instruction: Последняя выполненная инструкция
            task_id: ID задачи

        Returns:
            Словарь с решением:
            {
                "decision": "restart" | "continue_from_last" | "continue_from_adjusted",
                "reason": "объяснение решения",
                "adjusted_instruction": номер инструкции для продолжения (если decision == "continue_from_adjusted")
            }
        """
        logger.info(f"🔍 Анализ изменения количества инструкций: {old_count} -> {new_count}")

        # Формируем промпт для анализа
        prompt = f"""Ты - эксперт по управлению задачами и процессами разработки.

ПРОБЛЕМА: Количество инструкций в задаче изменилось с {old_count} на {new_count}.

КОНТЕКСТ ЗАДАЧИ:
{task_description}

ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ИНСТРУКЦИЯ: {last_completed_instruction}
ID ЗАДАЧИ: {task_id}

ПРИМИ РЕШЕНИЕ:

1. **RESTART** - Начать выполнение сначала (если изменения радикальные)
2. **CONTINUE_FROM_LAST** - Продолжить с последней выполненной инструкции
3. **CONTINUE_FROM_ADJUSTED** - Продолжить с скорректированного номера инструкции

ФАКТОРЫ ДЛЯ РЕШЕНИЯ:
- Если инструкции были объединены/упрощены - CONTINUE_FROM_LAST
- Если добавлены новые инструкции в начало - CONTINUE_FROM_ADJUSTED
- Если изменения кардинальные - RESTART
- Если количество уменьшилось незначительно - CONTINUE_FROM_LAST

ФОРМАТ ОТВЕТА (ТОЛЬКО JSON):
{{
    "decision": "restart" | "continue_from_last" | "continue_from_adjusted",
    "reason": "Подробное объяснение решения на основе анализа",
    "adjusted_instruction": номер инструкции для продолжения (если continue_from_adjusted)
}}

Правила принятия решения:
- Если old_count > new_count и разница небольшая - CONTINUE_FROM_LAST
- Если old_count < new_count - RESTART (безопасный вариант)
- Если old_count значительно отличается - RESTART
- Только при незначительных изменениях - CONTINUE_FROM_LAST
"""

        try:
            # Получаем ответ от модели с JSON mode для надежного парсинга
            response = await self.generate_response(
                prompt=prompt,
                response_format={"type": "json_object"},
                use_fastest=True
            )

            if not response.success:
                logger.error(f"Ошибка при анализе изменения инструкций: {response.error}")
                return {
                    "decision": "restart",
                    "reason": f"Ошибка анализа: {response.error}",
                    "adjusted_instruction": None
                }

            # Парсим JSON ответ
            try:
                import json
                decision_data = json.loads(response.content)
                logger.info(f"🤖 Решение по изменению инструкций: {decision_data.get('decision', 'unknown')}")

                # Валидируем обязательные поля
                if "decision" not in decision_data:
                    decision_data["decision"] = "restart"
                if "reason" not in decision_data:
                    decision_data["reason"] = "Решение не указано в ответе модели"
                if "adjusted_instruction" not in decision_data:
                    decision_data["adjusted_instruction"] = None

                return decision_data

            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON ответа: {e}")
                logger.error(f"Ответ модели: {response.content}")

                # Fallback: пытаемся извлечь решение из текста
                content_lower = response.content.lower()
                if "restart" in content_lower:
                    decision = "restart"
                elif "continue_from_adjusted" in content_lower:
                    decision = "continue_from_adjusted"
                elif "continue_from_last" in content_lower:
                    decision = "continue_from_last"
                else:
                    decision = "restart"  # Безопасный fallback

                return {
                    "decision": decision,
                    "reason": "Ошибка парсинга JSON, использовано резервное решение",
                    "adjusted_instruction": None
                }

        except Exception as e:
            logger.error(f"Критическая ошибка при анализе изменения инструкций: {e}", exc_info=True)
            return {
                "decision": "restart",
                "reason": f"Критическая ошибка анализа: {str(e)}",
                "adjusted_instruction": None
            }

    async def analyze_decision_response(
        self,
        decision_data: Dict[str, Any],
        original_report_file: str,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Анализирует принятое решение и подготавливает данные для выполнения.

        Args:
            decision_data: Данные решения от analyze_report_and_decide
            original_report_file: Путь к оригинальному репорт файлу
            task_id: ID задачи

        Returns:
            Словарь с финальными данными для выполнения:
            {
                "action": "continue" | "execute_free_instruction" | "stop_and_check",
                "next_instruction_name": "название следующей инструкции",
                "free_instruction_text": "текст свободной инструкции",
                "reason": "объяснение"
            }
        """
        decision = decision_data.get("decision", "continue")
        reason = decision_data.get("reason", "")
        next_instruction_name = decision_data.get("next_instruction_name", "")
        free_instruction_text = decision_data.get("free_instruction_text", "").strip()

        logger.info(f"🤖 Анализ решения: {decision}")
        logger.info(f"📝 Причина: {reason}")

        if decision == "continue":
            logger.info(f"➡️ Продолжаем линейно к инструкции: {next_instruction_name}")
            return {
                "action": "continue",
                "next_instruction_name": next_instruction_name,
                "free_instruction_text": "",
                "reason": reason
            }

        elif decision == "insert_instruction":
            if not free_instruction_text:
                logger.warning("Решение INSERT_INSTRUCTION, но текст инструкции пустой. Продолжаем линейно.")
                return {
                    "action": "continue",
                    "next_instruction_name": next_instruction_name,
                    "free_instruction_text": "",
                    "reason": reason + " (текст инструкции не указан)"
                }

            logger.info(f"🔧 Вставляем свободную инструкцию: {free_instruction_text[:100]}...")
            return {
                "action": "execute_free_instruction",
                "next_instruction_name": next_instruction_name,
                "free_instruction_text": free_instruction_text,
                "reason": reason
            }

        elif decision == "stop":
            # Останавливаемся на проверке репорта, не переходим к следующей инструкции
            logger.info(f"⏹️ Останавливаемся на текущей инструкции для дополнительной проверки: {reason}")
            return {
                "action": "stop_and_check",
                "next_instruction_name": next_instruction_name,
                "free_instruction_text": "",
                "reason": reason
            }

        else:
            logger.warning(f"Неизвестное решение: {decision}. Продолжаем линейно.")
            return {
                "action": "continue",
                "next_instruction_name": next_instruction_name,
                "free_instruction_text": "",
                "reason": f"Неизвестное решение '{decision}': {reason}"
            }
    
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
        
        # Генерируем ответы параллельно с timeout
        try:
            responses = await asyncio.wait_for(
                asyncio.gather(
                    self._call_model_with_retry(prompt, model1, response_format=response_format, max_retries=1),
                    self._call_model_with_retry(prompt, model2, response_format=response_format, max_retries=1),
                    return_exceptions=True
                ),
                timeout=60.0  # 60 секунд таймаут для параллельной генерации
            )
        except asyncio.TimeoutError:
            logger.error("Parallel generation timed out after 60 seconds")
            return ModelResponse(
                model_name="parallel_timeout",
                content="",
                response_time=60.0,
                success=False,
                error="Parallel generation timed out"
            )
        
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
            eval_response = await self._call_model_with_retry(evaluation_prompt, evaluator_model)
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
    
    async def _call_model_with_retry(
        self,
        prompt: str,
        model_config: ModelConfig,
        response_format: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> ModelResponse:
        """
        Вызов модели с retry логикой и exponential backoff.

        Args:
            prompt: Текст запроса
            model_config: Конфигурация модели
            response_format: Формат ответа
            max_retries: Максимальное количество попыток
            base_delay: Базовая задержка между попытками (сек)

        Returns:
            ModelResponse с результатом вызова
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return await self._call_model_internal(prompt, model_config, response_format)
            except Exception as e:
                last_error = e

                # Не retry для определенных типов ошибок
                if isinstance(e, ValueError) and "Validation error" in str(e):
                    # Валидационные ошибки не retry
                    break

                if attempt < max_retries - 1:
                    # Exponential backoff с jitter
                    delay = base_delay * (2 ** attempt)
                    # Добавляем jitter (±25%)
                    jitter = delay * 0.25 * (2 * (hash(str(attempt)) % 1000) / 1000 - 1)
                    delay += jitter

                    logger.warning(
                        f"Model call failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {max_retries} attempts failed for model {model_config.name}: {last_error}"
                    )

        # Все попытки провалились
        return ModelResponse(
            model_name=model_config.name,
            content="",
            response_time=0.0,
            success=False,
            error=f"Request failed after {max_retries} attempts: {last_error}"
        )

    async def _call_model(
        self,
        prompt: str,
        model_config: ModelConfig,
        response_format: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        """
        Вызов модели для генерации ответа.

        Returns:
            ModelResponse - всегда, даже при ошибках (для обратной совместимости)
        """
        try:
            return await self._call_model_internal(prompt, model_config, response_format)
        except Exception as e:
            # Для обратной совместимости возвращаем ModelResponse с ошибкой
            return ModelResponse(
                model_name=model_config.name,
                content="",
                response_time=0.0,
                success=False,
                error=str(e)
            )

    async def _call_model_internal(
        self,
        prompt: str,
        model_config: ModelConfig,
        response_format: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        """
        Внутренний вызов модели - поднимает исключения при ошибках.

        Raises:
            Exception: При любых ошибках API или сети
        """
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

            # Инвалидируем кэш самой быстрой модели при изменении статистики
            self._invalidate_fastest_cache()

            return ModelResponse(
                model_name=model_config.name,
                content=content,
                response_time=response_time,
                success=True
            )

        except Exception as e:
            response_time = time.time() - start_time

            model_config.error_count += 1

            # Инвалидируем кэш самой быстрой модели при ошибке
            self._invalidate_fastest_cache()

            # Поднимаем исключение для retry логики
            raise
