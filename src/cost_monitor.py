"""
Мониторинг стоимости API вызовов для LLM моделей.

Предоставляет функциональность для:
- Отслеживания расходов на API вызовы
- Установки лимитов и предупреждений
- Анализа эффективности использования моделей
- Рекомендаций по выбору моделей
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import yaml

logger = logging.getLogger(__name__)

@dataclass
class APICallRecord:
    """Запись о API вызове для мониторинга стоимости"""
    timestamp: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    task_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CostSummary:
    """Сводка стоимости за период"""
    period: str  # "hourly", "daily", "weekly", "monthly"
    start_date: str
    end_date: str
    total_cost: float
    total_tokens: int
    total_calls: int
    model_breakdown: Dict[str, Dict[str, float]]
    recommendations: List[str]

class CostMonitor:
    """Монитор стоимости API вызовов"""

    def __init__(self, config_path: str = "config/llm_cost_config.yaml", log_file: str = "logs/llm_cost_tracking.json"):
        self.config_path = Path(config_path)
        self.log_file = Path(log_file)
        self.config = self._load_config()
        self.records: List[APICallRecord] = []
        self._load_existing_records()

        # Настройки лимитов
        self.daily_limit = self.config.get('monitoring', {}).get('limits', {}).get('daily_limit', 10.0)
        self.monthly_limit = self.config.get('monitoring', {}).get('limits', {}).get('monthly_limit', 100.0)
        self.warning_thresholds = self.config.get('monitoring', {}).get('warning_thresholds', [50, 80, 95])

    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации стоимости"""
        if not self.config_path.exists():
            logger.warning(f"Конфигурационный файл {self.config_path} не найден, используются значения по умолчанию")
            return {}

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации стоимости: {e}")
            return {}

    def _load_existing_records(self):
        """Загрузка существующих записей о вызовах"""
        if not self.log_file.exists():
            return

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.records = [APICallRecord(**record) for record in data.get('records', [])]
        except Exception as e:
            logger.error(f"Ошибка загрузки записей о вызовах: {e}")
            self.records = []

    def _save_records(self):
        """Сохранение записей в файл"""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'last_updated': datetime.now().isoformat(),
            'total_records': len(self.records),
            'records': [record.to_dict() for record in self.records]
        }

        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения записей: {e}")

    def get_model_cost_info(self, model_name: str) -> Optional[Dict[str, float]]:
        """Получение информации о стоимости модели"""
        # Сначала проверяем OpenRouter модели
        openrouter_models = self.config.get('openrouter', {})
        if model_name in openrouter_models:
            return openrouter_models[model_name]

        # Затем специальные модели
        special_models = self.config.get('special_models', {})
        if model_name in special_models:
            return special_models[model_name]

        logger.warning(f"Информация о стоимости для модели {model_name} не найдена")
        return None

    def calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """
        Расчет стоимости API вызова

        Args:
            model_name: Название модели
            input_tokens: Количество входных токенов
            output_tokens: Количество выходных токенов

        Returns:
            Стоимость в USD
        """
        cost_info = self.get_model_cost_info(model_name)
        if not cost_info:
            return 0.0

        input_cost_per_1k = cost_info.get('input_cost_per_1k', 0.0)
        output_cost_per_1k = cost_info.get('output_cost_per_1k', 0.0)

        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k

        return input_cost + output_cost

    def record_api_call(self, model_name: str, input_tokens: int, output_tokens: int,
                       provider: str = "openrouter", task_id: Optional[str] = None,
                       success: bool = True, error_message: Optional[str] = None):
        """
        Запись информации о API вызове

        Args:
            model_name: Название модели
            input_tokens: Количество входных токенов
            output_tokens: Количество выходных токенов
            provider: Провайдер модели
            task_id: ID задачи (опционально)
            success: Успешность вызова
            error_message: Сообщение об ошибке (опционально)
        """
        total_tokens = input_tokens + output_tokens
        cost_usd = self.calculate_cost(model_name, input_tokens, output_tokens)

        record = APICallRecord(
            timestamp=datetime.now().isoformat(),
            model=model_name,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            task_id=task_id,
            success=success,
            error_message=error_message
        )

        self.records.append(record)
        self._save_records()

        # Проверка лимитов и отправка предупреждений
        self._check_limits_and_warn()

        logger.info(f"API вызов записан: {model_name}, стоимость ${cost_usd:.6f}, токены: {total_tokens}")

    def _check_limits_and_warn(self):
        """Проверка лимитов расходов и отправка предупреждений"""
        daily_cost = self.get_cost_summary('daily').total_cost
        monthly_cost = self.get_cost_summary('monthly').total_cost

        # Проверка дневного лимита
        for threshold in self.warning_thresholds:
            limit_value = self.daily_limit * (threshold / 100)
            if daily_cost >= limit_value:
                logger.warning(f"Дневной лимит расходов достигнут на {threshold}%: ${daily_cost:.2f} из ${self.daily_limit:.2f}")

        if daily_cost >= self.daily_limit:
            logger.error(f"ПРЕВЫШЕН дневной лимит расходов: ${daily_cost:.2f} из ${self.daily_limit:.2f}")

        # Проверка месячного лимита
        for threshold in self.warning_thresholds:
            limit_value = self.monthly_limit * (threshold / 100)
            if monthly_cost >= limit_value:
                logger.warning(f"Месячный лимит расходов достигнут на {threshold}%: ${monthly_cost:.2f} из ${self.monthly_limit:.2f}")

        if monthly_cost >= self.monthly_limit:
            logger.error(f"ПРЕВЫШЕН месячный лимит расходов: ${monthly_cost:.2f} из ${self.monthly_limit:.2f}")
    def get_cost_summary(self, period: str = 'daily') -> CostSummary:
        """
        Получение сводки стоимости за период

        Args:
            period: Период агрегации ('hourly', 'daily', 'weekly', 'monthly')

        Returns:
            CostSummary объект с агрегированными данными
        """
        now = datetime.now()

        if period == 'hourly':
            start_date = now - timedelta(hours=1)
        elif period == 'daily':
            start_date = now - timedelta(days=1)
        elif period == 'weekly':
            start_date = now - timedelta(weeks=1)
        elif period == 'monthly':
            start_date = now - timedelta(days=30)
        else:
            raise ValueError(f"Неизвестный период: {period}")

        # Фильтрация записей по периоду
        period_records = [
            r for r in self.records
            if datetime.fromisoformat(r.timestamp) >= start_date
        ]

        # Расчет общих метрик
        total_cost = sum(r.cost_usd for r in period_records)
        total_tokens = sum(r.total_tokens for r in period_records)
        total_calls = len(period_records)

        # Разбивка по моделям
        model_breakdown = {}
        for record in period_records:
            if record.model not in model_breakdown:
                model_breakdown[record.model] = {
                    'cost': 0.0,
                    'tokens': 0,
                    'calls': 0
                }
            model_breakdown[record.model]['cost'] += record.cost_usd
            model_breakdown[record.model]['tokens'] += record.total_tokens
            model_breakdown[record.model]['calls'] += 1

        # Генерация рекомендаций
        recommendations = self._generate_recommendations(model_breakdown, total_cost, period)

        return CostSummary(
            period=period,
            start_date=start_date.isoformat(),
            end_date=now.isoformat(),
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_calls=total_calls,
            model_breakdown=model_breakdown,
            recommendations=recommendations
        )

    def _generate_recommendations(self, model_breakdown: Dict[str, Dict[str, float]],
                                total_cost: float, period: str) -> List[str]:
        """Генерация рекомендаций по оптимизации расходов"""
        recommendations = []

        # Рекомендация по выбору моделей
        if model_breakdown:
            # Сортировка моделей по стоимости
            sorted_models = sorted(model_breakdown.items(), key=lambda x: x[1]['cost'], reverse=True)
            most_expensive = sorted_models[0][0]
            most_expensive_cost = sorted_models[0][1]['cost']

            if most_expensive_cost > total_cost * 0.5:
                recommendations.append(f"Модель {most_expensive} составляет более 50% расходов за {period} период")

            # Поиск эффективных моделей
            efficient_models = [
                model for model, stats in model_breakdown.items()
                if stats['calls'] > 0 and (stats['cost'] / stats['calls']) < 0.01  # Менее $0.01 за вызов
            ]

            if efficient_models:
                recommendations.append(f"Эффективные модели: {', '.join(efficient_models)}")

        # Рекомендации по лимитам
        if period == 'daily' and total_cost > self.daily_limit * 0.8:
            recommendations.append(f"Дневной лимит близок к превышению: ${total_cost:.2f} из ${self.daily_limit:.2f}")

        if period == 'monthly' and total_cost > self.monthly_limit * 0.8:
            recommendations.append(f"Месячный лимит близок к превышению: ${total_cost:.2f} из ${self.monthly_limit:.2f}")

        return recommendations

    def get_model_efficiency_report(self) -> Dict[str, Any]:
        """Отчет об эффективности использования моделей"""
        if not self.records:
            return {"message": "Нет данных о вызовах API"}

        # Группировка по моделям
        model_stats = {}
        for record in self.records:
            if record.model not in model_stats:
                model_stats[record.model] = {
                    'total_cost': 0.0,
                    'total_tokens': 0,
                    'total_calls': 0,
                    'successful_calls': 0,
                    'avg_cost_per_call': 0.0,
                    'avg_tokens_per_call': 0.0,
                    'success_rate': 0.0
                }

            stats = model_stats[record.model]
            stats['total_cost'] += record.cost_usd
            stats['total_tokens'] += record.total_tokens
            stats['total_calls'] += 1
            if record.success:
                stats['successful_calls'] += 1

        # Расчет производных метрик
        for model, stats in model_stats.items():
            if stats['total_calls'] > 0:
                stats['avg_cost_per_call'] = stats['total_cost'] / stats['total_calls']
                stats['avg_tokens_per_call'] = stats['total_tokens'] / stats['total_calls']
                stats['success_rate'] = stats['successful_calls'] / stats['total_calls']

        # Сортировка по общей стоимости
        sorted_models = sorted(model_stats.items(), key=lambda x: x[1]['total_cost'], reverse=True)

        return {
            'total_models_used': len(model_stats),
            'total_api_calls': sum(stats['total_calls'] for stats in model_stats.values()),
            'total_cost': sum(stats['total_cost'] for stats in model_stats.values()),
            'model_ranking': sorted_models,
            'most_used_model': sorted_models[0][0] if sorted_models else None,
            'generated_at': datetime.now().isoformat()
        }

    def reset_records(self, days_to_keep: int = 30):
        """
        Очистка старых записей, оставляя только указанное количество дней

        Args:
            days_to_keep: Количество дней для сохранения записей
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        old_count = len(self.records)
        self.records = [
            r for r in self.records
            if datetime.fromisoformat(r.timestamp) >= cutoff_date
        ]

        new_count = len(self.records)
        removed_count = old_count - new_count

        if removed_count > 0:
            logger.info(f"Удалено {removed_count} старых записей о вызовах API")
            self._save_records()

# Глобальный экземпляр монитора для использования в приложении
cost_monitor = CostMonitor()