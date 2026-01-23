"""
Проверка покрытия кода тестами
"""

import asyncio
import logging
import os
import sys
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
import xml.etree.ElementTree as ET

from ..interfaces import IQualityChecker
from ..models.quality_result import QualityResult, QualityStatus, QualityCheckType

logger = logging.getLogger(__name__)


class CoverageChecker(IQualityChecker):
    """
    Проверка покрытия кода тестами с помощью pytest-cov
    """

    def __init__(self):
        self._config = {}
        self._min_coverage = 80.0
        self._test_command = "pytest"
        self._coverage_command = "coverage"

    @property
    def name(self) -> str:
        return "Coverage Checker"

    @property
    def check_type(self) -> QualityCheckType:
        return QualityCheckType.COVERAGE

    @property
    def description(self) -> str:
        return "Проверяет покрытие кода тестами с помощью pytest-cov"

    def configure(self, config: Dict[str, Any]) -> None:
        """Настройка чекера покрытия"""
        self._config = config
        self._min_coverage = config.get('min_coverage', 80.0)
        self._test_command = config.get('test_command', 'pytest')
        self._coverage_command = config.get('coverage_command', 'coverage')
        logger.debug(f"Coverage checker configured with min_coverage: {self._min_coverage}")

    async def check(self, context: Optional[Dict[str, Any]] = None) -> QualityResult:
        """
        Выполнение проверки покрытия

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

            # Запускаем тесты с покрытием
            coverage_data = await self._run_coverage_tests(project_path)

            execution_time = time.time() - start_time

            if coverage_data is None:
                return QualityResult(
                    check_type=self.check_type,
                    status=QualityStatus.ERROR,
                    message="Failed to run coverage tests",
                    execution_time=execution_time
                )

            coverage_percentage = coverage_data['total_coverage']
            score = min(coverage_percentage / 100.0, 1.0)

            # Определяем статус на основе покрытия
            if coverage_percentage >= self._min_coverage:
                status = QualityStatus.PASSED
                message = f"Coverage {coverage_percentage:.1f}% meets minimum requirement of {self._min_coverage}%"
            elif coverage_percentage >= self._min_coverage * 0.8:  # 80% от минимума
                status = QualityStatus.WARNING
                message = f"Coverage {coverage_percentage:.1f}% slightly below minimum requirement of {self._min_coverage}%"
            else:
                status = QualityStatus.FAILED
                message = f"Coverage {coverage_percentage:.1f}% below minimum requirement of {self._min_coverage}%"

            return QualityResult(
                check_type=self.check_type,
                status=status,
                message=message,
                score=score,
                threshold=self._min_coverage / 100.0,
                execution_time=execution_time,
                details={
                    'coverage_percentage': coverage_percentage,
                    'min_coverage': self._min_coverage,
                    'files_covered': coverage_data['files_covered'],
                    'total_files': coverage_data['total_files'],
                    'missing_lines': coverage_data.get('missing_lines', {}),
                    'project_path': str(project_path)
                }
            )

        except Exception as e:
            logger.error(f"Error in coverage check: {e}")
            return QualityResult(
                check_type=self.check_type,
                status=QualityStatus.ERROR,
                message=f"Failed to check coverage: {str(e)}",
                execution_time=time.time() - start_time
            )

    async def _run_coverage_tests(self, project_path: Path) -> Optional[Dict[str, Any]]:
        """
        Запуск тестов с покрытием и сбор результатов

        Args:
            project_path: Путь к проекту

        Returns:
            Данные о покрытии или None при ошибке
        """
        try:
            # Создаем временную директорию для файлов покрытия
            with tempfile.TemporaryDirectory() as temp_dir:
                coverage_file = Path(temp_dir) / ".coverage"
                coverage_xml = Path(temp_dir) / "coverage.xml"

                # Запускаем pytest с coverage
                env = os.environ.copy()
                env['COVERAGE_FILE'] = str(coverage_file)

                # Команда запуска тестов с покрытием
                cmd = [
                    sys.executable, "-m", "pytest",
                    "--cov=src",
                    "--cov-report=xml",
                    "--cov-report=term-missing",
                    f"--cov-report=xml:{coverage_xml}",
                    "test/",
                    "-v"
                ]

                logger.debug(f"Running coverage command: {' '.join(cmd)}")
                logger.debug(f"Working directory: {project_path}")

                # Запускаем процесс
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(project_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )

                stdout, stderr = await process.communicate()

                # Логируем вывод
                if stdout:
                    logger.debug(f"Coverage stdout: {stdout.decode()}")
                if stderr:
                    logger.debug(f"Coverage stderr: {stderr.decode()}")

                if process.returncode != 0:
                    logger.warning(f"Coverage tests failed with return code {process.returncode}")
                    # Даже при неудачных тестах пытаемся получить покрытие

                # Парсим XML отчет покрытия
                if coverage_xml.exists():
                    return self._parse_coverage_xml(coverage_xml)
                else:
                    # Если XML не найден, пытаемся извлечь данные из stdout
                    return self._extract_coverage_from_output(stdout.decode(), stderr.decode())

        except Exception as e:
            logger.error(f"Error running coverage tests: {e}")
            return None

    def _parse_coverage_xml(self, xml_file: Path) -> Dict[str, Any]:
        """
        Парсинг XML отчета покрытия

        Args:
            xml_file: Путь к XML файлу

        Returns:
            Данные о покрытии
        """
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Общее покрытие
            total_coverage = float(root.get('line-rate', '0')) * 100

            # Данные по файлам
            files_data = {}
            total_files = 0
            covered_files = 0

            for package in root.findall('.//package'):
                for cls in package.findall('classes/class'):
                    filename = cls.get('filename', '')
                    if filename.startswith('src/'):  # Только исходный код
                        total_files += 1
                        line_rate = float(cls.get('line-rate', '0'))
                        if line_rate > 0:
                            covered_files += 1

                        # Собираем информацию о непокрытых строках
                        lines = cls.find('lines')
                        if lines is not None:
                            missing_lines = []
                            for line in lines.findall('line'):
                                hits = int(line.get('hits', '0'))
                                number = int(line.get('number', '0'))
                                if hits == 0:
                                    missing_lines.append(number)

                            if missing_lines:
                                files_data[filename] = missing_lines[:10]  # Первые 10 непокрытых строк

            return {
                'total_coverage': total_coverage,
                'files_covered': covered_files,
                'total_files': total_files,
                'missing_lines': files_data
            }

        except Exception as e:
            logger.error(f"Error parsing coverage XML: {e}")
            return {
                'total_coverage': 0.0,
                'files_covered': 0,
                'total_files': 0,
                'missing_lines': {}
            }

    def _extract_coverage_from_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """
        Извлечение данных о покрытии из вывода pytest-cov

        Args:
            stdout: Стандартный вывод
            stderr: Стандартный вывод ошибок

        Returns:
            Данные о покрытии
        """
        output = stdout + stderr

        # Ищем строку типа "TOTAL 85% 123 45 78"
        import re
        coverage_match = re.search(r'TOTAL\s+(\d+)%', output)
        if coverage_match:
            total_coverage = float(coverage_match.group(1))
        else:
            # Ищем другие паттерны
            coverage_match = re.search(r'(\d+(?:\.\d+)?)%', output)
            total_coverage = float(coverage_match.group(1)) if coverage_match else 0.0

        return {
            'total_coverage': total_coverage,
            'files_covered': 0,  # Не можем определить из вывода
            'total_files': 0,
            'missing_lines': {}
        }

    def get_default_threshold(self) -> float:
        return 0.8  # 80%

    def is_configurable(self) -> bool:
        return True

    def get_supported_file_types(self) -> list[str]:
        return ['.py']

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Валидация конфигурации"""
        min_cov = config.get('min_coverage', 80.0)
        return isinstance(min_cov, (int, float)) and 0 <= min_cov <= 100