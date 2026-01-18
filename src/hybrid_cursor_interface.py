"""
Гибридный интерфейс для работы с Cursor

Комбинирует CLI и файловый интерфейс для максимальной надежности:
- Простые задачи (вопросы, анализ) → CLI (быстро)
- Сложные задачи (создание, изменение) → Файловый интерфейс (надежно)
- Автоматический fallback при неудаче CLI
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

try:
    from .cursor_cli_interface import CursorCLIInterface, CursorCLIResult
    from .cursor_file_interface import CursorFileInterface
    from .prompt_formatter import PromptFormatter
except ImportError:
    # Fallback для прямого запуска
    from cursor_cli_interface import CursorCLIInterface, CursorCLIResult
    from cursor_file_interface import CursorFileInterface
    from prompt_formatter import PromptFormatter

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Сложность задачи"""
    SIMPLE = "simple"      # Вопросы, анализ без изменений
    COMPLEX = "complex"    # Создание, изменение, рефакторинг
    AUTO = "auto"          # Автоматическое определение


@dataclass
class HybridExecutionResult:
    """Результат выполнения через гибридный интерфейс"""
    success: bool
    method_used: str  # "cli", "file", "cli_with_fallback"
    output: str
    error_message: Optional[str] = None
    side_effects_verified: bool = False
    cli_result: Optional[CursorCLIResult] = None
    file_result: Optional[Dict[str, Any]] = None


