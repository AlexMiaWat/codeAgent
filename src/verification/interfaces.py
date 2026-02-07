"""
Интерфейсы для системы верификации
"""
from dataclasses import dataclass

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from src.quality.models.quality_result import QualityResult, MultiLevelVerificationResult, VerificationResult, VerificationLevel, QualityGateResult


class IExecutionMonitor(ABC):
    """
    Интерфейс для мониторинга выполнения задач
    """

    @abstractmethod
    async def start_monitoring(self, task_id: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Начало мониторинга выполнения задачи

        Args:
            task_id: Идентификатор задачи
            context: Контекст выполнения
        """
        pass

    @abstractmethod
    async def update_progress(self, task_id: str, progress_data: Dict[str, Any]) -> None:
        """
        Обновление прогресса выполнения

        Args:
            task_id: Идентификатор задачи
            progress_data: Данные прогресса
        """
        pass

    @abstractmethod
    async def check_execution_health(self, task_id: str) -> Dict[str, Any]:
        """
        Проверка здоровья выполнения задачи

        Args:
            task_id: Идентификатор задачи

        Returns:
            Данные о здоровье выполнения
        """
        pass

    @abstractmethod
    async def stop_monitoring(self, task_id: str) -> Dict[str, Any]:
        """
        Остановка мониторинга и получение финальных метрик

        Args:
            task_id: Идентификатор задачи

        Returns:
            Финальные метрики выполнения
        """
        pass


class ILLMValidator(ABC):
    """
    Интерфейс для LLM-based валидации результатов
    """

    @abstractmethod
    async def validate_code_quality(self, code_changes: Dict[str, Any],
                                   context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Валидация качества кода через LLM

        Args:
            code_changes: Изменения в коде
            context: Контекст валидации

        Returns:
            Результат валидации
        """
        pass

    @abstractmethod
    async def validate_task_compliance(self, task_description: str, execution_result: Dict[str, Any],
                                      context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Валидация соответствия выполнения задаче

        Args:
            task_description: Описание задачи
            execution_result: Результат выполнения
            context: Контекст валидации

        Returns:
            Результат валидации
        """
        pass

    @abstractmethod
    async def generate_improvement_suggestions(self, analysis_data: Dict[str, Any]) -> list[str]:
        """
        Генерация предложений по улучшению

        Args:
            analysis_data: Данные для анализа

        Returns:
            Список предложений
        """
        pass


class IMultiLevelVerificationManager(ABC):
    """
    Интерфейс для многоуровневого менеджера верификации
    """

    @abstractmethod
    async def run_verification_pipeline(self, task_id: str,
                                       context: Optional[Dict[str, Any]] = None) -> MultiLevelVerificationResult:
        """
        Запуск полного пайплайна верификации

        Args:
            task_id: Идентификатор задачи
            context: Контекст верификации

        Returns:
            Результат многоуровневой верификации
        """
        pass

    @abstractmethod
    async def run_pre_execution_checks(self, task_id: str,
                                      context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Выполнение проверок перед выполнением

        Args:
            task_id: Идентификатор задачи
            context: Контекст выполнения

        Returns:
            Результат pre-execution верификации
        """
        pass

    @abstractmethod
    async def run_in_execution_monitoring(self, task_id: str,
                                         context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Мониторинг выполнения задачи

        Args:
            task_id: Идентификатор задачи
            context: Контекст выполнения

        Returns:
            Результат in-execution верификации
        """
        pass

    @abstractmethod
    async def run_post_execution_validation(self, task_id: str,
                                           execution_result: Dict[str, Any],
                                           context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Валидация после выполнения

        Args:
            task_id: Идентификатор задачи
            execution_result: Результат выполнения
            context: Контекст валидации

        Returns:
            Результат post-execution верификации
        """
        pass

    @abstractmethod
    async def run_ai_validation(self, task_id: str, analysis_data: Dict[str, Any],
                               context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        AI-based валидация результатов

        Args:
            task_id: Идентификатор задачи
            analysis_data: Данные для анализа
            context: Контекст валидации

        Returns:
            Результат AI валидации
        """
        pass

    @abstractmethod
    async def run_cross_validation(self, verification_results: Dict[str, VerificationResult],
                                  context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Кросс-валидация результатов между уровнями

        Args:
            verification_results: Результаты верификации по уровням
            context: Контекст валидации

        Returns:
            Результат кросс-валидации
        """
        pass