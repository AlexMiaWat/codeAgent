"""
LLM-based валидация результатов выполнения задач
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from .interfaces import ILLMValidator
from src.llm.manager import LLMManager
from ..quality.models.quality_result import VerificationResult, VerificationLevel, QualityGateResult, QualityResult, QualityCheckType, QualityStatus

logger = logging.getLogger(__name__)


class LLMValidator(ILLMValidator):
    """
    Валидатор результатов на основе LLM анализа
    """

    def __init__(self, llm_manager: Optional[LLMManager] = None, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация LLM валидатора

        Args:
            llm_manager: Менеджер LLM (если None - будет создан новый)
            config: Конфигурация валидатора
        """
        self.config = config or {}
        self.code_quality_threshold = self.config.get('code_quality_threshold', 0.7)
        self.task_compliance_threshold = self.config.get('task_compliance_threshold', 0.8)
        self.logic_validation_threshold = self.config.get('logic_validation_threshold', 0.75)

        # Initialize LLM manager lazily to avoid config loading in tests
        self._llm_manager = llm_manager

    @property
    def llm_manager(self) -> LLMManager:
        """Lazy initialization of LLM manager"""
        if self._llm_manager is None:
            self._llm_manager = LLMManager()
        return self._llm_manager

    @llm_manager.setter
    def llm_manager(self, value: LLMManager):
        """Set LLM manager"""
        self._llm_manager = value

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
        start_time = datetime.now()

        try:
            # Подготавливаем данные для анализа
            analysis_data = self._prepare_code_analysis_data(code_changes, context)

            # Создаем промпт для анализа качества кода
            prompt = self._create_code_quality_prompt(analysis_data)

            # Получаем анализ от LLM
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                use_fastest=False,  # Для качества используем лучшую модель
                use_parallel=True,  # Используем параллельное выполнение для надежности
                response_format={"type": "json_object"}
            )

            if not response.success:
                return self._create_error_result(
                    "code_quality",
                    f"LLM analysis failed: {response.error}",
                    start_time
                )

            # Парсим результат анализа
            analysis_result = self._parse_code_quality_analysis(response.content)

            # Создаем QualityGateResult на основе анализа
            quality_result = self._create_quality_result_from_analysis(
                analysis_result,
                QualityCheckType.CODE_QUALITY_AI
            )

            return VerificationResult(
                task_id=code_changes.get('task_id', 'unknown'),
                verification_level=VerificationLevel.AI_VALIDATION,
                quality_result=QualityGateResult(
                    gate_name="ai_code_quality",
                    results=[quality_result]
                ),
                execution_time=(datetime.now() - start_time).total_seconds(),
                metadata={
                    'analysis_type': 'code_quality',
                    'llm_model': response.model_name,
                    'raw_analysis': analysis_result
                }
            )

        except Exception as e:
            logger.error(f"Error in code quality validation: {e}")
            return self._create_error_result("code_quality", str(e), start_time)

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
        start_time = datetime.now()

        try:
            # Подготавливаем данные для анализа
            analysis_data = {
                'task_description': task_description,
                'execution_result': execution_result,
                'context': context or {}
            }

            # Создаем промпт для анализа соответствия
            prompt = self._create_task_compliance_prompt(analysis_data)

            # Получаем анализ от LLM
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                use_fastest=False,
                use_parallel=True,
                response_format={"type": "json_object"}
            )

            if not response.success:
                return self._create_error_result(
                    "task_compliance",
                    f"LLM analysis failed: {response.error}",
                    start_time
                )

            # Парсим результат анализа
            analysis_result = self._parse_task_compliance_analysis(response.content)

            # Создаем QualityGateResult
            quality_result = self._create_quality_result_from_analysis(
                analysis_result,
                QualityCheckType.TASK_COMPLIANCE
            )

            return VerificationResult(
                task_id=execution_result.get('task_id', 'unknown'),
                verification_level=VerificationLevel.AI_VALIDATION,
                quality_result=QualityGateResult(
                    gate_name="ai_task_compliance",
                    results=[quality_result]
                ),
                execution_time=(datetime.now() - start_time).total_seconds(),
                metadata={
                    'analysis_type': 'task_compliance',
                    'llm_model': response.model_name,
                    'task_description': task_description,
                    'raw_analysis': analysis_result
                }
            )

        except Exception as e:
            logger.error(f"Error in task compliance validation: {e}")
            return self._create_error_result("task_compliance", str(e), start_time)

    async def validate_logic_correctness(self, code_changes: Dict[str, Any],
                                        context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Валидация корректности логики изменений

        Args:
            code_changes: Изменения в коде
            context: Контекст валидации

        Returns:
            Результат валидации
        """
        start_time = datetime.now()

        try:
            # Подготавливаем данные для анализа
            analysis_data = self._prepare_logic_analysis_data(code_changes, context)

            # Создаем промпт для анализа логики
            prompt = self._create_logic_validation_prompt(analysis_data)

            # Получаем анализ от LLM
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                use_fastest=False,
                use_parallel=True,
                response_format={"type": "json_object"}
            )

            if not response.success:
                return self._create_error_result(
                    "logic_validation",
                    f"LLM analysis failed: {response.error}",
                    start_time
                )

            # Парсим результат анализа
            analysis_result = self._parse_logic_validation_analysis(response.content)

            # Создаем QualityGateResult
            quality_result = self._create_quality_result_from_analysis(
                analysis_result,
                QualityCheckType.LOGIC_VALIDATION
            )

            return VerificationResult(
                task_id=code_changes.get('task_id', 'unknown'),
                verification_level=VerificationLevel.AI_VALIDATION,
                quality_result=QualityGateResult(
                    gate_name="ai_logic_validation",
                    results=[quality_result]
                ),
                execution_time=(datetime.now() - start_time).total_seconds(),
                metadata={
                    'analysis_type': 'logic_validation',
                    'llm_model': response.model_name,
                    'raw_analysis': analysis_result
                }
            )

        except Exception as e:
            logger.error(f"Error in logic validation: {e}")
            return self._create_error_result("logic_validation", str(e), start_time)

    async def generate_improvement_suggestions(self, analysis_data: Dict[str, Any]) -> List[str]:
        """
        Генерация предложений по улучшению

        Args:
            analysis_data: Данные для анализа

        Returns:
            Список предложений
        """
        try:
            prompt = self._create_improvement_suggestions_prompt(analysis_data)

            response = await self.llm_manager.generate_response(
                prompt=prompt,
                use_fastest=True,  # Для предложений можно использовать быструю модель
                response_format={"type": "json_object"}
            )

            if not response.success:
                logger.warning(f"Failed to generate improvement suggestions: {response.error}")
                return []

            # Парсим предложения
            suggestions_data = json.loads(response.content)
            return suggestions_data.get('suggestions', [])

        except Exception as e:
            logger.error(f"Error generating improvement suggestions: {e}")
            return []

    def _prepare_code_analysis_data(self, code_changes: Dict[str, Any],
                                  context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Подготовка данных для анализа качества кода"""
        return {
            'files_changed': code_changes.get('files_changed', []),
            'lines_added': code_changes.get('lines_added', 0),
            'lines_removed': code_changes.get('lines_removed', 0),
            'code_snippets': code_changes.get('code_snippets', []),
            'language': code_changes.get('language', 'python'),
            'project_context': context or {}
        }

    def _prepare_logic_analysis_data(self, code_changes: Dict[str, Any],
                                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Подготовка данных для анализа логики"""
        return {
            'code_changes': code_changes.get('code_changes', []),
            'task_description': code_changes.get('task_description', ''),
            'existing_code': code_changes.get('existing_code', []),
            'dependencies': code_changes.get('dependencies', []),
            'context': context or {}
        }

    def _create_code_quality_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """Создание промпта для анализа качества кода"""
        return f"""
        Analyze the code quality of the following code changes and provide a detailed assessment.

        Code Changes Analysis:
        - Files changed: {len(analysis_data['files_changed'])}
        - Lines added: {analysis_data['lines_added']}
        - Lines removed: {analysis_data['lines_removed']}
        - Language: {analysis_data['language']}

        Code snippets:
        {chr(10).join([f"File: {snippet.get('file', 'unknown')}{chr(10)}{snippet.get('content', '')}" for snippet in analysis_data['code_snippets'][:3]])}

        Please provide a JSON response with the following structure:
        {{
            "overall_score": 0.0-1.0,
            "readability_score": 0.0-1.0,
            "maintainability_score": 0.0-1.0,
            "efficiency_score": 0.0-1.0,
            "issues": [
                {{
                    "type": "error|warning|info",
                    "description": "description of the issue",
                    "severity": "high|medium|low",
                    "file": "file name",
                    "line": "line number if applicable"
                }}
            ],
            "strengths": ["list of code strengths"],
            "recommendations": ["list of improvement recommendations"]
        }}

        Focus on:
        - Code readability and style
        - Potential bugs or logic errors
        - Performance issues
        - Best practices compliance
        - Maintainability concerns
        """

    def _create_task_compliance_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """Создание промпта для анализа соответствия задаче"""
        execution_json = json.dumps(analysis_data['execution_result'], indent=2)
        context_json = json.dumps(analysis_data['context'], indent=2)
        return f"""
        Analyze whether the execution result properly fulfills the task requirements.

        Task Description:
        {analysis_data['task_description']}

        Execution Result:
        {execution_json}

        Context:
        {context_json}

        Please provide a JSON response with the following structure:
        {{
            "compliance_score": 0.0-1.0,
            "requirements_met": ["list of requirements that were satisfied"],
            "requirements_missing": ["list of requirements that were not addressed"],
            "issues": [
                {{
                    "type": "missing_feature|incorrect_implementation|extra_functionality",
                    "description": "description of the issue",
                    "severity": "high|medium|low"
                }}
            ],
            "overall_assessment": "brief assessment of task completion quality"
        }}

        Evaluate:
        - Completeness of task implementation
        - Accuracy of the solution
        - Adherence to requirements
        - Quality of implementation
        """

    def _create_logic_validation_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """Создание промпта для анализа логики"""
        changes_text = chr(10).join([f"File: {change.get('file', '')}{chr(10)}Change: {change.get('change', '')}" for change in analysis_data['code_changes'][:5]])
        code_context = chr(10).join([f"File: {code.get('file', '')}{chr(10)}Content: {code.get('content', '')[:500]}" for code in analysis_data['existing_code'][:3]])
        return f"""
        Analyze the logical correctness of the code changes.

        Task: {analysis_data['task_description']}

        Code Changes:
        {changes_text}

        Existing Code Context:
        {code_context}

        Please provide a JSON response with the following structure:
        {{
            "logic_score": 0.0-1.0,
            "logic_issues": [
                {{
                    "type": "logical_error|edge_case|performance|security",
                    "description": "description of the logic issue",
                    "severity": "high|medium|low",
                    "file": "affected file"
                }}
            ],
            "logic_strengths": ["list of logical strengths"],
            "edge_cases": ["potential edge cases to consider"],
            "logic_flow_assessment": "assessment of the logical flow"
        }}

        Focus on:
        - Logical correctness of algorithms
        - Edge cases handling
        - Error conditions
        - Data flow integrity
        - Business logic implementation
        """

    def _create_improvement_suggestions_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """Создание промпта для генерации предложений по улучшению"""
        analysis_json = json.dumps(analysis_data, indent=2)
        return f"""
        Based on the analysis data provided, generate specific improvement suggestions.

        Analysis Data:
        {analysis_json}

        Please provide a JSON response with the following structure:
        {{
            "suggestions": [
                {{
                    "category": "performance|security|maintainability|usability|testing",
                    "priority": "high|medium|low",
                    "description": "detailed description of the suggestion",
                    "implementation_effort": "low|medium|high",
                    "expected_benefit": "description of expected benefits"
                }}
            ]
        }}

        Focus on actionable, specific suggestions that would improve code quality.
        """

    def _parse_code_quality_analysis(self, content: str) -> Dict[str, Any]:
        """Парсинг анализа качества кода"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse code quality analysis: {content}")
            return {
                "overall_score": 0.5,
                "issues": [{"type": "error", "description": "Failed to parse LLM response"}],
                "strengths": [],
                "recommendations": []
            }

    def _parse_task_compliance_analysis(self, content: str) -> Dict[str, Any]:
        """Парсинг анализа соответствия задаче"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse task compliance analysis: {content}")
            return {
                "compliance_score": 0.5,
                "requirements_met": [],
                "requirements_missing": ["Unable to analyze due to parsing error"],
                "issues": [{"type": "error", "description": "Failed to parse LLM response"}],
                "overall_assessment": "Analysis failed due to parsing error"
            }

    def _parse_logic_validation_analysis(self, content: str) -> Dict[str, Any]:
        """Парсинг анализа логики"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse logic validation analysis: {content}")
            return {
                "logic_score": 0.5,
                "logic_issues": [{"type": "error", "description": "Failed to parse LLM response"}],
                "logic_strengths": [],
                "edge_cases": [],
                "logic_flow_assessment": "Analysis failed due to parsing error"
            }

    def _create_quality_result_from_analysis(self, analysis_result: Dict[str, Any],
                                           check_type: QualityCheckType) -> QualityResult:
        """Создание QualityResult из анализа"""
        score = analysis_result.get('overall_score') or analysis_result.get('compliance_score') or analysis_result.get('logic_score', 0.5)

        issues = analysis_result.get('issues', []) + analysis_result.get('logic_issues', [])
        has_high_severity = any(issue.get('severity') == 'high' for issue in issues)

        if score >= 0.8 and not has_high_severity:
            status = QualityStatus.PASSED
        elif score >= 0.6:
            status = QualityStatus.WARNING
        else:
            status = QualityStatus.FAILED

        message = f"AI validation completed with score {score:.2f}"
        if issues:
            high_issues = [i for i in issues if i.get('severity') == 'high']
            if high_issues:
                message += f", {len(high_issues)} high-severity issues found"

        return QualityResult(
            check_type=check_type,
            status=status,
            message=message,
            score=score,
            threshold=self.code_quality_threshold,
            details=analysis_result
        )

    def _create_error_result(self, analysis_type: str, error: str,
                           start_time: datetime) -> VerificationResult:
        """Создание результата ошибки"""
        return VerificationResult(
            task_id="error",
            verification_level=VerificationLevel.AI_VALIDATION,
            quality_result=QualityGateResult(
                gate_name=f"ai_{analysis_type}_error",
                results=[QualityResult(
                    check_type=getattr(QualityCheckType, f"{analysis_type.upper()}_AI".replace('_', '')),
                    status=QualityStatus.ERROR,
                    message=f"AI validation failed: {error}",
                    score=0.0
                )]
            ),
            execution_time=(datetime.now() - start_time).total_seconds(),
            metadata={'error': error}
        )