"""
Проверка стиля кода
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional
from pathlib import Path

from ..interfaces import IQualityChecker
from ..models.quality_result import QualityResult, QualityStatus, QualityCheckType

logger = logging.getLogger(__name__)


class StyleChecker(IQualityChecker):
    """
    Проверка стиля кода с помощью ruff
    """

    def __init__(self):
        self._config = {}
        self._max_violations = 50  # Максимум нарушений
        self._max_files_with_violations = 10  # Максимум файлов с нарушениями
        self._exclude_patterns = ['__pycache__', '.git', 'migrations', 'test_']

    @property
    def name(self) -> str:
        return "Style Checker"

    @property
    def check_type(self) -> QualityCheckType:
        return QualityCheckType.STYLE

    @property
    def description(self) -> str:
        return "Проверяет соблюдение стандартов кода с помощью ruff"

    def configure(self, config: Dict[str, Any]) -> None:
        """Настройка чекера стиля"""
        self._config = config
        self._max_violations = config.get('max_violations', 50)
        self._max_files_with_violations = config.get('max_files_with_violations', 10)
        self._exclude_patterns = config.get('exclude_patterns', self._exclude_patterns)
        logger.debug("Style checker configured")

    async def check(self, context: Optional[Dict[str, Any]] = None) -> QualityResult:
        """
        Выполнение проверки стиля

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

            # Запускаем проверку стиля с помощью ruff
            style_data = await self._run_ruff_check(project_path)

            execution_time = time.time() - start_time

            if style_data is None:
                return QualityResult(
                    check_type=self.check_type,
                    status=QualityStatus.ERROR,
                    message="Failed to run style check",
                    execution_time=execution_time
                )

            total_violations = style_data['total_violations']
            files_with_violations = style_data['files_with_violations']
            total_files = style_data['total_files']

            # Вычисляем скор на основе нарушений
            violation_score = min(total_violations / self._max_violations, 1.0)
            file_score = min(files_with_violations / self._max_files_with_violations, 1.0)
            score = max(0.0, 1.0 - (violation_score + file_score) / 2)

            # Определяем статус
            if total_violations == 0:
                status = QualityStatus.PASSED
                message = "Code style is perfect - no violations found"
            elif total_violations <= self._max_violations // 2 and files_with_violations <= self._max_files_with_violations // 2:
                status = QualityStatus.WARNING
                message = f"Minor style violations: {total_violations} issues in {files_with_violations} files"
            else:
                status = QualityStatus.FAILED
                message = f"Significant style violations: {total_violations} issues in {files_with_violations} out of {total_files} files"

            return QualityResult(
                check_type=self.check_type,
                status=status,
                message=message,
                score=score,
                threshold=0.8,  # Порог для стиля
                execution_time=execution_time,
                details={
                    'total_violations': total_violations,
                    'files_with_violations': files_with_violations,
                    'total_files': total_files,
                    'violations': style_data['violations'][:20],  # Первые 20 нарушений
                    'violation_types': style_data['violation_types'],
                    'max_violations': self._max_violations,
                    'max_files_with_violations': self._max_files_with_violations,
                    'project_path': str(project_path)
                }
            )

        except Exception as e:
            logger.error(f"Error in style check: {e}")
            return QualityResult(
                check_type=self.check_type,
                status=QualityStatus.ERROR,
                message=f"Failed to check style: {str(e)}",
                execution_time=time.time() - start_time
            )

    def get_default_threshold(self) -> float:
        return 0.9  # 90% чистоты стиля

    def is_configurable(self) -> bool:
        return True

    def get_supported_file_types(self) -> list[str]:
        return ['.py']

    async def _run_ruff_check(self, project_path: Path) -> Optional[Dict[str, Any]]:
        """
        Запуск проверки стиля с помощью ruff

        Args:
            project_path: Путь к проекту

        Returns:
            Данные о стиле кода или None при ошибке
        """
        try:
            # Команда ruff check
            cmd = [
                'ruff',
                'check',
                'src/',  # Проверяем только src директорию
                '--output-format=json',  # JSON формат вывода
                '--exclude', ','.join(self._exclude_patterns),  # Исключаем паттерны
            ]

            logger.debug(f"Running ruff command: {' '.join(cmd)}")
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
                    logger.debug(f"Ruff stderr: {stderr_text}")

            stdout_text = stdout.decode()

            if process.returncode == 0:
                # Нет нарушений
                total_files = self._count_python_files(project_path)
                return {
                    'total_violations': 0,
                    'files_with_violations': 0,
                    'total_files': total_files,
                    'violations': [],
                    'violation_types': {}
                }
            elif process.returncode in (1, 2):  # 1 - нарушения найдены, 2 - синтаксические ошибки
                # Парсим JSON вывод
                return self._parse_ruff_output(stdout_text)
            else:
                logger.error(f"Ruff failed with return code {process.returncode}")
                return None

        except FileNotFoundError:
            logger.error("ruff not installed")
            return None
        except Exception as e:
            logger.error(f"Error running ruff check: {e}")
            return None

    def _parse_ruff_output(self, output: str) -> Dict[str, Any]:
        """
        Парсинг вывода ruff

        Args:
            output: JSON вывод ruff

        Returns:
            Обработанные данные о нарушениях
        """
        try:
            violations = []
            violation_types = {}
            files_with_violations = set()

            # Разбираем JSON по строкам
            for line in output.strip().split('\n'):
                if line.strip():
                    try:
                        violation = json.loads(line.strip())
                        violations.append({
                            'code': violation.get('code', ''),
                            'message': violation.get('message', ''),
                            'filename': violation.get('filename', ''),
                            'line': violation.get('location', {}).get('row', 0),
                            'column': violation.get('location', {}).get('column', 0),
                            'category': violation.get('code', '')[:1] if violation.get('code') else 'U'  # F, E, W, etc.
                        })

                        # Подсчитываем типы нарушений
                        code = violation.get('code', 'UNK')
                        violation_types[code] = violation_types.get(code, 0) + 1

                        # Добавляем файл в список с нарушениями
                        files_with_violations.add(violation.get('filename', ''))

                    except json.JSONDecodeError:
                        continue

            return {
                'total_violations': len(violations),
                'files_with_violations': len(files_with_violations),
                'total_files': self._count_python_files(Path('.')),
                'violations': violations,
                'violation_types': violation_types
            }

        except Exception as e:
            logger.error(f"Error parsing ruff output: {e}")
            return {
                'total_violations': 0,
                'files_with_violations': 0,
                'total_files': 0,
                'violations': [],
                'violation_types': {}
            }

    def _count_python_files(self, project_path: Path) -> int:
        """
        Подсчет Python файлов в проекте

        Args:
            project_path: Путь к проекту

        Returns:
            Количество Python файлов
        """
        count = 0
        src_dir = project_path / 'src'
        if src_dir.exists():
            for root, dirs, files in os.walk(src_dir):
                # Исключаем паттерны
                dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self._exclude_patterns)]

                for file in files:
                    if file.endswith('.py') and not any(pattern in file for pattern in self._exclude_patterns):
                        count += 1

        return count

    def get_default_threshold(self) -> float:
        return 0.8  # 80% чистоты стиля

    def is_configurable(self) -> bool:
        return True

    def get_supported_file_types(self) -> list[str]:
        return ['.py']

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Валидация конфигурации"""
        max_violations = config.get('max_violations', 50)
        max_files = config.get('max_files_with_violations', 10)
        return isinstance(max_violations, int) and isinstance(max_files, int) and max_violations > 0 and max_files > 0