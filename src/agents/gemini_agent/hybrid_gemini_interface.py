"""
Гибридный интерфейс для работы с Gemini
Комбинирует CLI и файловый интерфейс для максимальной надежности.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    from .gemini_cli_interface import GeminiCLIInterface, GeminiCLIResult
    from ...cursor_file_interface import CursorFileInterface
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from gemini_cli_interface import GeminiCLIInterface, GeminiCLIResult
    from cursor_file_interface import CursorFileInterface

logger = logging.getLogger(__name__)

@dataclass
class HybridGeminiResult:
    """Результат выполнения через гибридный интерфейс"""
    success: bool
    method_used: str  # "cli", "file", "cli_with_fallback"
    output: str
    error_message: Optional[str] = None
    side_effects_verified: bool = False
    cli_result: Optional[GeminiCLIResult] = None
    file_result: Optional[Dict[str, Any]] = None

class HybridGeminiInterface:
    """
    Гибридный интерфейс для работы с Gemini
    Автоматически переключается на файловый интерфейс при неудаче API.
    """
    def __init__(
        self,
        cli_interface: Optional[GeminiCLIInterface] = None,
        file_interface: Optional[CursorFileInterface] = None,
        project_dir: Optional[str] = None,
        verify_side_effects: bool = True
    ):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.verify_side_effects = verify_side_effects
        
        # Инициализация интерфейсов
        self.cli = cli_interface or GeminiCLIInterface(project_dir=str(self.project_dir))
        self.file = file_interface or CursorFileInterface(project_dir=self.project_dir)
        
        logger.info("Гибридный интерфейс Gemini инициализирован")

    def execute_task(
        self,
        instruction: str,
        task_id: Optional[str] = None,
        expected_files: Optional[List[str]] = None,
        control_phrase: str = "Задача выполнена успешно!",
        timeout: int = 600,
        session_id: Optional[str] = None
    ) -> HybridGeminiResult:
        """
        Выполнение задачи с автоматическим fallback
        """
        if not task_id:
            import time
            task_id = f"gemini_task_{int(time.time())}"
            
        logger.info(f"Выполнение задачи Gemini {task_id}")
        
        # 1. Пробуем через CLI
        if self.cli.is_available():
            try:
                cli_res_dict = self.cli.execute_instruction(
                    instruction=instruction,
                    task_id=task_id,
                    timeout=timeout,
                    control_phrase=control_phrase,
                    session_id=session_id,
                    expected_files=expected_files
                )
                
                success = cli_res_dict.get("success", False)
                cli_result = GeminiCLIResult(
                    success=success,
                    stdout=cli_res_dict.get("stdout", ""),
                    stderr=cli_res_dict.get("stderr", ""),
                    return_code=cli_res_dict.get("return_code", -1),
                    cli_available=True,
                    error_message=cli_res_dict.get("error_message")
                )
                
                if success:
                    return HybridGeminiResult(
                        success=True,
                        method_used="cli",
                        output=cli_result.stdout,
                        side_effects_verified=cli_res_dict.get("side_effects_verified", False),
                        cli_result=cli_result
                    )
                else:
                    logger.warning(f"CLI Gemini не справился: {cli_result.error_message}. Пробуем fallback...")
            except Exception as e:
                logger.error(f"Ошибка при вызове CLI Gemini: {e}")
                cli_result = None

            # 2. Fallback на файловый интерфейс
            logger.info("Использование файлового интерфейса (fallback)")
            try:
                self.file.write_instruction(instruction, task_id)
                file_res = self.file.wait_for_result(
                    task_id=task_id,
                    timeout=timeout,
                    control_phrase=control_phrase
                )
                
                return HybridGeminiResult(
                    success=file_res.get("success", False),
                    method_used="cli_with_fallback",
                    output=file_res.get("content", ""),
                    error_message=file_res.get("error"),
                    side_effects_verified=True,
                    file_result=file_res,
                    cli_result=cli_result
                )
            except Exception as e:
                logger.error(f"Ошибка файлового интерфейса Gemini: {e}")
                return HybridGeminiResult(
                    success=False,
                    method_used="cli_with_fallback",
                    output="",
                    error_message=f"Ошибка файлового интерфейса: {e}",
                    cli_result=cli_result
                )
        else:
            # CLI недоступен, сразу файловый интерфейс
            logger.info("CLI Gemini недоступен, используем файловый интерфейс")
            self.file.write_instruction(instruction, task_id)
            file_res = self.file.wait_for_result(
                task_id=task_id,
                timeout=timeout,
                control_phrase=control_phrase
            )
            
            return HybridGeminiResult(
                success=file_res.get("success", False),
                method_used="file",
                output=file_res.get("content", ""),
                error_message=file_res.get("error"),
                side_effects_verified=True,
                file_result=file_res
            )

def create_hybrid_gemini_interface(
    project_dir: Optional[str] = None,
    container_name: Optional[str] = None,
    verify_side_effects: bool = True
) -> HybridGeminiInterface:
    cli = GeminiCLIInterface(project_dir=project_dir, container_name=container_name)
    return HybridGeminiInterface(cli_interface=cli, project_dir=project_dir, verify_side_effects=verify_side_effects)
