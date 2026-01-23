"""
Проверка сложности кода
"""

import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..interfaces import IQualityChecker
from ..models.quality_result import QualityResult, QualityStatus, QualityCheckType

logger = logging.getLogger(__name__)


class ComplexityChecker(IQualityChecker):
    """
    Проверка цикломатической сложности кода с помощью radon
    """

    def __init__(self):
        self._config = {}
        self._max_complexity = 10
        self._warning_threshold = 15
        self._exclude_patterns = ['test_', '__pycache__', '.git']

    @property
    def name(self) -> str:
        return "Complexity Checker"

    @property
    def check_type(self) -> QualityCheckType:
        return QualityCheckType.COMPLEXITY

    @property
    def description(self) -> str:
        return "Проверяет цикломатическую сложность функций и методов с помощью radon"

    def configure(self, config: Dict[str, Any]) -> None:
        """Настройка чекера сложности"""
        self._config = config
        self._max_complexity = config.get('max_complexity', 10)
        self._warning_threshold = config.get('warning_threshold', 15)
        self._exclude_patterns = config.get('exclude_patterns', ['test_', '__pycache__', '.git'])
        logger.debug(f"Complexity checker configured with max_complexity: {self._max_complexity}")

    async def check(self, context: Optional[Dict[str, Any]] = None) -> QualityResult:
        """
        Выполнение проверки сложности

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

            # Анализируем сложность кода
            complexity_data = await self._analyze_complexity(project_path)

            execution_time = time.time() - start_time

            if complexity_data is None:
                return QualityResult(
                    check_type=self.check_type,
                    status=QualityStatus.ERROR,
                    message="Failed to analyze code complexity",
                    execution_time=execution_time
                )

            avg_complexity = complexity_data['average_complexity']
            high_complexity_count = complexity_data['high_complexity_count']
            warning_complexity_count = complexity_data['warning_complexity_count']

            # Вычисляем скор (0.0 - 1.0, где 1.0 - отлично)
            score = max(0.0, 1.0 - (avg_complexity / self._max_complexity))

            # Определяем статус
            if avg_complexity <= self._max_complexity and high_complexity_count == 0:
                status = QualityStatus.PASSED
                message = f"Average complexity {avg_complexity:.1f} within limit of {self._max_complexity}"
            elif avg_complexity <= self._max_complexity * 1.2 and high_complexity_count <= 2:
                status = QualityStatus.WARNING
                message = f"Average complexity {avg_complexity:.1f} slightly above limit, {high_complexity_count} functions with high complexity"
            else:
                status = QualityStatus.FAILED
                message = f"Average complexity {avg_complexity:.1f} exceeds limit of {self._max_complexity}, {high_complexity_count} functions too complex"

            return QualityResult(
                check_type=self.check_type,
                status=status,
                message=message,
                score=score,
                threshold=1.0 - (self._max_complexity / 20.0),  # Нормализованный порог
                execution_time=execution_time,
                details={
                    'average_complexity': avg_complexity,
                    'max_complexity': self._max_complexity,
                    'high_complexity_functions': high_complexity_count,
                    'warning_complexity_functions': warning_complexity_count,
                    'total_functions': complexity_data['total_functions'],
                    'complex_functions': complexity_data['complex_functions'][:5],  # Топ 5 самых сложных
                    'project_path': str(project_path)
                }
            )

        except Exception as e:
            logger.error(f"Error in complexity check: {e}")
            return QualityResult(
                check_type=self.check_type,
                status=QualityStatus.ERROR,
                message=f"Failed to check complexity: {str(e)}",
                execution_time=time.time() - start_time
            )

    async def _analyze_complexity(self, project_path: Path) -> Optional[Dict[str, Any]]:
        """
        Анализ цикломатической сложности с помощью radon

        Args:
            project_path: Путь к проекту

        Returns:
            Данные о сложности кода или None при ошибке
        """
        try:
            # Импортируем radon здесь, чтобы избежать ошибок если его нет
            from radon.complexity import cc_visit, cc_rank
            from radon.cli import Config

            # Находим все Python файлы в src директории
            python_files = self._find_python_files(project_path)

            if not python_files:
                logger.warning(f"No Python files found in {project_path}")
                return {
                    'average_complexity': 0.0,
                    'high_complexity_count': 0,
                    'warning_complexity_count': 0,
                    'total_functions': 0,
                    'complex_functions': []
                }

            all_complexities = []
            complex_functions = []

            # Анализируем каждый файл
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()

                    # Получаем сложность для всех функций/классов в файле
                    blocks = cc_visit(code)

                    for block in blocks:
                        complexity = block.complexity
                        all_complexities.append(complexity)

                        # Сохраняем информацию о сложных функциях
                        if complexity >= self._max_complexity:
                            complex_functions.append({
                                'name': block.name,
                                'complexity': complexity,
                                'file': str(file_path.relative_to(project_path)),
                                'line': block.lineno,
                                'rank': cc_rank(complexity)
                            })

                except Exception as e:
                    logger.warning(f"Error analyzing {file_path}: {e}")
                    continue

            if not all_complexities:
                return {
                    'average_complexity': 0.0,
                    'high_complexity_count': 0,
                    'warning_complexity_count': 0,
                    'total_functions': 0,
                    'complex_functions': []
                }

            avg_complexity = sum(all_complexities) / len(all_complexities)
            high_complexity_count = sum(1 for c in all_complexities if c >= self._max_complexity)
            warning_complexity_count = sum(1 for c in all_complexities if self._max_complexity <= c < self._warning_threshold)

            # Сортируем по сложности (наиболее сложные первыми)
            complex_functions.sort(key=lambda x: x['complexity'], reverse=True)

            return {
                'average_complexity': avg_complexity,
                'high_complexity_count': high_complexity_count,
                'warning_complexity_count': warning_complexity_count,
                'total_functions': len(all_complexities),
                'complex_functions': complex_functions
            }

        except ImportError:
            logger.error("radon not installed, cannot analyze complexity")
            return None
        except Exception as e:
            logger.error(f"Error analyzing complexity: {e}")
            return None

    def _find_python_files(self, project_path: Path) -> List[Path]:
        """
        Поиск Python файлов в проекте

        Args:
            project_path: Путь к проекту

        Returns:
            Список путей к Python файлам
        """
        python_files = []

        # Ищем в src директории
        src_dir = project_path / 'src'
        if src_dir.exists():
            for root, dirs, files in os.walk(src_dir):
                # Исключаем паттерны
                dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self._exclude_patterns)]

                for file in files:
                    if file.endswith('.py'):
                        file_path = Path(root) / file
                        # Дополнительная проверка на исключения в имени файла
                        if not any(pattern in file for pattern in self._exclude_patterns):
                            python_files.append(file_path)

        return python_files

    def get_default_threshold(self) -> float:
        return 0.5  # Нормализованный порог для сложности 10

    def is_configurable(self) -> bool:
        return True

    def get_supported_file_types(self) -> list[str]:
        return ['.py']

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Валидация конфигурации"""
        max_comp = config.get('max_complexity', 10)
        return isinstance(max_comp, int) and max_comp > 0