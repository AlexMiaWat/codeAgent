"""
Quality Gates Framework

Комплексная система контроля качества кода и выполнения задач.
Проверяет покрытие тестами, сложность кода, безопасность и другие метрики качества.
"""

from .quality_gate_manager import QualityGateManager
from .models.quality_result import QualityResult, QualityStatus
from .models.quality_metrics import QualityMetrics

__all__ = [
    'QualityGateManager',
    'QualityResult',
    'QualityStatus',
    'QualityMetrics'
]