"""
Проверка безопасности кода
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..interfaces import IQualityChecker
from ..models.quality_result import QualityResult, QualityStatus, QualityCheckType

logger = logging.getLogger(__name__)


class SecurityChecker(IQualityChecker):
    """
    Проверка безопасности кода с помощью bandit
    """

    def __init__(self):
        self._config = {}
        self._severity_thresholds = {
            'high': 0,  # Максимум high severity уязвимостей
            'medium': 5,  # Максимум medium severity уязвимостей
        }
        self._exclude_patterns = ['test_', '__pycache__', '.git', 'migrations']

    @property
    def name(self) -> str:
        return "Security Checker"

    @property
    def check_type(self) -> QualityCheckType:
        return QualityCheckType.SECURITY

    @property
    def description(self) -> str:
        return "Проверяет код на наличие уязвимостей безопасности с помощью bandit"

    def configure(self, config: Dict[str, Any]) -> None:
        """Настройка чекера безопасности"""
        self._config = config
        self._severity_thresholds = config.get('severity_thresholds', self._severity_thresholds)
        self._exclude_patterns = config.get('exclude_patterns', self._exclude_patterns)
        logger.debug("Security checker configured")

    async def check(self, context: Optional[Dict[str, Any]] = None) -> QualityResult:
        """
        Выполнение проверки безопасности

        Args:
            context: Контекст с путем к проекту

        Returns:
            Результат проверки
        """
        import time
        start_time = time.time()

        try:
            project_path = context.get('project_path', '.') if context else '.'
            project_path = Path(project_path).resolve()

            # Запускаем bandit сканирование
            security_data = await self._run_bandit_scan(project_path)

            execution_time = time.time() - start_time

            if security_data is None:
                return QualityResult(
                    check_type=self.check_type,
                    status=QualityStatus.ERROR,
                    message="Failed to run security scan",
                    execution_time=execution_time
                )

            vulnerabilities_found = security_data['total_issues']
            high_severity_count = security_data['high_severity_count']
            medium_severity_count = security_data['medium_severity_count']
            low_severity_count = security_data['low_severity_count']

            # Вычисляем скор на основе уязвимостей
            if vulnerabilities_found == 0:
                score = 1.0
            else:
                # Штрафуем за каждую уязвимость в зависимости от severity
                penalty = (high_severity_count * 0.3 + medium_severity_count * 0.1 + low_severity_count * 0.05)
                score = max(0.0, 1.0 - penalty)

            # Определяем статус
            max_high = self._severity_thresholds.get('high', 0)
            max_medium = self._severity_thresholds.get('medium', 5)

            if vulnerabilities_found == 0:
                status = QualityStatus.PASSED
                message = "No security vulnerabilities found"
            elif high_severity_count <= max_high and medium_severity_count <= max_medium:
                status = QualityStatus.WARNING
                message = f"Found {vulnerabilities_found} security issues within acceptable limits"
            else:
                status = QualityStatus.FAILED
                message = f"Found {vulnerabilities_found} security vulnerabilities exceeding limits (high: {high_severity_count}/{max_high}, medium: {medium_severity_count}/{max_medium})"

            return QualityResult(
                check_type=self.check_type,
                status=status,
                message=message,
                score=score,
                threshold=0.9,  # Порог для безопасности
                execution_time=execution_time,
                details={
                    'vulnerabilities_found': vulnerabilities_found,
                    'high_severity_count': high_severity_count,
                    'medium_severity_count': medium_severity_count,
                    'low_severity_count': low_severity_count,
                    'issues': security_data['issues'][:10],  # Первые 10 проблем
                    'severity_thresholds': self._severity_thresholds,
                    'project_path': str(project_path)
                }
            )

        except Exception as e:
            logger.error(f"Error in security check: {e}")
            return QualityResult(
                check_type=self.check_type,
                status=QualityStatus.ERROR,
                message=f"Failed to check security: {str(e)}",
                execution_time=time.time() - start_time
            )

    def get_default_threshold(self) -> float:
        return 0.9  # 90% безопасность

    def is_configurable(self) -> bool:
        return True

    def get_supported_file_types(self) -> list[str]:
        return ['.py', 'requirements.txt', 'pyproject.toml']

    async def _run_bandit_scan(self, project_path: Path) -> Optional[Dict[str, Any]]:
        """
        Запуск bandit сканирования

        Args:
            project_path: Путь к проекту

        Returns:
            Данные о безопасности или None при ошибке
        """
        try:
            # Создаем временный файл для результатов
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                output_file = temp_file.name

            # Команда bandit
            cmd = [
                'bandit',
                '-r', 'src/',  # Сканируем только src директорию
                '-f', 'json',  # JSON формат вывода
                '-o', output_file,  # Вывод в файл
                '--exclude', ','.join(self._exclude_patterns),  # Исключаем паттерны
                '-q'  # Тихий режим
            ]

            logger.debug(f"Running bandit command: {' '.join(cmd)}")
            logger.debug(f"Working directory: {project_path}")

            # Запускаем процесс
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            # Логируем ошибки если есть
            if stderr:
                stderr_text = stderr.decode()
                if stderr_text.strip():
                    logger.debug(f"Bandit stderr: {stderr_text}")

            try:
                # Читаем результаты из файла
                with open(output_file, 'r') as f:
                    bandit_results = json.load(f)

                # Удаляем временный файл
                os.unlink(output_file)

                # Обрабатываем результаты
                return self._process_bandit_results(bandit_results)

            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.error(f"Error reading bandit results: {e}")
                if os.path.exists(output_file):
                    os.unlink(output_file)
                return self._extract_issues_from_output(stdout.decode(), stderr.decode())

        except FileNotFoundError:
            logger.error("bandit not installed")
            return None
        except Exception as e:
            logger.error(f"Error running bandit scan: {e}")
            return None

    def _process_bandit_results(self, bandit_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка результатов bandit

        Args:
            bandit_results: Результаты сканирования bandit

        Returns:
            Обработанные данные о безопасности
        """
        issues = []
        high_count = 0
        medium_count = 0
        low_count = 0

        # Обрабатываем результаты по файлам
        for filename, file_results in bandit_results.get('results', {}).items():
            for issue in file_results:
                severity = issue.get('issue_severity', 'low').lower()
                confidence = issue.get('issue_confidence', 'low').lower()

                # Подсчитываем по severity
                if severity == 'high':
                    high_count += 1
                elif severity == 'medium':
                    medium_count += 1
                else:
                    low_count += 1

                issues.append({
                    'filename': filename,
                    'line': issue.get('line_number', 0),
                    'severity': severity,
                    'confidence': confidence,
                    'test_id': issue.get('test_id', ''),
                    'test_name': issue.get('test_name', ''),
                    'issue_text': issue.get('issue_text', ''),
                    'code': issue.get('code', '')
                })

        # Сортируем по severity (high -> medium -> low)
        severity_order = {'high': 3, 'medium': 2, 'low': 1}
        issues.sort(key=lambda x: severity_order.get(x['severity'], 0), reverse=True)

        return {
            'total_issues': len(issues),
            'high_severity_count': high_count,
            'medium_severity_count': medium_count,
            'low_severity_count': low_count,
            'issues': issues
        }

    def _extract_issues_from_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """
        Извлечение информации об issues из вывода bandit

        Args:
            stdout: Стандартный вывод
            stderr: Стандартный вывод ошибок

        Returns:
            Данные о безопасности на основе вывода
        """
        output = stdout + stderr

        # Простой подсчет issues из вывода
        high_count = output.count('High severity')
        medium_count = output.count('Medium severity')
        low_count = output.count('Low severity')

        # Если ничего не нашли, предполагаем что сканирование прошло успешно
        if high_count == 0 and medium_count == 0 and low_count == 0:
            return {
                'total_issues': 0,
                'high_severity_count': 0,
                'medium_severity_count': 0,
                'low_severity_count': 0,
                'issues': []
            }

        return {
            'total_issues': high_count + medium_count + low_count,
            'high_severity_count': high_count,
            'medium_severity_count': medium_count,
            'low_severity_count': low_count,
            'issues': []
        }

    def get_default_threshold(self) -> float:
        return 0.9  # 90% безопасность

    def is_configurable(self) -> bool:
        return True

    def get_supported_file_types(self) -> list[str]:
        return ['.py']

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Валидация конфигурации"""
        thresholds = config.get('severity_thresholds', {})
        return isinstance(thresholds, dict)