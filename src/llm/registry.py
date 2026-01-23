"""
ModelRegistry - управление конфигурациями моделей и их ролями

Ответственность:
- Загрузка конфигурации из YAML
- Автоматический выбор моделей по ролям
- Управление статистикой моделей
- Валидация конфигураций
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from .types import ModelConfig, ModelRole, IModelRegistry, IConfigLoader

logger = logging.getLogger(__name__)


class ModelRegistry(IModelRegistry):
    """
    Реестр моделей - управляет конфигурациями моделей и их ролями

    Предоставляет:
    - Загрузку и валидацию конфигураций
    - Автоматический выбор моделей по ролям
    - Статистику использования моделей
    - Быстрый доступ к моделям по имени/роли
    """

    def __init__(self, config_loader: IConfigLoader, config_path: str = "config/llm_settings.yaml"):
        """
        Инициализация реестра моделей

        Args:
            config_loader: Загрузчик конфигурации
            config_path: Путь к файлу конфигурации
        """
        self.config_loader = config_loader
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.models: Dict[str, ModelConfig] = {}

        self._load_config()
        self._init_models()

    def _load_config(self):
        """Загрузка конфигурации"""
        self.config = self.config_loader.load_config(self.config_path)

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

    # Реализация интерфейса IModelRegistry

    def get_models_by_role(self, role: ModelRole) -> List[ModelConfig]:
        """Получить модели по роли"""
        return [model for model in self.models.values() if model.role == role and model.enabled]

    def get_model(self, name: str) -> Optional[ModelConfig]:
        """Получить модель по имени"""
        return self.models.get(name)

    def get_all_models(self) -> List[ModelConfig]:
        """Получить все модели"""
        return list(self.models.values())

    def update_model_stats(self, model_name: str, success: bool, response_time: float) -> None:
        """Обновить статистику модели"""
        if model_name in self.models:
            model = self.models[model_name]
            model.last_response_time = response_time
            if success:
                model.success_count += 1
            else:
                model.error_count += 1

    def get_fastest_model(self, role: ModelRole = ModelRole.PRIMARY) -> Optional[ModelConfig]:
        """Получить самую быструю модель для указанной роли"""
        role_models = self.get_models_by_role(role)
        if not role_models:
            return None

        # Выбираем модель с минимальным средним временем ответа
        # Для моделей без статистики используем некоторую эвристику
        def get_avg_time(model: ModelConfig) -> float:
            total_requests = model.success_count + model.error_count
            if total_requests > 0:
                # Среднее время на основе статистики
                return model.last_response_time  # Упрощенно, в реальности нужна история
            else:
                # Для новых моделей - эвристика по размеру модели
                if '1b' in model.name.lower() or 'mini' in model.name.lower():
                    return 2.0  # Быстрые маленькие модели
                elif '70b' in model.name.lower() or '72b' in model.name.lower():
                    return 15.0  # Медленные большие модели
                else:
                    return 5.0  # Средние модели

        return min(role_models, key=get_avg_time)

    def disable_model(self, model_name: str) -> None:
        """Отключить модель"""
        if model_name in self.models:
            self.models[model_name].enabled = False
            logger.info(f"Disabled model {model_name}")

    def enable_model(self, model_name: str) -> None:
        """Включить модель"""
        if model_name in self.models:
            self.models[model_name].enabled = True
            logger.info(f"Enabled model {model_name}")