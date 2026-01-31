# src/agents/gemini_agent/gemini_agent_cli.py

import argparse
import sys
import os
import json
import subprocess
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
from google import genai
from google.genai import types
from collections.abc import Iterable

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    else:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class GeminiDeveloperAgent:
    def __init__(self, api_key: str, project_path: Path, model_name: str = "gemini-2.5-flash"):
        self.project_path = project_path.resolve()
        self.api_key = api_key
        self.model_name = os.getenv("GEMINI_MODEL_NAME", model_name)
        
        self.client = genai.Client(api_key=self.api_key, vertexai=False, http_options=types.HttpOptions(api_version='v1beta'))
        
        # Определение инструментов как Function Declarations для Gemini API
        self.tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="read_file",
                        description="Reads the content of a file.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file relative to project root"
                                )
                            },
                            required=["path"]
                        )
                    ),
                    types.FunctionDeclaration(
                        name="write_file",
                        description="Writes content to a file. Creates directories if needed.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file relative to project root"
                                ),
                                "content": types.Schema(
                                    type=types.Type.STRING,
                                    description="Content to write"
                                )
                            },
                            required=["path", "content"]
                        )
                    ),
                    types.FunctionDeclaration(
                        name="list_dir",
                        description="Lists files and directories in a given path.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to directory (default: current directory)"
                                )
                            },
                            required=[]
                        )
                    ),
                    types.FunctionDeclaration(
                        name="run_shell_command",
                        description="Executes a shell command in the project root.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "command": types.Schema(
                                    type=types.Type.STRING,
                                    description="Shell command to execute"
                                )
                            },
                            required=["command"]
                        )
                    ),
                    types.FunctionDeclaration(
                        name="get_file_info",
                        description="Get metadata about a file or directory.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file or directory"
                                )
                            },
                            required=["path"]
                        )
                    )
                ]
            )
        ]
        
        # Системный промпт
        self.system_instruction = f"""
You are an expert AI software engineer and architect working on a project.
Your goal is to complete the assigned task by modifying the codebase, running commands, and verifying your work.

PROJECT ROOT: {self.project_path}

CAPABILITIES:
1. You can READ files to understand the code.
2. You can WRITE files to create or modify code.
3. You can LIST directories to explore the structure.
4. You can RUN shell commands (git, pytest, python, pip, etc.).

RULES:
1. **ACT, DON'T JUST PLAN:** If you need to refactor, create a file, or fix a bug, USE THE TOOLS to actually do it. Do not just describe what you would do.
2. **VERIFY:** After making changes, try to verify them (e.g., run a script or check the file content).
3. **CONTEXT:** You are working inside the project directory. All paths should be relative to the project root or absolute paths within the project.
4. **SAFETY:** Do not delete critical system files.
5. **FINAL REPORT:** When the task is done, generate a detailed markdown report summarizing what you did.

You must operate in a loop: THOUGHT -> ACTION (Tool Call) -> OBSERVATION (Tool Result) -> THOUGHT ...
"""
        


    def _validate_path(self, path: Union[str, Path]) -> Path:
        """Ensures the path is within the project directory."""
        try:
            full_path = (self.project_path / path).resolve()
            # Простая проверка, что путь начинается с папки проекта
            # (Можно ослабить для доступа к временным файлам, если нужно)
            if not str(full_path).startswith(str(self.project_path)):
                # Разрешаем доступ, если это явно запрошено, но логируем предупреждение
                # В Docker контейнере пути могут быть специфичными
                logger.warning(f"Accessing path outside project root: {full_path}")
            return full_path
        except Exception as e:
            raise ValueError(f"Invalid path: {path}. Error: {e}")

    # --- TOOLS ---

    def read_file(self, path: str) -> str:
        """Reads the content of a file."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: File not found at {target_path}"
            if not target_path.is_file():
                return f"Error: {target_path} is not a file"
            
            content = target_path.read_text(encoding='utf-8', errors='replace')
            logger.info(f"📖 Read file: {path} ({len(content)} chars)")
            return content
        except Exception as e:
            return f"Error reading file {path}: {str(e)}"

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a file. Creates directories if needed."""
        try:
            target_path = self._validate_path(path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding='utf-8')
            logger.info(f"💾 Wrote file: {path}")
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file {path}: {str(e)}"

    def list_dir(self, path: str = ".") -> str:
        """Lists files and directories in a given path."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: Directory not found at {target_path}"
            
            items = []
            for item in target_path.iterdir():
                type_str = "DIR" if item.is_dir() else "FILE"
                items.append(f"{type_str}: {item.name}")
            
            result = "\n".join(items)
            logger.info(f"📂 Listed dir: {path}")
            return result if result else "(Empty directory)"
        except Exception as e:
            return f"Error listing directory {path}: {str(e)}"

    def run_shell_command(self, command: str) -> str:
        """Executes a shell command in the project root."""
        try:
            # Security check: prevent dangerous commands
            forbidden = ["rm -rf /", ":(){ :|:& };:"] # Fork bomb
            if any(cmd in command for cmd in forbidden):
                return "Error: Command denied for security reasons."

            logger.info(f"🚀 Executing shell: {command}")
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout
            )
            
            output = f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            output += f"Return Code: {result.returncode}"
            
            return output
        except subprocess.TimeoutExpired:
            return "Error: Command timed out."
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def get_file_info(self, path: str) -> str:
        """Get metadata about a file or directory."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return "Path does not exist"
            
            stat = target_path.stat()
            return f"Type: {'Directory' if target_path.is_dir() else 'File'}\nSize: {stat.st_size} bytes\nModified: {stat.st_mtime}"
        except Exception as e:
            return f"Error getting info: {e}"

    def _execute_function_call(self, func_name: str, args: dict) -> dict:
        """Выполняет вызов функции по имени с переданными аргументами."""
        try:
            if func_name == "read_file":
                result = self.read_file(**args)
            elif func_name == "write_file":
                result = self.write_file(**args)
            elif func_name == "list_dir":
                result = self.list_dir(**args)
            elif func_name == "run_shell_command":
                result = self.run_shell_command(**args)
            elif func_name == "get_file_info":
                result = self.get_file_info(**args)
            else:
                result = f"Unknown function {func_name}"
            # Возвращаем результат как словарь, ожидаемый FunctionResponse
            return {"result": result}
        except Exception as e:
            logger.error(f"Error executing function {func_name}: {e}")
            return {"error": str(e)}

    def execute(self, instruction: str, output_file_path: Path, control_phrase: str):
        """
        Executes the instruction using the chat loop and tools.
        """
        print(f"🤖 Gemini Agent started.")
        print(f"📍 Project Path: {self.project_path}")
        print(f"📝 Instruction: {instruction}")

        try:
            # Формируем сообщение для модели
            full_prompt = (
                f"TASK: {instruction}\n\n"
                f"Execute this task by using the available tools. "
                f"Make real changes to the codebase if required. "
                f"When you have completed the task, generate a final report."
            )

            # Конфигурация с инструментами и системной инструкцией
            config = types.GenerateContentConfig(
                tools=self.tools,
                system_instruction=self.system_instruction,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)  # Ручная обработка
            )
            
            # Создаем историю диалога
            history = [types.Content(parts=[types.Part.from_text(text=full_prompt)], role="user")]
            
            max_steps = 10
            final_text = None
            
            for step in range(max_steps):
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=history,
                    config=config
                )
                
                # Проверяем наличие вызовов функций
                function_calls = []
                text_parts = []
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.text:
                                text_parts.append(part.text)
                            if part.function_call:
                                function_calls.append(part.function_call)
                
                # Если есть текстовые части, собираем их
                if text_parts:
                    final_text = "\n".join(text_parts)
                
                # Если есть вызовы функций, выполняем их
                if function_calls:
                    for fc in function_calls:
                        func_name = fc.name
                        args = fc.args
                        logger.info(f"Вызов функции {func_name} с аргументами {args}")
                        # Выполняем соответствующую функцию
                        result = self._execute_function_call(func_name, args)
                        # Добавляем ответ функции в историю
                        history.append(types.Content(
                            parts=[types.Part.from_function_response(
                                name=func_name,
                                response=result
                            )],
                            role="function"
                        ))
                    # Продолжаем цикл для следующего ответа модели
                    continue
                else:
                    # Нет вызовов функций - значит, финальный ответ
                    break
            
            if final_text is None:
                final_text = "Задача выполнена, но финальный отчет не сгенерирован."
            
            # Нормализация: убираем двойные восклицательные знаки в контрольной фразе, если модель их сгенерировала
            if control_phrase.endswith("!"):
                double_bang_phrase = control_phrase + "!"
                if double_bang_phrase in final_text:
                    logger.info(f"Fixed double exclamation mark in control phrase: {double_bang_phrase} -> {control_phrase}")
                    final_text = final_text.replace(double_bang_phrase, control_phrase)

            # Добавляем контрольную фразу, если её нет
            if control_phrase not in final_text:
                final_text += f"\n\n{control_phrase}"
            
            # Сохраняем отчет
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path.write_text(final_text, encoding='utf-8')
            
            print(f"✅ Execution completed.")
            print(f"📄 Report saved to: {output_file_path}")
            
        except Exception as e:
            logger.error(f"Critical error during execution: {e}", exc_info=True)
            # В случае ошибки создаем файл с ошибкой, чтобы сервер не висел вечно
            error_msg = f"# Error Report\n\nTask failed with exception:\n```\n{str(e)}\n```\n\n{control_phrase}"
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path.write_text(error_msg, encoding='utf-8')
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Gemini CLI Agent with Real Capabilities")
    parser.add_argument("instruction", type=str, help="The instruction to execute.")
    parser.add_argument("output_file_path", type=str, help="Path to save the final report.")
    parser.add_argument("control_phrase", type=str, help="Phrase to append to the report.")
    parser.add_argument("--project_path", type=str, default=".", help="Project root directory.")
    
    args = parser.parse_args()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY is not set in environment.", file=sys.stderr)
        sys.exit(1)

    agent = GeminiDeveloperAgent(
        api_key=api_key,
        project_path=Path(args.project_path)
    )
    
    agent.execute(
        instruction=args.instruction,
        output_file_path=Path(args.output_file_path),
        control_phrase=args.control_phrase
    )

if __name__ == "__main__":
    main()
