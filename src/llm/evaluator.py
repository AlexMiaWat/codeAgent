"""
ResponseEvaluator - оценка качества ответов

Ответственность:
- LLM-based оценка качества
- Выбор по множеству критериев
- Confidence scoring
- A/B testing ответов
"""

import logging
from typing import Dict, List, Optional, Any
from .types import ModelConfig, EvaluationResult, IResponseEvaluator, IClientManager

logger = logging.getLogger(__name__)


class ResponseEvaluator(IResponseEvaluator):
    """
    Оценщик ответов - оценивает качество ответов моделей

    Предоставляет:
    - Оценку качества через LLM
    - Confidence scoring
    - Сравнение нескольких ответов
    - Выбор лучшего ответа по критериям
    """

    def __init__(self, evaluator_model: Optional[ModelConfig] = None):
        """
        Инициализация оценщика ответов

        Args:
            evaluator_model: Модель для оценки (если None, будет выбрана автоматически)
        """
        self.evaluator_model = evaluator_model

    async def evaluate_response(
        self,
        prompt: str,
        response: str,
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> EvaluationResult:
        """
        Оценить качество ответа

        Args:
            prompt: Исходный запрос
            response: Ответ для оценки
            client_manager: Менеджер клиентов для вызова модели
            evaluator_model: Модель-оценщик (опционально)

        Returns:
            Результат оценки
        """
        # Выбираем модель-оценщик
        eval_model = evaluator_model or self.evaluator_model
        if not eval_model:
            # Fallback: возвращаем среднюю оценку
            logger.warning("No evaluator model available, returning neutral score")
            return EvaluationResult(score=3.0, reasoning="No evaluator available")

        # Создаем промпт для оценки
        evaluation_prompt = self._create_evaluation_prompt(prompt, response)

        try:
            # Вызываем модель-оценщик
            model_response = await client_manager.call_model(
                model_config=eval_model,
                prompt=evaluation_prompt
            )

            if not model_response.success:
                logger.warning(f"Evaluation model failed: {model_response.error}")
                return EvaluationResult(score=3.0, reasoning="Evaluation failed")

            # Парсим оценку из ответа
            score, reasoning = self._parse_evaluation_response(model_response.content)

            return EvaluationResult(score=score, reasoning=reasoning)

        except Exception as e:
            logger.error(f"Error during response evaluation: {e}")
            return EvaluationResult(score=3.0, reasoning=f"Evaluation error: {e}")

    def _create_evaluation_prompt(self, prompt: str, response: str) -> str:
        """
        Создать промпт для оценки ответа

        Args:
            prompt: Исходный запрос
            response: Ответ для оценки

        Returns:
            Промпт для модели-оценщика
        """
        return f"""Please evaluate the quality of this response to the given prompt.

Prompt: {prompt}

Response: {response}

Evaluate the response on a scale from 1 to 5, where:
1 = Very poor quality, incorrect, irrelevant, or harmful
2 = Poor quality, has some issues but minimally useful
3 = Average quality, acceptable but could be better
4 = Good quality, well-structured and helpful
5 = Excellent quality, comprehensive, accurate, and insightful

Consider factors like:
- Accuracy and correctness
- Relevance to the prompt
- Clarity and coherence
- Completeness of information
- Helpfulness and usefulness

Provide your evaluation in this format:
Score: [1-5]
Reasoning: [brief explanation of your evaluation]

Your response should be concise and follow the exact format above."""

    def _parse_evaluation_response(self, content: str) -> tuple[float, str]:
        """
        Распарсить ответ модели-оценщика

        Args:
            content: Ответ модели-оценщика

        Returns:
            (score, reasoning)
        """
        try:
            lines = content.strip().split('\n')
            score = 3.0  # default
            reasoning = "No reasoning provided"

            for line in lines:
                line = line.strip()
                if line.startswith('Score:'):
                    try:
                        score_text = line.split(':', 1)[1].strip()
                        # Извлекаем число
                        import re
                        match = re.search(r'(\d+(?:\.\d+)?)', score_text)
                        if match:
                            score = float(match.group(1))
                            score = max(1.0, min(5.0, score))  # Ограничиваем диапазон
                    except (ValueError, IndexError):
                        logger.warning(f"Could not parse score from: {line}")
                elif line.startswith('Reasoning:'):
                    reasoning = line.split(':', 1)[1].strip()

            return score, reasoning

        except Exception as e:
            logger.warning(f"Error parsing evaluation response: {e}")
            return 3.0, f"Parse error: {e}"

    async def compare_responses(
        self,
        prompt: str,
        responses: List[str],
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> List[EvaluationResult]:
        """
        Сравнить несколько ответов

        Args:
            prompt: Исходный запрос
            responses: Список ответов для сравнения
            client_manager: Менеджер клиентов
            evaluator_model: Модель-оценщик

        Returns:
            Список результатов оценки
        """
        results = []
        for response in responses:
            result = await self.evaluate_response(prompt, response, client_manager, evaluator_model)
            results.append(result)

        return results

    async def select_best_response(
        self,
        prompt: str,
        responses: List[str],
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> tuple[int, EvaluationResult]:
        """
        Выбрать лучший ответ из списка

        Args:
            prompt: Исходный запрос
            responses: Список ответов
            client_manager: Менеджер клиентов
            evaluator_model: Модель-оценщик

        Returns:
            (index_of_best, evaluation_result)
        """
        if not responses:
            raise ValueError("No responses to evaluate")

        if len(responses) == 1:
            result = await self.evaluate_response(prompt, responses[0], client_manager, evaluator_model)
            return 0, result

        # Оцениваем все ответы
        evaluations = await self.compare_responses(prompt, responses, client_manager, evaluator_model)

        # Находим лучший по score
        best_index = 0
        best_score = evaluations[0].score

        for i, evaluation in enumerate(evaluations[1:], 1):
            if evaluation.score > best_score:
                best_score = evaluation.score
                best_index = i

        return best_index, evaluations[best_index]

    def set_evaluator_model(self, model: ModelConfig):
        """Установить модель-оценщик"""
        self.evaluator_model = model

    def get_evaluation_stats(self, evaluations: List[EvaluationResult]) -> Dict[str, Any]:
        """Получить статистику оценок"""
        if not evaluations:
            return {}

        scores = [e.score for e in evaluations]

        return {
            'count': len(evaluations),
            'average_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'score_distribution': self._get_score_distribution(scores)
        }

    def _get_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Получить распределение оценок"""
        distribution = {}
        for score in scores:
            key = f"{score:.1f}"
            distribution[key] = distribution.get(key, 0) + 1
        return distribution