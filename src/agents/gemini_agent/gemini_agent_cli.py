# src/agents/gemini_agent/gemini_agent_cli.py

import argparse
import concurrent.futures
import datetime
import logging
import os
import pickle
import subprocess
import sys
from pathlib import Path
from typing import Union

from dotenv import load_dotenv
from google import genai
from google.genai import types

__version__ = "1.1.0"

# Настройка кодировки для Windows
if sys.platform == "win32":
    import codecs

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()


class GeminiDeveloperAgent:
    def __init__(self, api_key: str, project_path: Path, model_name: str = "gemini-2.5-flash"):
        self.project_path = project_path.resolve()
        self.api_key = api_key
        self.model_name = os.getenv("GEMINI_MODEL_NAME", model_name)

        self.client = genai.Client(
            api_key=self.api_key,
            vertexai=False,
            http_options=types.HttpOptions(api_version="v1beta"),
        )
        self.memory_file = self.project_path / ".gemini_memory.md"
        self.sessions_dir = self.project_path / ".gemini_sessions"
        self.sessions_dir.mkdir(exist_ok=True)

        # Token and rate limit management
        self.token_history = []  # List of (timestamp, token_count)
        self.max_tokens_per_minute = 800000  # Safety limit (80% of 1M) for token budget per minute
        self.max_history_tokens = 600000  # Max history size before trimming to stay within budget
        self.chars_per_token = (
            2.0  # Heuristic for token estimation (chars -> tokens) - lowered for Russian support
        )

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
                                    description="Path to file relative to project root",
                                )
                            },
                            required=["path"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="read_file_lines",
                        description="Reads a specific range of lines from a file.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file relative to project root",
                                ),
                                "start_line": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="Start line number (1-based index)",
                                ),
                                "end_line": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="End line number (1-based index)",
                                ),
                            },
                            required=["path", "start_line", "end_line"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="write_file",
                        description="Writes content to a file. Creates directories if needed.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file relative to project root",
                                ),
                                "content": types.Schema(
                                    type=types.Type.STRING, description="Content to write"
                                ),
                            },
                            required=["path", "content"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="replace_in_file",
                        description="Replaces a specific string in a file with a new string.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file relative to project root",
                                ),
                                "old_string": types.Schema(
                                    type=types.Type.STRING, description="Exact string to replace"
                                ),
                                "new_string": types.Schema(
                                    type=types.Type.STRING, description="New string to replace with"
                                ),
                            },
                            required=["path", "old_string", "new_string"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="insert_at_line",
                        description="Inserts content at a specific line number in a file.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file relative to project root",
                                ),
                                "line_number": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="Line number to insert at (1-based index)",
                                ),
                                "content": types.Schema(
                                    type=types.Type.STRING, description="Content to insert"
                                ),
                            },
                            required=["path", "line_number", "content"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="get_code_skeleton",
                        description="Returns the skeleton of the code (classes, methods, functions) without implementation. Can include imports, global variables, class attributes, and docstrings.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file relative to project root",
                                ),
                                "include_imports": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description="Include import statements (default: false)",
                                ),
                                "include_global_variables": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description="Include global variable assignments (default: false)",
                                ),
                                "include_class_attributes": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description="Include class attribute assignments (default: false)",
                                ),
                                "include_docstrings": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description="Include docstrings for classes and functions (default: false)",
                                ),
                                "include_classes": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description="Include class definitions (default: true)",
                                ),
                                "include_functions": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description="Include top-level function definitions (default: true)",
                                ),
                            },
                            required=["path"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="check_syntax",
                        description="Checks syntax of a file (supports Python, JSON, YAML).",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file relative to project root",
                                )
                            },
                            required=["path"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="read_symbol",
                        description="Reads the source code of a specific symbol (class or function) from a file.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file relative to project root",
                                ),
                                "symbol_name": types.Schema(
                                    type=types.Type.STRING,
                                    description="Name of the class or function to read",
                                ),
                            },
                            required=["path", "symbol_name"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="read_memory",
                        description="Reads the agent's long-term memory file.",
                        parameters=types.Schema(type=types.Type.OBJECT, properties={}, required=[]),
                    ),
                    types.FunctionDeclaration(
                        name="add_to_memory",
                        description="Appends a note to the agent's long-term memory.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "text": types.Schema(
                                    type=types.Type.STRING, description="Text to add to memory"
                                )
                            },
                            required=["text"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="git_status",
                        description="Returns the current git status (branch, changed files, untracked files).",
                        parameters=types.Schema(type=types.Type.OBJECT, properties={}, required=[]),
                    ),
                    types.FunctionDeclaration(
                        name="git_diff_check",
                        description="Checks git diff to see changes made to the codebase.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Optional path to specific file or directory",
                                ),
                                "staged": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description="Whether to show staged changes (default: false)",
                                ),
                            },
                            required=[],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="list_dir",
                        description="Lists files and directories in a given path.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to directory (default: current directory)",
                                )
                            },
                            required=[],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="list_dir_recursive",
                        description="Lists files and directories recursively up to a specified depth.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to directory (default: current directory)",
                                ),
                                "depth": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="Maximum depth of recursion (default: 2)",
                                ),
                            },
                            required=[],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="run_shell_command",
                        description="Executes a shell command in the project root.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "command": types.Schema(
                                    type=types.Type.STRING, description="Shell command to execute"
                                )
                            },
                            required=["command"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="get_file_info",
                        description="Get metadata about a file or directory.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING, description="Path to file or directory"
                                )
                            },
                            required=["path"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="find_files",
                        description="Find files matching a glob pattern.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "pattern": types.Schema(
                                    type=types.Type.STRING,
                                    description="Glob pattern (e.g., '**/*.py', 'src/test_*.ts')",
                                ),
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Directory to search in (default: project root)",
                                ),
                            },
                            required=["pattern"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="search_files",
                        description="Search for a text pattern in files (grep-like).",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "pattern": types.Schema(
                                    type=types.Type.STRING,
                                    description="Regex or text pattern to search for",
                                ),
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Directory or file to search in (default: project root)",
                                ),
                                "case_sensitive": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description="Whether the search is case sensitive (default: true)",
                                ),
                            },
                            required=["pattern"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="run_tests",
                        description="Runs project tests using pytest. Can optionally return only failed tests.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Optional path to specific test file or directory",
                                ),
                                "only_failures": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description="If true, only runs and reports tests that failed in the last run.",
                                ),
                            },
                            required=[],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="search_symbols",
                        description="Searches for class and function definitions matching a pattern across the project.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "pattern": types.Schema(
                                    type=types.Type.STRING,
                                    description="Pattern to search for in symbol names (classes, functions)",
                                )
                            },
                            required=["pattern"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="apply_diff",
                        description="Applies a unified diff to a file.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Path to file relative to project root",
                                ),
                                "diff_content": types.Schema(
                                    type=types.Type.STRING,
                                    description="Content of the unified diff",
                                ),
                            },
                            required=["path", "diff_content"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="semantic_search",
                        description="Searches for code by meaning (looking for keywords in filenames, definitions, and comments).",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "query": types.Schema(
                                    type=types.Type.STRING,
                                    description="Query or keywords to search for",
                                )
                            },
                            required=["query"],
                        ),
                    ),
                ]
            )
        ]

        # Системный промпт
        base_system_instruction = f"""
You are an expert AI software engineer and architect working on a project.
Your goal is to complete the assigned task by modifying the codebase, running commands, and verifying your work.

PROJECT ROOT: {self.project_path}

CAPABILITIES:
1. You can READ files to understand the code.
2. You can WRITE files to create or modify code.
3. You can EDIT files precisely using replace_in_file (preferred over write_file for small changes) or insert_at_line.
4. You can LIST directories (simple and recursive) to explore the structure.
5. You can SEARCH for files by name (find_files), content (search_files), or symbol definitions (search_symbols).
6. You can GET CODE SKELETON (get_code_skeleton) to understand file structure. Use 'include_classes' or 'include_functions' to filter output.
7. You can READ SYMBOL (read_symbol) to get source code of a specific class or function.
8. You can CHECK SYNTAX (check_syntax) to verify your changes (supports Python, JSON, YAML).
9. You can USE MEMORY (read_memory, add_to_memory) to store and retrieve important information across steps.
10. You can CHECK DIFFS (git_diff_check) to see what you have changed.
11. You can RUN shell commands (git, pytest, python, pip, etc.).

RULES:
1. **ACT, DON'T JUST PLAN:** If you need to refactor, create a file, or fix a bug, USE THE TOOLS to actually do it. Do not just describe what you would do.
2. **VERIFY:** After making changes, try to verify them (e.g., run a script or check the file content).
3. **CONTEXT:** You are working inside the project directory. All paths should be relative to the project root or absolute paths within the project.
4. **SAFETY:** Do not delete critical system files.
5. **FINAL REPORT:** When the task is done, generate a detailed markdown report summarizing what you did.

You must operate in a loop: THOUGHT -> ACTION (Tool Call) -> OBSERVATION (Tool Result) -> THOUGHT ...
"""
        # Load project specific rules
        self.system_instruction = base_system_instruction + self._load_project_rules()

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

    def _load_project_rules(self) -> str:
        """Loads project-specific rules from .cursor/rules or AGENTS.md."""
        rules = ""

        # Check AGENTS.md
        agents_md = self.project_path / "AGENTS.md"
        if agents_md.exists() and agents_md.is_file():
            try:
                content = agents_md.read_text(encoding="utf-8", errors="replace")
                rules += f"\n\n## Project Context (from AGENTS.md):\n{content}\n"
                logger.info("Loaded AGENTS.md")
            except Exception as e:
                logger.warning(f"Failed to read AGENTS.md: {e}")

        # Check .cursor/rules
        cursor_rules = self.project_path / ".cursor/rules"
        if cursor_rules.exists():
            try:
                if cursor_rules.is_file():
                    content = cursor_rules.read_text(encoding="utf-8", errors="replace")
                    rules += f"\n\n## Cursor Rules:\n{content}\n"
                    logger.info("Loaded .cursor/rules file")
                elif cursor_rules.is_dir():
                    rules += "\n\n## Cursor Rules:\n"
                    count = 0
                    for rule_file in cursor_rules.glob("*.md"):  # Assuming markdown files
                        content = rule_file.read_text(encoding="utf-8", errors="replace")
                        rules += f"### {rule_file.name}:\n{content}\n\n"
                        count += 1
                    logger.info(f"Loaded {count} files from .cursor/rules/")
            except Exception as e:
                logger.warning(f"Failed to read .cursor/rules: {e}")

        return rules

    def _estimate_tokens(self, content_list: list) -> int:
        """Estimates token count for a list of Content objects."""
        total_chars = 0
        for content in content_list:
            if hasattr(content, "parts"):
                for part in content.parts:
                    if hasattr(part, "text") and part.text:
                        total_chars += len(part.text)
                    elif hasattr(part, "function_call") and part.function_call:
                        total_chars += len(str(part.function_call))
                    elif hasattr(part, "function_response") and part.function_response:
                        total_chars += len(str(part.function_response))
        return int(total_chars / self.chars_per_token)

    def _wait_for_rate_limit(self, current_request_tokens: int):
        """Waits if the token budget per minute is close to being exceeded."""
        now = datetime.datetime.now()
        one_minute_ago = now - datetime.timedelta(seconds=60)

        # Cleanup old history
        self.token_history = [item for item in self.token_history if item[0] > one_minute_ago]

        current_minute_tokens = sum(item[1] for item in self.token_history)

        if current_minute_tokens + current_request_tokens > self.max_tokens_per_minute:
            # We need to wait. Calculate how long.
            # Simple approach: wait until the oldest request in the window falls out
            if self.token_history:
                wait_time = (
                    self.token_history[0][0] + datetime.timedelta(seconds=61) - now
                ).total_seconds()
                wait_time = max(1, min(wait_time, 60))  # Clamp between 1 and 60s
                logger.info(
                    f"Rate limit management: budget ({current_minute_tokens} tokens) close to limit. Waiting {wait_time:.1f}s..."
                )
                import time

                time.sleep(wait_time)
                # Re-check recursively
                self._wait_for_rate_limit(current_request_tokens)

        # Record this request
        self.token_history.append((datetime.datetime.now(), current_request_tokens))

    def _trim_history(self, history: list) -> list:
        """Ensures history doesn't exceed context window while keeping important parts."""
        estimated_tokens = self._estimate_tokens(history)

        if estimated_tokens <= self.max_history_tokens:
            return history

        logger.info(
            f"History too large ({estimated_tokens} tokens). Trimming to stay within budget..."
        )

        # Strategy:
        # 1. Keep the first message (Original TASK) - it's history[0]
        # 2. Keep the last 10 messages (latest turns)
        # 3. Discard everything in between

        if len(history) <= 12:  # Initial task + 10 turns + buffer
            return history

        trimmed = [history[0]]  # Keep TASK
        trimmed.extend(history[-10:])  # Keep last 10 turns

        new_estimate = self._estimate_tokens(trimmed)
        logger.info(
            f"Trimmed history: {estimated_tokens} -> {new_estimate} tokens. Removed {len(history) - len(trimmed)} messages."
        )

        return trimmed

    # --- TOOLS ---

    def read_file(self, path: str) -> str:
        """Reads the content of a file."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: File not found at {target_path}"
            if not target_path.is_file():
                return f"Error: {target_path} is not a file"

            content = target_path.read_text(encoding="utf-8", errors="replace")
            logger.info(f"📖 Read file: {path} ({len(content)} chars)")

            # Truncate content if it's too large to avoid hitting token limits
            max_chars = 20000
            if len(content) > max_chars:
                content = (
                    content[:max_chars]
                    + f"\n... [Content truncated. Original size: {len(content)} chars]"
                )

            return content
        except Exception as e:
            return f"Error reading file {path}: {str(e)}"

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a file. Creates directories if needed."""
        try:
            target_path = self._validate_path(path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            logger.info(f"💾 Wrote file: {path}")

            msg = f"Successfully wrote to {path}"
            if path.endswith(".py"):
                syntax_check = self.check_syntax(path)
                msg += f"\nSyntax check: {syntax_check}"
            return msg
        except Exception as e:
            return f"Error writing file {path}: {str(e)}"

    def replace_in_file(self, path: str, old_string: str, new_string: str) -> str:
        """Replaces a specific string in a file with a new string."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: File not found at {target_path}"

            content = target_path.read_text(encoding="utf-8", errors="replace")

            if old_string not in content:
                return f"Error: The string to replace was not found in {path}. Please check formatting and whitespace."

            if content.count(old_string) > 1:
                return f"Error: The string to replace occurs multiple times ({content.count(old_string)}) in {path}. Please provide more context to make it unique."

            new_content = content.replace(old_string, new_string)
            target_path.write_text(new_content, encoding="utf-8")

            logger.info(f"✏️ Replaced string in file: {path}")

            msg = f"Successfully replaced string in {path}"
            if path.endswith(".py"):
                syntax_check = self.check_syntax(path)
                msg += f"\nSyntax check: {syntax_check}"
            return msg
        except Exception as e:
            return f"Error replacing in file {path}: {str(e)}"

    def insert_at_line(self, path: str, line_number: int, content: str) -> str:
        """Inserts content at a specific line number in a file."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: File not found at {target_path}"

            file_content = target_path.read_text(encoding="utf-8", errors="replace")
            lines = file_content.splitlines(keepends=True)

            if line_number < 1 or line_number > len(lines) + 1:
                return f"Error: Line number {line_number} is out of range (1-{len(lines) + 1})"

            idx = line_number - 1

            # Если вставляем не в начало, проверяем, что предыдущая строка заканчивается переводом строки
            if idx > 0 and idx <= len(lines):
                prev_line_idx = idx - 1
                if not lines[prev_line_idx].endswith("\n"):
                    lines[prev_line_idx] += "\n"

            # Ensure content ends with newline
            if not content.endswith("\n"):
                content += "\n"

            lines.insert(idx, content)
            new_content = "".join(lines)

            target_path.write_text(new_content, encoding="utf-8")
            logger.info(f"➕ Inserted at line {line_number} in file: {path}")

            msg = f"Successfully inserted content at line {line_number} in {path}"
            if path.endswith(".py"):
                syntax_check = self.check_syntax(path)
                msg += f"\nSyntax check: {syntax_check}"
            return msg
        except Exception as e:
            return f"Error inserting in file {path}: {str(e)}"

    def get_code_skeleton(
        self,
        path: str,
        include_imports: bool = False,
        include_global_variables: bool = False,
        include_class_attributes: bool = False,
        include_docstrings: bool = False,
        include_classes: bool = True,
        include_functions: bool = True,
    ) -> str:
        """Returns the skeleton of the code (classes, methods, functions) without implementation."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: File not found at {target_path}"

            if target_path.suffix == ".py":
                import ast

                def get_args_str(args):
                    arg_list = []
                    # Positional args
                    for i, arg in enumerate(args.args):
                        arg_str = arg.arg
                        if arg.annotation:
                            # Try to get annotation as string (simple cases)
                            try:
                                if isinstance(arg.annotation, ast.Name):
                                    arg_str += f": {arg.annotation.id}"
                                elif isinstance(arg.annotation, ast.Attribute):
                                    arg_str += f": {arg.annotation.attr}"
                                elif isinstance(arg.annotation, ast.Constant):
                                    arg_str += f": {arg.annotation.value}"
                                else:
                                    arg_str += ": ..."  # Complex annotation
                            except:
                                pass
                        arg_list.append(arg_str)

                    # Varargs
                    if args.vararg:
                        arg_list.append(f"*{args.vararg.arg}")

                    # Kwargs
                    if args.kwarg:
                        arg_list.append(f"**{args.kwarg.arg}")

                    return ", ".join(arg_list)

                try:
                    source = target_path.read_text(encoding="utf-8", errors="replace")
                    tree = ast.parse(source)
                    skeleton = []

                    for node in tree.body:
                        # Imports
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            if include_imports:
                                if isinstance(node, ast.Import):
                                    names = ", ".join([n.name for n in node.names])
                                    skeleton.append(f"import {names}")
                                elif isinstance(node, ast.ImportFrom):
                                    module = node.module or ""
                                    names = ", ".join([n.name for n in node.names])
                                    skeleton.append(f"from {module} import {names}")

                        # Global Variables
                        elif isinstance(node, ast.Assign) and include_global_variables:
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    skeleton.append(f"{target.id} = ...")

                        # Functions
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not include_functions:
                                continue

                            decorators = [
                                f"@{d.id}" for d in node.decorator_list if isinstance(d, ast.Name)
                            ]
                            skeleton.extend(decorators)

                            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                            args_str = get_args_str(node.args)
                            ret_ann = ""
                            if node.returns:
                                try:
                                    if isinstance(node.returns, ast.Name):
                                        ret_ann = f" -> {node.returns.id}"
                                    elif isinstance(node.returns, ast.Constant):  # Python 3.8+
                                        ret_ann = f" -> {node.returns.value}"
                                    else:
                                        ret_ann = " -> ..."
                                except:
                                    pass

                            skeleton.append(f"{prefix}def {node.name}({args_str}){ret_ann}:")
                            if include_docstrings and ast.get_docstring(node):
                                doc = ast.get_docstring(node).replace("\n", "\n    ")
                                skeleton.append(f'    """{doc}"""')
                            skeleton.append("    ...")
                            skeleton.append("")  # Empty line after function

                        # Classes
                        elif isinstance(node, ast.ClassDef):
                            if not include_classes:
                                continue

                            decorators = [
                                f"@{d.id}" for d in node.decorator_list if isinstance(d, ast.Name)
                            ]
                            skeleton.extend(decorators)

                            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                            bases_str = f"({', '.join(bases)})" if bases else ""
                            skeleton.append(f"class {node.name}{bases_str}:")

                            if include_docstrings and ast.get_docstring(node):
                                doc = ast.get_docstring(node).replace("\n", "\n    ")
                                skeleton.append(f'    """{doc}"""')

                            has_content = False
                            for item in node.body:
                                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    prefix = (
                                        "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                                    )
                                    args_str = get_args_str(item.args)

                                    skeleton.append(f"    {prefix}def {item.name}({args_str}):")
                                    if include_docstrings and ast.get_docstring(item):
                                        doc = ast.get_docstring(item).replace("\n", "\n        ")
                                        skeleton.append(f'        """{doc}"""')
                                    skeleton.append("        ...")
                                    has_content = True
                                elif isinstance(item, ast.Assign) and include_class_attributes:
                                    for target in item.targets:
                                        if isinstance(target, ast.Name):
                                            skeleton.append(f"    {target.id} = ...")
                                            has_content = True

                            if not has_content:
                                skeleton.append("    ...")
                            skeleton.append("")  # Empty line after class

                    return "\n".join(skeleton).strip() if skeleton else "No definitions found."
                except Exception as e:
                    return f"Error parsing Python file: {e}"

            elif target_path.suffix in [".js", ".ts", ".jsx", ".tsx"]:
                # Basic regex-based skeleton for JS/TS
                import re

                try:
                    content = target_path.read_text(encoding="utf-8", errors="replace")
                    skeleton = []
                    lines = content.splitlines()

                    # Regex patterns
                    class_pattern = re.compile(r"^\s*(export\s+)?(default\s+)?class\s+(\w+)")
                    func_pattern = re.compile(
                        r"^\s*(export\s+)?(default\s+)?(async\s+)?function\s+(\w+)"
                    )
                    const_func_pattern = re.compile(
                        r"^\s*(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(async\s+)?(\([^)]*\)|[^=]+)\s*=>"
                    )
                    method_pattern = re.compile(r"^\s*(async\s+)?(\w+)\s*\([^)]*\)\s*{")

                    for line in lines:
                        if include_imports and (
                            line.strip().startswith("import ")
                            or line.strip().startswith("require(")
                        ):
                            skeleton.append(line.strip())
                            continue

                        # Check patterns
                        if class_pattern.search(line):
                            if include_classes:
                                skeleton.append(line.strip().rstrip("{").strip() + " { ... }")
                        elif func_pattern.search(line):
                            if include_functions:
                                skeleton.append(line.strip().rstrip("{").strip() + " { ... }")
                        elif const_func_pattern.search(line):
                            if include_functions:
                                # Clean up the arrow function definition for display
                                clean_line = line.strip().rstrip("{").strip()
                                if clean_line.endswith("=>"):
                                    clean_line = clean_line[:-2].strip()
                                skeleton.append(clean_line + " => { ... }")
                        # Simple heuristic for methods inside classes (indented)
                        elif line.startswith("  ") or line.startswith("\t"):
                            if (
                                method_pattern.search(line)
                                and not line.strip().startswith("if")
                                and not line.strip().startswith("for")
                                and not line.strip().startswith("while")
                            ):
                                # We don't have a separate include_methods, so we include them if we include classes or functions?
                                # Usually if you want a skeleton you want methods.
                                skeleton.append(line.strip().rstrip("{").strip() + " { ... }")

                    return (
                        "\n".join(skeleton).strip()
                        if skeleton
                        else "No definitions found (or regex failed)."
                    )
                except Exception as e:
                    return f"Error parsing JS/TS file: {e}"

            else:
                # Fallback for other files - basic regex or just first lines
                return "Error: Skeleton extraction currently only supported for .py, .js, .ts files. Use read_file instead."
        except Exception as e:
            return f"Error getting skeleton: {e}"

    def check_syntax(self, path: str) -> str:
        """Checks syntax of a file (supports Python, JSON, YAML)."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: File not found at {target_path}"

            content = target_path.read_text(encoding="utf-8", errors="replace")

            if target_path.suffix == ".py":
                # Try using ruff if available for better feedback
                try:
                    import subprocess

                    result = subprocess.run(
                        ["ruff", "check", str(target_path)],
                        capture_output=True,
                        text=True,
                        cwd=self.project_path,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        return "✅ Syntax and lint check passed (ruff)."
                    else:
                        return f"❌ Lint errors (ruff):\n{result.stdout}\n{result.stderr}"
                except (ImportError, FileNotFoundError, subprocess.SubprocessError):
                    # Fallback to basic ast check
                    import ast

                    try:
                        ast.parse(content)
                        return "✅ Syntax check passed (valid Python code)."
                    except SyntaxError as e:
                        return f"❌ SyntaxError: {e.msg} at line {e.lineno}, offset {e.offset}"
                    except Exception as e:
                        return f"Error checking syntax: {e}"
            elif target_path.suffix == ".json":
                import json

                try:
                    json.loads(content)
                    return "✅ Syntax check passed (valid JSON)."
                except json.JSONDecodeError as e:
                    return f"❌ JSONDecodeError: {e.msg} at line {e.lineno}, column {e.colno}"
            elif target_path.suffix in [".yaml", ".yml"]:
                try:
                    import yaml

                    yaml.safe_load(content)
                    return "✅ Syntax check passed (valid YAML)."
                except Exception as e:
                    return f"❌ YAMLError: {e}"
            else:
                return f"Syntax checking currently not supported for {target_path.suffix} files."
        except Exception as e:
            return f"Error checking syntax: {e}"

    def read_symbol(self, path: str, symbol_name: str) -> str:
        """Reads the source code of a specific symbol (class or function) from a file."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: File not found at {target_path}"

            if target_path.suffix != ".py":
                return "Error: Symbol reading is currently only supported for .py files."

            import ast

            content = target_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name == symbol_name:
                        # Extract source code using line numbers
                        lines = content.splitlines()
                        # ast node line numbers are 1-based
                        start_line = node.lineno - 1
                        # end_lineno is available in Python 3.8+
                        if hasattr(node, "end_lineno"):
                            end_line = node.end_lineno
                            return "\n".join(lines[start_line:end_line])
                        else:
                            # Fallback if end_lineno not available (should be on 3.10)
                            return f"Found {symbol_name}, but cannot extract full source (missing end_lineno)."

            return f"Error: Symbol '{symbol_name}' not found in {path}."
        except Exception as e:
            return f"Error reading symbol: {e}"

    def read_memory(self) -> str:
        """Reads the agent's long-term memory file."""
        try:
            if not self.memory_file.exists():
                return "Memory is empty."
            content = self.memory_file.read_text(encoding="utf-8", errors="replace")
            logger.info("🧠 Read memory")
            return content
        except Exception as e:
            return f"Error reading memory: {e}"

    def add_to_memory(self, text: str) -> str:
        """Appends a note to the agent's long-term memory."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"\n## [{timestamp}]\n{text}\n"

            with open(self.memory_file, "a", encoding="utf-8") as f:
                f.write(entry)

            logger.info("🧠 Added to memory")
            return "Successfully added note to memory."
        except Exception as e:
            return f"Error writing to memory: {e}"

    def git_diff_check(self, path: str = None, staged: bool = False) -> str:
        """Checks git diff to see changes made to the codebase."""
        try:
            command = ["git", "diff"]
            if staged:
                command.append("--cached")
            if path:
                command.append(path)

            result = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
                cwd=self.project_path,
                timeout=30,
            )

            if result.returncode != 0:
                return f"Error running git diff: {result.stderr}"

            return result.stdout if result.stdout else "No changes in git diff."
        except Exception as e:
            return f"Error checking diff: {e}"

    def run_tests(self, path: str = None, only_failures: bool = False) -> str:
        """Runs project tests using pytest."""
        try:
            command = ["pytest"]
            if only_failures:
                command.append("--lf")
                command.append("--tb=short")

            if path:
                target_path = self._validate_path(path)
                command.append(str(target_path))

            logger.info(f"🧪 Running tests: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
                cwd=self.project_path,
                timeout=120,
            )

            output = f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            output += f"Return Code: {result.returncode}"

            if only_failures and result.returncode == 0:
                if "no previously failed tests" in result.stdout:
                    return (
                        "No previously failed tests to run. All tests passed or no history found."
                    )

            return output
        except subprocess.TimeoutExpired:
            return "Error: Tests timed out."
        except Exception as e:
            return f"Error running tests: {e}"

    def apply_diff(self, path: str, diff_content: str) -> str:
        """Applies a unified diff to a file."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: File not found at {target_path}"

            # Write diff to a temporary file
            diff_file = self.project_path / ".temp.diff"
            diff_file.write_text(diff_content, encoding="utf-8")

            try:
                # Use patch command to apply diff
                command = ["patch", str(target_path), str(diff_file)]
                result = subprocess.run(
                    command,
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    text=True,
                    cwd=self.project_path,
                    timeout=30,
                )

                if result.returncode == 0:
                    logger.info(f"🩹 Applied diff to {path}")
                    msg = f"Successfully applied diff to {path}"
                    if path.endswith(".py"):
                        syntax_check = self.check_syntax(path)
                        msg += f"\nSyntax check: {syntax_check}"
                    return msg
                else:
                    return f"Error applying diff: {result.stderr}"
            finally:
                if diff_file.exists():
                    diff_file.unlink()
        except Exception as e:
            return f"Error applying diff: {e}"

    def search_symbols(self, pattern: str) -> str:
        """Searches for class and function definitions matching a pattern across the project."""
        try:
            # Use grep to find definitions
            # Python definitions: 'class Name' or 'def name'
            # We use a broad regex to match both
            grep_pattern = f"(class|def)[[:space:]]+.*{pattern}"

            command = ["grep", "-rnE", grep_pattern, "."]
            command.extend(
                [
                    "--exclude-dir=.git",
                    "--exclude-dir=__pycache__",
                    "--exclude-dir=node_modules",
                    "--exclude-dir=.venv",
                ]
            )

            result = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
                cwd=self.project_path,
                timeout=30,
            )

            output = result.stdout
            if not output:
                return f"No symbols found matching '{pattern}'."

            if len(output) > 5000:
                output = output[:5000] + "\n... [Output truncated]"

            logger.info(f"🔎 Symbol search: {pattern}")
            return output
        except Exception as e:
            return f"Error searching symbols: {str(e)}"

    def semantic_search(self, query: str) -> str:
        """
        Performs an enhanced search by looking for keywords in filenames,
        symbol definitions (classes/functions), and code content.
        Prioritizes definitions and filename matches.
        """
        try:
            keywords = [k.strip() for k in query.split() if len(k.strip()) > 2]
            if not keywords and query:
                keywords = [query.strip()]

            if not keywords:
                return "Error: Empty or too short query."

            results = []
            seen_files = set()

            # 1. Search in filenames (High priority)
            filename_matches = []
            exclude_dirs = {
                ".git",
                "__pycache__",
                "node_modules",
                ".venv",
                ".mypy_cache",
                ".pytest_cache",
                ".gemini_sessions",
                "gemini_env",
                "venv",
                "env",
            }
            for kw in keywords:
                # Use glob to find files containing keyword in name
                for match in self.project_path.rglob(f"*{kw}*"):
                    if match.is_file():
                        # Check if any part of the path is in exclude_dirs
                        parts = match.relative_to(self.project_path).parts
                        if any(
                            part in exclude_dirs or (part.startswith(".") and part != ".cursor")
                            for part in parts[:-1]
                        ):
                            continue

                        rel_path = str(match.relative_to(self.project_path))
                        if rel_path not in seen_files:
                            filename_matches.append(rel_path)
                            seen_files.add(rel_path)

            if filename_matches:
                results.append("### Relevant Files (by name):")
                for f in filename_matches[:10]:
                    results.append(f"- {f}")

            # 2. Search in definitions (symbols) (High priority)
            # We search for the full query first, then individual keywords
            symbol_results = []
            search_patterns = [query] + keywords
            for pattern in search_patterns:
                grep_pattern = f"(class|def)[[:space:]]+.*{pattern}"
                command = ["grep", "-rnE", grep_pattern, "."]
                for d in exclude_dirs:
                    command.append(f"--exclude-dir={d}")

                grep_res = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    cwd=self.project_path,
                    timeout=20,
                    errors="replace",
                )
                if grep_res.stdout:
                    for line in grep_res.stdout.splitlines():
                        if line.strip() and line not in symbol_results:
                            # Skip hidden files except in .cursor
                            if any(
                                part.startswith(".") and part != ".cursor"
                                for part in Path(line.split(":")[0]).parts
                            ):
                                continue
                            # Limit line length for safety
                            if len(line) > 500:
                                line = line[:500] + "..."
                            symbol_results.append(line)
                if len(symbol_results) > 15:
                    break

            if symbol_results:
                results.append("\n### Symbol Definitions Found:")
                results.extend(symbol_results[:15])

            # 3. Search in code content (Medium priority)
            content_matches = []
            # Search for the query as a phrase first
            grep_query = query
            command = ["grep", "-rn", grep_query, "."]
            for d in exclude_dirs:
                command.append(f"--exclude-dir={d}")

            grep_result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.project_path,
                timeout=20,
                errors="replace",
            )
            if grep_result.stdout:
                for line in grep_result.stdout.splitlines():
                    # Skip hidden files except in .cursor
                    if any(
                        part.startswith(".") and part != ".cursor"
                        for part in Path(line.split(":")[0]).parts
                    ):
                        continue
                    if len(line) > 500:
                        line = line[:500] + "..."
                    content_matches.append(line)

            # If few matches, add keyword searches
            if len(content_matches) < 10:
                for kw in keywords:
                    if (
                        kw.lower() in query.lower() and kw in query
                    ):  # only if it was part of original
                        command = ["grep", "-rn", kw, "."]
                        for d in exclude_dirs:
                            command.append(f"--exclude-dir={d}")
                        grep_result = subprocess.run(
                            command,
                            capture_output=True,
                            text=True,
                            cwd=self.project_path,
                            timeout=10,
                            errors="replace",
                        )
                        if grep_result.stdout:
                            for line in grep_result.stdout.splitlines():
                                # Skip hidden files except in .cursor
                                if any(
                                    part.startswith(".") and part != ".cursor"
                                    for part in Path(line.split(":")[0]).parts
                                ):
                                    continue
                                if len(line) > 500:
                                    line = line[:500] + "..."
                                if line not in content_matches:
                                    content_matches.append(line)
                                if len(content_matches) > 30:
                                    break
                    if len(content_matches) > 30:
                        break

            if content_matches:
                results.append("\n### Code Content Matches:")
                # Filter out lines that are already in symbol_results
                unique_content = [m for m in content_matches if m not in symbol_results]
                results.extend(unique_content[:20])
                if len(unique_content) > 20:
                    results.append(f"... and {len(unique_content) - 20} more matches.")

            final_output = "\n".join(results)

            # Truncate output if it's too large
            max_chars = 15000
            if len(final_output) > max_chars:
                final_output = (
                    final_output[:max_chars]
                    + f"\n... [Output truncated. Original size: {len(final_output)} chars]"
                )

            if not final_output:
                return f"No matches found for '{query}'. Try different keywords."

            logger.info(f"🧠 Enhanced semantic search for: {query}")
            return final_output
        except Exception as e:
            return f"Error in semantic search: {str(e)}"

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

    def list_dir_recursive(self, path: str = ".", depth: int = 2) -> str:
        """Lists files and directories recursively up to a specified depth."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: Directory not found at {target_path}"

            items = []
            base_depth = len(target_path.parts)

            for root, dirs, files in os.walk(target_path):
                current_depth = len(Path(root).parts) - base_depth
                if current_depth >= depth:
                    del dirs[:]  # Don't recurse deeper
                    continue

                rel_root = Path(root).relative_to(target_path)
                if str(rel_root) != ".":
                    items.append(f"DIR: {rel_root}")

                for f in files:
                    items.append(f"FILE: {rel_root / f}")

            result = "\n".join(items)
            logger.info(f"📂 Listed dir recursive: {path} (depth={depth})")
            return result if result else "(Empty directory)"
        except Exception as e:
            return f"Error listing directory recursively {path}: {str(e)}"

    def find_files(self, pattern: str, path: str = ".") -> str:
        """Find files matching a glob pattern."""
        try:
            target_path = self._validate_path(path)
            matches = list(target_path.rglob(pattern))
            if not matches:
                return "No files found matching pattern."

            # Limit results to avoid token overflow
            limit = 50
            result = "\n".join([str(p.relative_to(self.project_path)) for p in matches[:limit]])
            if len(matches) > limit:
                result += f"\n... and {len(matches) - limit} more files."

            logger.info(f"🔍 Found {len(matches)} files matching {pattern}")
            return result
        except Exception as e:
            return f"Error finding files: {str(e)}"

    def search_files(self, pattern: str, path: str = ".", case_sensitive: bool = True) -> str:
        """Search for a text pattern in files (grep-like)."""
        try:
            target_path = self._validate_path(path)
            if not target_path.exists():
                return f"Error: Path not found: {path}"

            command = ["grep", "-rn" if target_path.is_dir() else "-n"]
            if not case_sensitive:
                command.append("-i")

            command.extend([pattern, str(target_path)])

            # Исключаем некоторые директории для скорости
            if target_path.is_dir():
                command.extend(
                    [
                        "--exclude-dir=.git",
                        "--exclude-dir=__pycache__",
                        "--exclude-dir=node_modules",
                        "--exclude-dir=.venv",
                    ]
                )

            result = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
                cwd=self.project_path,
                timeout=30,
            )

            output = result.stdout
            if len(output) > 5000:
                output = output[:5000] + "\n... [Output truncated]"

            logger.info(f"🔎 Search content: {pattern} in {path}")
            return output if output else "No matches found."
        except subprocess.TimeoutExpired:
            return "Error: Search timed out."
        except Exception as e:
            return f"Error searching files: {str(e)}"

    def run_shell_command(self, command: str) -> str:
        """Executes a shell command in the project root."""
        try:
            # Security check: prevent dangerous commands
            forbidden = ["rm -rf /", ":(){ :|:& };:"]  # Fork bomb
            if any(cmd in command for cmd in forbidden):
                return "Error: Command denied for security reasons."

            logger.info(f"🚀 Executing shell: {command}")
            # Load environment variables from .env file in project root if it exists
            env_path = self.project_path / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded environment variables from {env_path}")

            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_path,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=120,  # 2 minutes timeout
                env={
                    **os.environ,
                    **dict(os.environ),
                },  # Explicitly pass current env which includes loaded .env
            )

            output = f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            output += f"Return Code: {result.returncode}"

            # Truncate output if it's too large
            max_chars = 10000
            if len(output) > max_chars:
                output = (
                    output[:max_chars]
                    + f"\n... [Output truncated. Original size: {len(output)} chars]"
                )

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

    def git_status(self) -> str:
        """Returns the current git status (branch, changed files, untracked files)."""
        try:
            command = ["git", "status"]
            result = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
                cwd=self.project_path,
                timeout=30,
            )
            if result.returncode != 0:
                return f"Error running git status: {result.stderr}"
            return result.stdout
        except Exception as e:
            return f"Error checking git status: {e}"

    def _execute_function_call(self, func_name: str, args: dict) -> dict:
        """Выполняет вызов функции по имени с переданными аргументами."""
        try:
            if func_name == "read_file":
                result = self.read_file(**args)
            elif func_name == "write_file":
                result = self.write_file(**args)
            elif func_name == "replace_in_file":
                result = self.replace_in_file(**args)
            elif func_name == "insert_at_line":
                result = self.insert_at_line(**args)
            elif func_name == "get_code_skeleton":
                result = self.get_code_skeleton(**args)
            elif func_name == "check_syntax":
                result = self.check_syntax(**args)
            elif func_name == "read_symbol":
                result = self.read_symbol(**args)
            elif func_name == "read_memory":
                result = self.read_memory(**args)
            elif func_name == "add_to_memory":
                result = self.add_to_memory(**args)
            elif func_name == "git_diff_check":
                result = self.git_diff_check(**args)
            elif func_name == "list_dir":
                result = self.list_dir(**args)
            elif func_name == "list_dir_recursive":
                result = self.list_dir_recursive(**args)
            elif func_name == "find_files":
                result = self.find_files(**args)
            elif func_name == "search_files":
                result = self.search_files(**args)
            elif func_name == "run_shell_command":
                result = self.run_shell_command(**args)
            elif func_name == "run_tests":
                result = self.run_tests(**args)
            elif func_name == "apply_diff":
                result = self.apply_diff(**args)
            elif func_name == "search_symbols":
                result = self.search_symbols(**args)
            elif func_name == "get_file_info":
                result = self.get_file_info(**args)
            elif func_name == "semantic_search":
                result = self.semantic_search(**args)
            else:
                result = f"Unknown function {func_name}"
            # Возвращаем результат как словарь, ожидаемый FunctionResponse
            return {"result": result}
        except Exception as e:
            logger.error(f"Error executing function {func_name}: {e}")
            return {"error": str(e)}

    def _load_session(self, session_id: str) -> list:
        """Loads chat history from a session file."""
        session_file = self.sessions_dir / f"{session_id}.pkl"
        if session_file.exists():
            try:
                with open(session_file, "rb") as f:
                    history = pickle.load(f)
                logger.info(f"Loaded session history from {session_file}")
                return history
            except Exception as e:
                logger.error(f"Failed to load session {session_id}: {e}")
        return []

    def _save_session(self, session_id: str, history: list):
        """Saves chat history to a session file."""
        if not session_id:
            return
        session_file = self.sessions_dir / f"{session_id}.pkl"
        try:
            with open(session_file, "wb") as f:
                pickle.dump(history, f)
            logger.info(f"Saved session history to {session_file}")
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")

    def execute(
        self, instruction: str, output_file_path: Path, control_phrase: str, session_id: str = None
    ):
        """
        Executes the instruction using the chat loop and tools.
        """
        print("🤖 Gemini Agent started.")
        print(f"📍 Project Path: {self.project_path}")
        print(f"📝 Instruction: {instruction}")
        if session_id:
            print(f"🆔 Session ID: {session_id}")

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
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),  # Ручная обработка
            )

            # Загружаем историю или создаем новую
            history = []
            if session_id:
                history = self._load_session(session_id)

            if not history:
                history = [
                    types.Content(parts=[types.Part.from_text(text=full_prompt)], role="user")
                ]
            else:
                # Если история есть, добавляем новое сообщение
                history.append(
                    types.Content(parts=[types.Part.from_text(text=full_prompt)], role="user")
                )

            if session_id:
                self._save_session(session_id, history)

            max_steps = 50
            final_text = None

            for step in range(max_steps):
                # Save session at each step to prevent data loss on crash
                if session_id:
                    self._save_session(session_id, history)

                # Trim history if it's too large to stay within context limits
                history = self._trim_history(history)

                # Estimate tokens for this request
                current_request_tokens = self._estimate_tokens(history)

                # Выполняем запрос к API с повторными попытками
                max_retries = 8  # Reduced slightly to fit into 300s timeout better
                response = None
                last_error = None

                for attempt in range(max_retries):
                    try:
                        # Manage rate limits (tokens per minute)
                        self._wait_for_rate_limit(current_request_tokens)

                        # Задержка между запросами для предотвращения 429 ошибки (по просьбе пользователя)
                        import random
                        import time

                        # Delay 1-2 seconds between requests
                        base_delay = 1.0 + random.uniform(0.5, 1.5)
                        logger.debug(f"Applied delay between requests: {base_delay:.2f}s")
                        time.sleep(base_delay)

                        response = self.client.models.generate_content(
                            model=self.model_name, contents=history, config=config
                        )
                        break
                    except Exception as e:
                        last_error = e
                        error_str = str(e).lower()
                        retryable_keywords = [
                            "429",
                            "too many requests",
                            "resource_exhausted",
                            "quota",
                            "limit",
                            "500",
                            "503",
                            "504",
                            "deadline",
                            "timeout",
                        ]

                        if (
                            any(kw in error_str for kw in retryable_keywords)
                            and attempt < max_retries - 1
                        ):
                            # Default backoff: 5, 10, 20, 40... capped
                            wait_time = min(60, (2**attempt) * 5)

                            # Try to extract "retry in X.Xs" or similar from Gemini error
                            import re

                            match = re.search(r"retry in (\d+(\.\d+)?)s", error_str)
                            if match:
                                try:
                                    suggested_wait = float(match.group(1))
                                    wait_time = max(wait_time, suggested_wait + 2)
                                    logger.info(
                                        f"Rate limit hit. Retry suggested in {suggested_wait}s. Waiting {wait_time}s."
                                    )
                                except ValueError:
                                    pass
                            else:
                                logger.warning(
                                    f"Gemini API retryable error: {e}. Waiting {wait_time}s before retry."
                                )

                            time.sleep(wait_time)
                        else:
                            # Если ошибка не исправима или попытки исчерпаны
                            logger.error(
                                f"Gemini API critical error after {attempt+1} attempts: {e}"
                            )
                            raise e

                if not response:
                    raise last_error or Exception(
                        "Failed to get response from Gemini API after retries"
                    )

                # Добавляем ответ модели в историю (включая мысли и вызовы функций)
                history.append(response.candidates[0].content)
                if session_id:
                    self._save_session(session_id, history)

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
                    print(f"\n💬 Thought:\n{final_text}\n")  # Streaming output emulation

                # Если есть вызовы функций, выполняем их
                if function_calls:
                    results = []
                    # Используем ThreadPoolExecutor для параллельного выполнения инструментов
                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=min(len(function_calls), 10)
                    ) as executor:
                        # Запускаем задачи
                        future_to_fc = {
                            executor.submit(self._execute_function_call, fc.name, fc.args): fc
                            for fc in function_calls
                        }

                        # Собираем результаты в том же порядке, в котором они были вызваны
                        for fc in function_calls:
                            # Находим соответствующий future
                            future = next(
                                f for f, func_call in future_to_fc.items() if func_call == fc
                            )
                            try:
                                result = future.result()
                                results.append((fc.name, result))
                                logger.info(f"Выполнено: {fc.name}")
                                print(f"🛠️ Tool Call Completed: {fc.name}")
                            except Exception as e:
                                logger.error(f"Ошибка при выполнении {fc.name}: {e}")
                                results.append((fc.name, {"error": str(e)}))

                    # Добавляем ответы функций в историю
                    for func_name, result in results:
                        history.append(
                            types.Content(
                                parts=[
                                    types.Part.from_function_response(
                                        name=func_name, response=result
                                    )
                                ],
                                role="function",
                            )
                        )

                    if session_id:
                        self._save_session(session_id, history)
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
                    logger.info(
                        f"Fixed double exclamation mark in control phrase: {double_bang_phrase} -> {control_phrase}"
                    )
                    final_text = final_text.replace(double_bang_phrase, control_phrase)

            # Добавляем контрольную фразу, если её нет
            if control_phrase not in final_text:
                final_text += f"\n\n{control_phrase}"

            # Сохраняем отчет
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path.write_text(final_text, encoding="utf-8")

            print("✅ Execution completed.")
            print(f"📄 Report saved to: {output_file_path}")

        except Exception as e:
            logger.error(f"Critical error during execution: {e}", exc_info=True)
            # В случае ошибки создаем файл с ошибкой, чтобы сервер не висел вечно
            error_msg = f"# Error Report\n\nTask failed with exception:\n```\n{str(e)}\n```\n\n{control_phrase}"
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path.write_text(error_msg, encoding="utf-8")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Gemini CLI Agent with Real Capabilities")
    parser.add_argument("instruction", type=str, help="The instruction to execute.")
    parser.add_argument("output_file_path", type=str, help="Path to save the final report.")
    parser.add_argument("control_phrase", type=str, help="Phrase to append to the report.")
    parser.add_argument("--project_path", type=str, default=".", help="Project root directory.")
    parser.add_argument(
        "--session_id", type=str, default=None, help="Session ID for continuing the conversation."
    )
    parser.add_argument("--version", action="version", version=f"Gemini CLI Agent v{__version__}")

    args = parser.parse_args()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY is not set in environment.", file=sys.stderr)
        sys.exit(1)

    agent = GeminiDeveloperAgent(api_key=api_key, project_path=Path(args.project_path))

    agent.execute(
        instruction=args.instruction,
        output_file_path=Path(args.output_file_path),
        control_phrase=args.control_phrase,
        session_id=args.session_id,
    )


if __name__ == "__main__":
    main()
