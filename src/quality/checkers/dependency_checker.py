"""
Проверка зависимостей проекта
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from ..interfaces import IQualityChecker
from ..models.quality_result import QualityResult, QualityCheckType, QualityStatus

logger = logging.getLogger(__name__)


class DependencyChecker(IQualityChecker):
    """
    Проверка зависимостей проекта
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация чекера зависимостей

        Args:
            config: Конфигурация чекера
        """
        self.config = config or {}
        self.check_imports = self.config.get('check_imports', True)
        self.check_requirements = self.config.get('check_requirements', True)
        self.check_conflicts = self.config.get('check_conflicts', True)
        self.requirements_files = self.config.get('requirements_files', ['requirements.txt', 'pyproject.toml'])

    @property
    def name(self) -> str:
        """Имя проверки"""
        return "dependency_checker"

    @property
    def check_type(self) -> QualityCheckType:
        """Тип проверки"""
        return QualityCheckType.DEPENDENCY

    @property
    def description(self) -> str:
        """Описание проверки"""
        return "Checks project dependencies for completeness and conflicts"

    def get_default_threshold(self) -> float:
        """Порог по умолчанию"""
        return 0.7

    def is_configurable(self) -> bool:
        """Поддерживает настройку"""
        return True

    def get_supported_file_types(self) -> list[str]:
        """Поддерживаемые типы файлов"""
        return ['.py', '.txt', '.toml']

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Валидация конфигурации"""
        if 'check_imports' in config and not isinstance(config['check_imports'], bool):
            return False
        if 'check_requirements' in config and not isinstance(config['check_requirements'], bool):
            return False
        if 'check_conflicts' in config and not isinstance(config['check_conflicts'], bool):
            return False
        if 'requirements_files' in config and not isinstance(config['requirements_files'], list):
            return False
        return True

    async def check(self, context: Optional[Dict[str, Any]] = None) -> QualityResult:
        """
        Выполнение проверки зависимостей

        Args:
            context: Контекст выполнения

        Returns:
            Результат проверки
        """
        import time
        start_time = time.time()

        try:
            project_path = context.get('project_path', '.') if context else '.'
            project_dir = Path(project_path)

            issues = []
            score = 1.0

            # Проверка наличия файлов зависимостей
            if self.check_requirements:
                requirements_found = False
                for req_file in self.requirements_files:
                    if (project_dir / req_file).exists():
                        requirements_found = True
                        break

                if not requirements_found:
                    issues.append("No requirements file found (requirements.txt or pyproject.toml)")
                    score -= 0.3

            # Проверка импортов
            if self.check_imports:
                import_issues = await self._check_imports(project_dir)
                issues.extend(import_issues)
                if import_issues:
                    score -= 0.4

            # Проверка конфликтов зависимостей
            if self.check_conflicts:
                conflict_issues = await self._check_dependency_conflicts(project_dir)
                issues.extend(conflict_issues)
                if conflict_issues:
                    score -= 0.3

            # Определение статуса
            if score >= 0.8:
                status = QualityStatus.PASSED
            elif score >= 0.6:
                status = QualityStatus.WARNING
            else:
                status = QualityStatus.FAILED

            message = "Dependency check completed"
            if issues:
                message += f" with {len(issues)} issues: " + "; ".join(issues[:3])
                if len(issues) > 3:
                    message += f" and {len(issues) - 3} more"

            return QualityResult(
                check_type=QualityCheckType.DEPENDENCY,
                status=status,
                message=message,
                score=max(0.0, score),
                execution_time=time.time() - start_time,
                details={
                    'issues': issues,
                    'requirements_found': requirements_found if self.check_requirements else None
                }
            )

        except Exception as e:
            logger.error(f"Error during dependency check: {e}")
            return QualityResult(
                check_type=QualityCheckType.DEPENDENCY,
                status=QualityStatus.ERROR,
                message=f"Dependency check failed: {str(e)}",
                score=0.0,
                execution_time=time.time() - start_time
            )

    async def _check_imports(self, project_dir: Path) -> list[str]:
        """
        Проверка корректности импортов в Python файлах

        Args:
            project_dir: Директория проекта

        Returns:
            Список проблем с импортами
        """
        issues = []

        try:
            # Ищем Python файлы
            python_files = list(project_dir.rglob("*.py"))
            python_files = [f for f in python_files if not str(f).startswith(str(project_dir / "test"))]

            if not python_files:
                return issues

            # Проверяем импорты в каждом файле
            for py_file in python_files[:10]:  # Ограничиваем для производительности
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Простая проверка синтаксиса импортов
                    lines = content.split('\n')
                    for i, line in enumerate(lines[:50]):  # Проверяем первые 50 строк
                        line = line.strip()
                        if line.startswith(('import ', 'from ')):
                            # Проверяем базовую синтаксическую корректность
                            if 'import' in line and ('(' in line or ')' in line):
                                if not (line.count('(') == line.count(')')):
                                    issues.append(f"Invalid import syntax in {py_file.name}:{i+1}")

                except Exception as e:
                    logger.debug(f"Could not check imports in {py_file}: {e}")

        except Exception as e:
            issues.append(f"Import check failed: {str(e)}")

        return issues

    async def _check_dependency_conflicts(self, project_dir: Path) -> list[str]:
        """
        Проверка конфликтов зависимостей

        Args:
            project_dir: Директория проекта

        Returns:
            Список конфликтов зависимостей
        """
        issues = []

        try:
            # Проверяем наличие pip-tools или poetry для управления зависимостями
            has_pip_tools = (project_dir / "requirements.in").exists()
            has_poetry = (project_dir / "pyproject.toml").exists() and "poetry" in (project_dir / "pyproject.toml").read_text()

            if not (has_pip_tools or has_poetry):
                issues.append("No dependency management tool detected (pip-tools or poetry recommended)")

            # Простая проверка на наличие устаревших пакетов
            if (project_dir / "requirements.txt").exists():
                try:
                    result = subprocess.run([
                        sys.executable, "-m", "pip", "list", "--outdated", "--format=json"
                    ], capture_output=True, text=True, timeout=30)

                    if result.returncode == 0 and result.stdout.strip():
                        import json
                        outdated = json.loads(result.stdout)
                        if outdated:
                            issues.append(f"{len(outdated)} outdated packages found")

                except Exception as e:
                    logger.debug(f"Could not check for outdated packages: {e}")

        except Exception as e:
            issues.append(f"Dependency conflict check failed: {str(e)}")

        return issues

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настройка чекера

        Args:
            config: Конфигурация
        """
        self.config.update(config)
        self.check_imports = self.config.get('check_imports', True)
        self.check_requirements = self.config.get('check_requirements', True)
        self.check_conflicts = self.config.get('check_conflicts', True)
        self.requirements_files = self.config.get('requirements_files', ['requirements.txt', 'pyproject.toml'])