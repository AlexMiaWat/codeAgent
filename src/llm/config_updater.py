"""
Модуль для автоматического обновления конфигурации LLM на основе результатов тестирования

Интегрирует ModelDiscovery, LLMTestRunner и автоматическое обновление конфигурации
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime

from .model_discovery import ModelDiscovery
from .llm_test_runner import LLMTestRunner
from .llm_manager import LLMManager

logger = logging.getLogger(__name__)


class ConfigUpdater:
    """Класс для автоматического обновления конфигурации LLM"""
    
    def __init__(
        self,
        config_path: str = "config/llm_settings.yaml",
        auto_backup: bool = True
    ):
        """
        Инициализация ConfigUpdater
        
        Args:
            config_path: Путь к файлу конфигурации LLM
            auto_backup: Создавать резервную копию перед обновлением
        """
        self.config_path = Path(config_path)
        self.auto_backup = auto_backup
        self.discovery = ModelDiscovery(config_path)
        self.llm_manager = LLMManager(config_path)
        self.test_runner = LLMTestRunner(self.llm_manager)
    
    async def run_full_test_and_update(
        self,
        test_prompt: str = "Привет, это тестовое сообщение. Ответь кратко.",
        update_config: bool = True
    ) -> Dict[str, Any]:
        """
        Запуск полного тестирования и обновление конфигурации
        
        Args:
            test_prompt: Текст для тестирования моделей
            update_config: Обновить конфигурацию на основе результатов
        
        Returns:
            Словарь с результатами тестирования и обновления
        """
        logger.info("Starting full test and configuration update")
        
        # Шаг 1: Тестирование всех моделей
        logger.info("Step 1: Testing all models...")
        test_results = await self.test_runner.test_all_models(
            simple_prompt=test_prompt,
            delay=1.0
        )
        
        # Шаг 2: Определение самых быстрых моделей
        logger.info("Step 2: Determining fastest models...")
        fastest_models = self.test_runner.get_fastest_models(min_available=True)
        
        # Шаг 3: Получение списка работающих моделей
        logger.info("Step 3: Getting working models...")
        working_models = self.test_runner.get_working_models()
        
        # Шаг 4: Обновление конфигурации
        if update_config:
            logger.info("Step 4: Updating configuration...")
            self.discovery.update_config_with_test_results(
                test_results=test_results,
                fastest_models=fastest_models,
                working_models=working_models
            )
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'test_results': test_results,
            'fastest_models': fastest_models,
            'working_models': working_models,
            'config_updated': update_config
        }
        
        logger.info(f"Test complete: {len(working_models)} working models, "
                   f"{len(fastest_models)} fastest models identified")
        
        return result
    
    async def discover_and_sync_models(
        self,
        free_only: bool = True
    ) -> Dict[str, Any]:
        """
        Обнаружение моделей через API и синхронизация
        
        Args:
            free_only: Только бесплатные модели
        
        Returns:
            Результаты обнаружения
        """
        logger.info("Discovering models from API...")
        result = await self.discovery.sync_models_from_api(free_only=free_only)
        return result
