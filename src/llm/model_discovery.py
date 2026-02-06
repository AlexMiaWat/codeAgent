"""
Модуль для обнаружения и обновления моделей через API провайдеров

Функционал:
- Получение списка доступных моделей через OpenRouter API
- Фильтрация бесплатных моделей
- Обновление конфигурации на основе результатов тестирования
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

import yaml
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)


class ModelDiscovery:
    """Класс для обнаружения моделей через API провайдеров"""
    
    def __init__(self, config_path: str = "config/llm_settings.yaml"):
        """
        Инициализация ModelDiscovery
        
        Args:
            config_path: Путь к файлу конфигурации LLM
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Загрузка конфигурации"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"LLM config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}
        
        # Подстановка переменных окружения
        self.config = self._substitute_env_vars(self.config)
    
    def _substitute_env_vars(self, obj: Any) -> Any:
        """Рекурсивная подстановка переменных окружения"""
        import os
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            var_expr = obj[2:-1]
            env_value = os.getenv(var_expr.strip())
            if env_value is None:
                return obj  # Возвращаем как есть, если переменная не найдена
            return env_value
        return obj
    
    async def discover_openrouter_models(
        self,
        free_only: bool = True,
        min_context_length: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение списка доступных моделей через OpenRouter API
        
        Args:
            free_only: Только бесплатные модели
            min_context_length: Минимальная длина контекста
        
        Returns:
            Список моделей с информацией о них
        """
        provider_config = self.config.get('providers', {}).get('openrouter', {})
        base_url = provider_config.get('base_url', 'https://openrouter.ai/api/v1')
        
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
            logger.warning("OpenRouter API key not found. Please set OPENROUTER_API_KEY environment variable or add it to .env file.")
            return []
        
        try:
            # Получаем список моделей через OpenRouter API
            url = f"{base_url}/models"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://codeagent.local",
                "X-Title": "Code Agent"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            models = data.get('data', [])
            
            logger.info(f"Received {len(models)} models from OpenRouter")
            
            # Фильтруем модели
            filtered_models = []
            for model in models:
                model_id = model.get('id', '')
                
                # Пропускаем модели без ID
                if not model_id:
                    continue
                
                pricing = model.get('pricing', {})
                
                # Фильтр по бесплатным моделям
                if free_only:
                    prompt_price = pricing.get('prompt', 0) if pricing else 0
                    completion_price = pricing.get('completion', 0) if pricing else 0
                    
                    # Конвертируем в float для сравнения
                    try:
                        prompt_price = float(prompt_price) if prompt_price else 0
                        completion_price = float(completion_price) if completion_price else 0
                    except (ValueError, TypeError):
                        prompt_price = 0
                        completion_price = 0
                    
                    if prompt_price > 0 or completion_price > 0:
                        continue
                
                # Фильтр по минимальной длине контекста
                context_length = model.get('context_length', 0)
                if min_context_length and context_length < min_context_length:
                    continue
                
                filtered_models.append({
                    'id': model_id,
                    'name': model_id,
                    'context_length': context_length,
                    'pricing': pricing,
                    'architecture': model.get('architecture', {}),
                    'top_provider': model.get('top_provider', {}),
                    'per_request_limits': model.get('per_request_limits', {})
                })
            
            logger.info(f"Filtered to {len(filtered_models)} models (free_only={free_only})")
            
            return filtered_models
            
        except Exception as e:
            logger.error(f"Error discovering OpenRouter models: {e}")
            return []
    
    def update_config_with_test_results(
        self,
        test_results: Dict[str, Dict[str, Any]],
        fastest_models: List[tuple],
        working_models: List[str],
        output_path: Optional[Path] = None
    ):
        """
        Обновление конфигурации на основе результатов тестирования
        
        Args:
            test_results: Результаты тестирования моделей
            fastest_models: Список (model_name, response_time) отсортированный по скорости
            working_models: Список работающих моделей
            output_path: Путь для сохранения обновленной конфигурации (если None - перезаписывает исходный)
        """
        if output_path is None:
            output_path = self.config_path
        
        # Создаем резервную копию
        backup_path = self.config_path.with_suffix('.yaml.backup')
        import shutil
        shutil.copy2(self.config_path, backup_path)
        logger.info(f"Backup saved to: {backup_path}")
        
        # Обновляем роли моделей на основе результатов
        # Primary: самые быстрые работающие модели
        primary_models = [name for name, _ in fastest_models[:2] if name in working_models]
        
        # Duplicate: следующие по скорости работающие модели
        duplicate_models = [name for name, _ in fastest_models[2:4] if name in working_models]
        
        # Reserve: остальные работающие модели
        reserve_models = [name for name in working_models 
                         if name not in primary_models and name not in duplicate_models][:2]
        
        # Fallback: все остальные (включая потенциально неработающие, но оставляем их на случай)
        all_configured = set()
        provider_models = self.config.get('providers', {}).get('openrouter', {}).get('models', {})
        for provider_name, model_list in provider_models.items():
            if isinstance(model_list, list):
                for model in model_list:
                    if isinstance(model, dict):
                        all_configured.add(model.get('name'))
        
        fallback_models = [name for name in all_configured 
                          if name not in primary_models 
                          and name not in duplicate_models 
                          and name not in reserve_models][:2]
        
        # Обновляем конфигурацию
        if 'llm' not in self.config:
            self.config['llm'] = {}
        
        self.config['llm']['model_roles'] = {
            'primary': primary_models,
            'duplicate': duplicate_models,
            'reserve': reserve_models if reserve_models else ['kwaipilot/kat-coder-pro:free'],
            'fallback': fallback_models if fallback_models else ['undi95/remm-slerp-l2-13b']
        }
        
        # Добавляем метаданные обновления
        self.config['llm']['_last_updated'] = datetime.now().isoformat()
        self.config['llm']['_update_source'] = 'auto_test_results'
        self.config['llm']['_stats'] = {
            'total_tested': len(test_results),
            'working_count': len(working_models),
            'fastest_model': fastest_models[0][0] if fastest_models else None
        }
        
        # Сохраняем обновленную конфигурацию
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration updated: {len(primary_models)} primary, "
                   f"{len(duplicate_models)} duplicate, {len(reserve_models)} reserve, "
                   f"{len(fallback_models)} fallback models")
    
    async def sync_models_from_api(
        self,
        free_only: bool = True,
        update_config: bool = False
    ) -> Dict[str, Any]:
        """
        Синхронизация списка моделей из API и обновление конфигурации
        
        Args:
            free_only: Только бесплатные модели
            update_config: Обновить конфигурацию на основе API
        
        Returns:
            Словарь с результатами синхронизации
        """
        discovered = await self.discover_openrouter_models(free_only=free_only)
        
        result = {
            'discovered_count': len(discovered),
            'models': discovered,
            'timestamp': datetime.now().isoformat()
        }
        
        if update_config:
            # Здесь можно добавить логику автоматического обновления config
            # на основе обнаруженных моделей
            logger.info(f"Discovered {len(discovered)} models from API")
        
        return result