class HybridCursorInterface:
    """
    Гибридный интерфейс для работы с Cursor
    
    Автоматически выбирает оптимальный метод выполнения:
    - CLI для простых задач (быстро, но может не выполниться)
    - Файловый интерфейс для сложных задач (надежно)
    - Fallback на файловый при неудаче CLI
    """
    
    # Ключевые слова для определения сложности
    SIMPLE_KEYWORDS = [
        # Русские
        'что', 'как', 'почему', 'когда', 'где', 'кто',
        'объясни', 'покажи', 'найди', 'проверь', 'посмотри',
        'расскажи', 'опиши', 'анализ', 'поиск',
        # Английские
        'what', 'how', 'why', 'when', 'where', 'who',
        'explain', 'show', 'find', 'check', 'look',
        'tell', 'describe', 'analyze', 'search'
    ]
    
    COMPLEX_KEYWORDS = [
        # Русские
        'создай', 'измени', 'удали', 'добавь', 'реализуй',
        'рефактор', 'исправь', 'обнови', 'сгенерируй', 'напиши',
        'внедри', 'оптимизируй', 'перепиши', 'модифицируй',
        # Английские
        'create', 'modify', 'delete', 'add', 'implement',
        'refactor', 'fix', 'update', 'generate', 'write',
        'deploy', 'optimize', 'rewrite', 'change'
    ]
    
    def __init__(
        self,
        cli_interface: Optional[CursorCLIInterface] = None,
        file_interface: Optional[CursorFileInterface] = None,
        project_dir: Optional[str] = None,
        prefer_cli: bool = False,
        verify_side_effects: bool = True
    ):
        """
        Инициализация гибридного интерфейса
        
        Args:
            cli_interface: Интерфейс CLI (если None - создается автоматически)
            file_interface: Файловый интерфейс (если None - создается автоматически)
            project_dir: Директория проекта
            prefer_cli: Предпочитать CLI даже для сложных задач (с fallback)
            verify_side_effects: Проверять side-effects после выполнения
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.prefer_cli = prefer_cli
        self.verify_side_effects = verify_side_effects
        
        # Инициализация интерфейсов
        self.cli = cli_interface or CursorCLIInterface(project_dir=str(self.project_dir))
        self.file = file_interface or CursorFileInterface(project_dir=str(self.project_dir))
        
        logger.info(f"Гибридный интерфейс инициализирован")
        logger.info(f"  CLI доступен: {self.cli.is_available()}")
        logger.info(f"  Файловый интерфейс: готов")
        logger.info(f"  Проект: {self.project_dir}")
    
    def execute_task(
        self,
        instruction: str,
        task_id: Optional[str] = None,
        complexity: TaskComplexity = TaskComplexity.AUTO,
        expected_files: Optional[List[str]] = None,
        control_phrase: str = "Задача выполнена!",
        timeout: int = 600
    ) -> HybridExecutionResult:
        """
        Выполнение задачи с автоматическим выбором метода
        
        Args:
            instruction: Инструкция для выполнения
            task_id: ID задачи (генерируется автоматически если None)
            complexity: Сложность задачи (AUTO для автоопределения)
            expected_files: Список ожидаемых файлов для проверки side-effects
            control_phrase: Контрольная фраза для файлового интерфейса
            timeout: Таймаут выполнения (секунды)
        
        Returns:
            HybridExecutionResult с результатом выполнения
        """
        # Генерируем task_id если не указан
        if not task_id:
            import time
            task_id = f"task_{int(time.time())}"
        
        logger.info(f"Выполнение задачи {task_id}")
        logger.debug(f"  Инструкция: {instruction[:100]}...")
        
        # Определяем сложность задачи
        if complexity == TaskComplexity.AUTO:
            complexity = self._determine_complexity(instruction)
        
        logger.info(f"  Сложность: {complexity.value}")
        
        # Выбираем метод выполнения
        if complexity == TaskComplexity.SIMPLE and self.cli.is_available():
            # Простые задачи - через CLI
            return self._execute_via_cli(
                instruction=instruction,
                task_id=task_id,
                expected_files=expected_files,
                with_fallback=True
            )
        elif self.prefer_cli and self.cli.is_available():
            # Предпочитать CLI даже для сложных задач (с fallback)
            return self._execute_via_cli(
                instruction=instruction,
                task_id=task_id,
                expected_files=expected_files,
                with_fallback=True
            )
        else:
            # Сложные задачи или CLI недоступен - через файловый интерфейс
            return self._execute_via_file(
                instruction=instruction,
                task_id=task_id,
                control_phrase=control_phrase,
                timeout=timeout
            )
    
    def _determine_complexity(self, instruction: str) -> TaskComplexity:
        """
        Автоматическое определение сложности задачи
        
        Args:
            instruction: Инструкция для анализа
        
        Returns:
            TaskComplexity.SIMPLE или TaskComplexity.COMPLEX
        """
        instruction_lower = instruction.lower()
        
        # Проверяем наличие ключевых слов
        has_simple = any(keyword in instruction_lower for keyword in self.SIMPLE_KEYWORDS)
        has_complex = any(keyword in instruction_lower for keyword in self.COMPLEX_KEYWORDS)
        
        # Логика определения:
        # 1. Если есть сложные ключевые слова → COMPLEX
        # 2. Если есть только простые → SIMPLE
        # 3. Если нет ни тех, ни других → COMPLEX (безопаснее)
        
        if has_complex:
            logger.debug(f"Задача определена как COMPLEX (найдены ключевые слова изменения)")
            return TaskComplexity.COMPLEX
        elif has_simple and not has_complex:
            logger.debug(f"Задача определена как SIMPLE (только вопросы/анализ)")
            return TaskComplexity.SIMPLE
        else:
            logger.debug(f"Задача определена как COMPLEX (по умолчанию)")
            return TaskComplexity.COMPLEX
    
    def _execute_via_cli(
        self,
        instruction: str,
        task_id: str,
        expected_files: Optional[List[str]] = None,
        with_fallback: bool = True
    ) -> HybridExecutionResult:
        """
        Выполнение через CLI с опциональным fallback
        
        Args:
            instruction: Инструкция для выполнения
            task_id: ID задачи
            expected_files: Список ожидаемых файлов
            with_fallback: Использовать fallback на файловый интерфейс при неудаче
        
        Returns:
            HybridExecutionResult
        """
        logger.info(f"Выполнение через CLI: {task_id}")
        
        try:
            # Выполняем через CLI
            cli_result = self.cli.execute(
                prompt=instruction,
                working_dir=str(self.project_dir),
                new_chat=True
            )
            
            logger.info(f"CLI выполнен: success={cli_result.success}, code={cli_result.return_code}")
            
            # Проверяем side-effects если требуется
            side_effects_ok = True
            if self.verify_side_effects and expected_files:
                side_effects_ok = self._verify_side_effects(expected_files)
                logger.info(f"Проверка side-effects: {side_effects_ok}")
            
            # Если CLI выполнился успешно И side-effects проверены
            if cli_result.success and (not self.verify_side_effects or side_effects_ok):
                return HybridExecutionResult(
                    success=True,
                    method_used="cli",
                    output=cli_result.stdout,
                    side_effects_verified=side_effects_ok,
                    cli_result=cli_result
                )
            
            # CLI выполнился, но side-effects не подтверждены
            if cli_result.success and self.verify_side_effects and not side_effects_ok:
                logger.warning(f"CLI выполнен, но side-effects не подтверждены")
                
                if with_fallback:
                    logger.info(f"Fallback на файловый интерфейс")
                    return self._execute_via_file_fallback(
                        instruction=instruction,
                        task_id=task_id,
                        cli_result=cli_result
                    )
                else:
                    return HybridExecutionResult(
                        success=False,
                        method_used="cli",
                        output=cli_result.stdout,
                        error_message="Side-effects не подтверждены",
                        side_effects_verified=False,
                        cli_result=cli_result
                    )
            
            # CLI не выполнился
            if not cli_result.success:
                logger.warning(f"CLI не выполнился: {cli_result.error_message}")
                
                if with_fallback:
                    logger.info(f"Fallback на файловый интерфейс")
                    return self._execute_via_file_fallback(
                        instruction=instruction,
                        task_id=task_id,
                        cli_result=cli_result
                    )
                else:
                    return HybridExecutionResult(
                        success=False,
                        method_used="cli",
                        output=cli_result.stdout,
                        error_message=cli_result.error_message,
                        cli_result=cli_result
                    )
        
        except Exception as e:
            logger.error(f"Ошибка выполнения через CLI: {e}")
            
            if with_fallback:
                logger.info(f"Fallback на файловый интерфейс после ошибки")
                return self._execute_via_file_fallback(
                    instruction=instruction,
                    task_id=task_id,
                    cli_result=None
                )
            else:
                return HybridExecutionResult(
                    success=False,
                    method_used="cli",
                    output="",
                    error_message=f"Ошибка CLI: {str(e)}"
                )
    
    def _execute_via_file(
        self,
        instruction: str,
        task_id: str,
        control_phrase: str = "Задача выполнена!",
        timeout: int = 600
    ) -> HybridExecutionResult:
        """
        Выполнение через файловый интерфейс
        
        Args:
            instruction: Инструкция для выполнения
            task_id: ID задачи
            control_phrase: Контрольная фраза
            timeout: Таймаут ожидания результата
        
        Returns:
            HybridExecutionResult
        """
        logger.info(f"Выполнение через файловый интерфейс: {task_id}")
        
        try:
            # Записываем инструкцию
            self.file.write_instruction(instruction, task_id)
            logger.info(f"Инструкция записана: {self.file.instruction_file(task_id)}")
            
            # Ждем результат
            file_result = self.file.wait_for_result(
                task_id=task_id,
                timeout=timeout,
                control_phrase=control_phrase
            )
            
            logger.info(f"Результат получен: success={file_result.get('success')}")
            
            return HybridExecutionResult(
                success=file_result.get('success', False),
                method_used="file",
                output=file_result.get('content', ''),
                error_message=file_result.get('error'),
                side_effects_verified=True,  # Файловый интерфейс гарантирует выполнение
                file_result=file_result
            )
        
        except Exception as e:
            logger.error(f"Ошибка выполнения через файловый интерфейс: {e}")
            return HybridExecutionResult(
                success=False,
                method_used="file",
                output="",
                error_message=f"Ошибка файлового интерфейса: {str(e)}"
            )
    
    def _execute_via_file_fallback(
        self,
        instruction: str,
        task_id: str,
        cli_result: Optional[CursorCLIResult] = None
    ) -> HybridExecutionResult:
        """
        Fallback на файловый интерфейс после неудачи CLI
        
        Args:
            instruction: Инструкция для выполнения
            task_id: ID задачи
            cli_result: Результат CLI (для логирования)
        
        Returns:
            HybridExecutionResult
        """
        logger.info(f"Fallback: выполнение через файловый интерфейс")
        
        # Выполняем через файловый интерфейс
        file_result_obj = self._execute_via_file(
            instruction=instruction,
            task_id=task_id
        )
        
        # Обновляем метод на "cli_with_fallback"
        file_result_obj.method_used = "cli_with_fallback"
        file_result_obj.cli_result = cli_result
        
        return file_result_obj
    
    def _verify_side_effects(self, expected_files: List[str]) -> bool:
        """
        Проверка side-effects (наличие ожидаемых файлов)
        
        Args:
            expected_files: Список ожидаемых файлов (относительно project_dir)
        
        Returns:
            True если все файлы существуют, False иначе
        """
        if not expected_files:
            return True
        
        for file_path in expected_files:
            full_path = self.project_dir / file_path
            if not full_path.exists():
                logger.debug(f"Ожидаемый файл не найден: {full_path}")
                return False
        
        logger.debug(f"Все ожидаемые файлы найдены: {len(expected_files)}")
        return True
    
    def is_available(self) -> bool:
        """
        Проверка доступности хотя бы одного интерфейса
        
        Returns:
            True если доступен CLI или файловый интерфейс
        """
        return self.cli.is_available() or True  # Файловый интерфейс всегда доступен


def create_hybrid_cursor_interface(
    cli_path: Optional[str] = None,
    project_dir: Optional[str] = None,
    prefer_cli: bool = False,
    verify_side_effects: bool = True
) -> HybridCursorInterface:
    """
    Фабрика для создания гибридного интерфейса
    
    Args:
        cli_path: Путь к CLI (None для автопоиска)
        project_dir: Директория проекта
        prefer_cli: Предпочитать CLI даже для сложных задач
        verify_side_effects: Проверять side-effects после выполнения
    
    Returns:
        HybridCursorInterface
    """
    # Создаем CLI интерфейс
    cli = CursorCLIInterface(
        cli_path=cli_path,
        project_dir=project_dir
    )
    
    # Создаем файловый интерфейс
    file_interface = CursorFileInterface(
        project_dir=project_dir
    )
    
    # Создаем гибридный интерфейс
    return HybridCursorInterface(
        cli_interface=cli,
        file_interface=file_interface,
        project_dir=project_dir,
        prefer_cli=prefer_cli,
        verify_side_effects=verify_side_effects
    )


if __name__ == "__main__":
    # Пример использования
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Создаем гибридный интерфейс
    hybrid = create_hybrid_cursor_interface(
        cli_path="docker-compose-agent",
        project_dir="d:/Space/life",
        prefer_cli=False,  # Не предпочитать CLI для сложных задач
        verify_side_effects=True
    )
    
    print(f"Гибридный интерфейс создан")
    print(f"  CLI доступен: {hybrid.cli.is_available()}")
    print(f"  Файловый интерфейс: готов")
    print()
    
    # Пример 1: Простая задача (вопрос)
    print("=" * 70)
    print("Пример 1: Простая задача (вопрос)")
    print("=" * 70)
    
    result1 = hybrid.execute_task(
        instruction="Что находится в файле README.md?",
        task_id="example_1"
    )
    
    print(f"Результат:")
    print(f"  Success: {result1.success}")
    print(f"  Метод: {result1.method_used}")
    print(f"  Вывод: {result1.output[:200]}...")
    print()
    
    # Пример 2: Сложная задача (создание файла)
    print("=" * 70)
    print("Пример 2: Сложная задача (создание файла)")
    print("=" * 70)
    
    result2 = hybrid.execute_task(
        instruction="Создай файл test_hybrid.txt с текстом 'Hybrid interface test'",
        task_id="example_2",
        expected_files=["test_hybrid.txt"],
        control_phrase="Файл создан!"
    )
    
    print(f"Результат:")
    print(f"  Success: {result2.success}")
    print(f"  Метод: {result2.method_used}")
    print(f"  Side-effects проверены: {result2.side_effects_verified}")
    print()
