#!/usr/bin/env python3

# -*- coding: utf-8 -*-

# #region agent log

import json

import time

import os

from pathlib import Path

import sys # Added for stderr



# Ensure the log directory exists

log_dir = Path("d:/Space/codeAgent/.cursor")

print(f"Attempting to create log directory: {log_dir}", file=sys.stderr)

log_dir.mkdir(parents=True, exist_ok=True)

print(f"Log directory creation complete.", file=sys.stderr)



# Attempt to write a very early log to diagnose file creation issues

print(f"Attempting to write very early log to: {log_dir}/debug.log", file=sys.stderr)

with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

    f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H1", "location": "test_runner.py:very_early_script_start", "message": "test_runner.py script started - very early log", "timestamp": time.time(), "cwd": os.getcwd()}) + "\n")

print(f"Very early log written.", file=sys.stderr)



# #endregion

"""

Скрипт автоматизации тестирования Cursor CLI параметров

"""

import subprocess

import json

import csv

import time

import sys

import io

from pathlib import Path

from typing import Dict, List, Optional

from datetime import datetime



# Исправление кодировки для Windows

# if sys.platform == 'win32':

#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')



class CursorCLITester:

    def __init__(self, container_name: str = "cursor-agent", workspace: str = "/workspace"):

        self.container_name = container_name

        self.workspace = workspace

        self.results_dir = Path("results")

        self.results_dir.mkdir(exist_ok=True)

        

        # Тестовые модели (на основе реально доступных)

        self.models = [

            "",  # Auto (без флага -m)

            "auto",

            "gemini-3-flash",  # Дешевая модель

            "gemini-3-pro",    # Средняя модель

            "sonnet-4.5",      # Премиальная модель

            "opus-4.5",        # Премиальная модель

            "gpt-5.2",         # Премиальная модель

            "gpt-5.2-codex",  # Премиальная модель

            "grok"             # Альтернативная модель

        ]

        

        # Тестовые промпты

        self.test_prompts = {

            "simple": "Создай файл test.txt с текстом 'Hello'",

            "medium": "Создай простую функцию валидации email на Python",

            "complex": "Создай REST API endpoint с аутентификацией"

        }

        

        # Комбинации флагов

        self.flag_combinations = [

            ["-p"],

            ["-p", "--force"],

            ["-p", "--force", "--approve-mcps"],

            ["-p", "--force", "--approve-mcps", "--verbose"]

        ]

    

    def run_command(self, model: str, prompt: str, flags: List[str], timeout: int = 60) -> Dict:

        """Выполнить команду и вернуть результат"""

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H1", "location": "test_runner.py:run_command_entry", "message": "Entering run_command", "data": {"model": model, "prompt": prompt, "flags": flags, "timeout": timeout}, "timestamp": time.time()}) + "\n")

        # #endregion



        cmd_parts = ["docker", "exec", self.container_name, "bash", "-c"]

        

        # Формируем команду agent

        agent_cmd = ["cd", self.workspace, "&&", "/root/.local/bin/agent"]

        

        # Добавляем модель если указана (используем --model, а не -m)

        if model:

            agent_cmd.extend(["--model", model])

        

        # Добавляем флаги

        agent_cmd.extend(flags)

        

        # Добавляем prompt

        agent_cmd.append(f'"{prompt}"')

        

        # Объединяем в bash команду

        bash_cmd = " ".join(agent_cmd)

        cmd_parts.append(bash_cmd)

        

        start_time = time.time()

        result = {

            "model": model or "auto",

            "prompt_type": "simple",  # Определить из prompt

            "flags": " ".join(flags),

            "command": bash_cmd,

            "success": False,

            "return_code": None,

            "duration": None,

            "stdout": "",

            "stderr": "",

            "billing_error": False,

            "timeout": False,

            "error": None

        }

        

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H1", "location": "test_runner.py:run_command_before_exec", "message": "Executing command", "data": {"cmd_parts": cmd_parts, "bash_cmd": bash_cmd}, "timestamp": time.time()}) + "\n")

        # #endregion



        try:

            proc = subprocess.run(

                cmd_parts,

                capture_output=True,

                text=True,

                timeout=timeout,

                encoding='utf-8',

                errors='replace'

            )

            

            result["return_code"] = proc.returncode

            result["stdout"] = proc.stdout[:500]  # Первые 500 символов

            result["stderr"] = proc.stderr[:500]

            result["success"] = proc.returncode == 0

            result["billing_error"] = "unpaid invoice" in proc.stderr.lower() or "pay your invoice" in proc.stderr.lower()

            result["duration"] = time.time() - start_time

            

        except subprocess.TimeoutExpired:

            result["timeout"] = True

            result["duration"] = timeout

            result["error"] = "Timeout"

        except Exception as e:

            result["error"] = str(e)

            # #region agent log

            with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

                f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H3", "location": "test_runner.py:run_command_exception", "message": "Exception during command execution", "data": {"error": str(e)}, "timestamp": time.time()}) + "\n")

            # #endregion

        

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H1", "location": "test_runner.py:run_command_exit", "message": "Exiting run_command", "data": {"result": result}, "timestamp": time.time()}) + "\n")

        # #endregion

        return result



    def test_all_models(self, prompt_type: str = "simple") -> List[Dict]:

        """Протестировать все модели с базовой комбинацией флагов"""

        prompt = self.test_prompts[prompt_type]

        flags = ["-p", "--force", "--approve-mcps"]

        

        results = []

        print(f"\n=== Testing all models (prompt: {prompt_type}) ===")

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H2", "location": "test_runner.py:test_all_models_entry", "message": "Entering test_all_models", "data": {"prompt_type": prompt_type, "prompt": prompt, "flags": flags}, "timestamp": time.time()}) + "\n")

        # #endregion



        for model in self.models:

            print(f"Testing model: {model or 'auto'}")

            result = self.run_command(model, prompt, flags)

            results.append(result)

            

            # Вывод результата

            status = "[OK]" if result["success"] else "[FAIL]"

            if result["billing_error"]:

                status = "[BILLING]"

            if result["timeout"]:

                status = "[TIMEOUT]"

            

            print(f"  {status} Code: {result['return_code']}, Time: {result['duration']:.2f}s")

            

            # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H2", "location": "test_runner.py:test_all_models_loop", "message": "Model test iteration complete", "data": {"model": model, "result_summary": status}, "timestamp": time.time()}) + "\n")

            # #endregion



            # Пауза между тестами

            time.sleep(2)

        

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H2", "location": "test_runner.py:test_all_models_exit", "message": "Exiting test_all_models", "data": {"num_results": len(results)}, "timestamp": time.time()}) + "\n")

        # #endregion

        return results

    

    def test_flag_combinations(self, model: str = "claude-haiku") -> List[Dict]:

        """Протестировать все комбинации флагов с одной моделью"""

        prompt = self.test_prompts["simple"]

        

        results = []

        print(f"\n=== Testing flag combinations (model: {model or 'auto'}) ===")

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H2", "location": "test_runner.py:test_flag_combinations_entry", "message": "Entering test_flag_combinations", "data": {"model": model, "prompt": prompt}, "timestamp": time.time()}) + "\n")

        # #endregion

        

        for flags in self.flag_combinations:

            flags_str = " ".join(flags)

            print(f"Testing flags: {flags_str}")

            

            result = self.run_command(model, prompt, flags)

            result["flags"] = flags_str

            results.append(result)

            

            status = "[OK]" if result["success"] else "[FAIL]"

            print(f"  {status} Code: {result['return_code']}, Time: {result['duration']:.2f}s")



            # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H2", "location": "test_runner.py:test_flag_combinations_loop", "message": "Flag combination test iteration complete", "data": {"flags": flags_str, "result_summary": status}, "timestamp": time.time()}) + "\n")

            # #endregion

            

            time.sleep(2)

        

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H2", "location": "test_runner.py:test_flag_combinations_exit", "message": "Exiting test_flag_combinations", "data": {"num_results": len(results)}, "timestamp": time.time()}) + "\n")

        # #endregion

        return results

    

    def save_results(self, results: List[Dict], filename: str):

        """Сохранить результаты в CSV"""

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H3", "location": "test_runner.py:save_results_entry", "message": "Entering save_results", "data": {"filename": filename, "num_results": len(results) if results else 0}, "timestamp": time.time()}) + "\n")

        # #endregion

        if not results:

            # #region agent log

            with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

                f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H3", "location": "test_runner.py:save_results_no_results", "message": "No results to save", "data": {"filename": filename}, "timestamp": time.time()}) + "\n")

            # #endregion

            return

        

        filepath = self.results_dir / filename

        fieldnames = results[0].keys()

        

        with open(filepath, 'w', newline='', encoding='utf-8') as f:

            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()

            writer.writerows(results)

        

        print(f"\nResults saved: {filepath}")

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H3", "location": "test_runner.py:save_results_exit", "message": "Exiting save_results", "data": {"filepath": str(filepath)}, "timestamp": time.time()}) + "\n")

    def generate_summary(self, all_results: Dict[str, List[Dict]]) -> Dict:
        """Сгенерировать сводку результатов"""
        # #region agent log
        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H3", "location": "test_runner.py:generate_summary_entry", "message": "Entering generate_summary", "data": {"num_result_categories": len(all_results)}, "timestamp": time.time()}) + "\n")
        # #endregion

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": sum(len(r) for r in all_results.values()),
            "successful": 0,
            "failed": 0,
            "billing_errors": 0,
            "timeouts": 0,
            "working_models": [],
            "recommendations": []
        }

        # Анализ результатов
        for category, results in all_results.items():
            for result in results:
                if result["success"]:
                    summary["successful"] += 1
                    if category == "models" and result["model"] not in summary["working_models"]:
                        summary["working_models"].append(result["model"])
                else:
                    summary["failed"] += 1

                if result["billing_error"]:
                    summary["billing_errors"] += 1

                if result["timeout"]:
                    summary["timeouts"] += 1

        # Рекомендации
        if summary["billing_errors"] > 0:
            summary["recommendations"].append("Использовать дешевые модели (claude-haiku, gpt-4o-mini)")

        if summary["timeouts"] > 0:
            summary["recommendations"].append("Увеличить таймаут или проверить контейнер")

        if summary["working_models"]:
            summary["recommendations"].append(f"Рекомендуемые модели: {', '.join(summary['working_models'][:3])}")

        # #region agent log
        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H3", "location": "test_runner.py:generate_summary_exit", "message": "Exiting generate_summary", "data": {"summary": summary}, "timestamp": time.time()}) + "\n")
        # #endregion

        return summary
    def run_full_test_suite(self):

        """Запустить полный набор тестов"""

        print("=" * 80)

        print("STARTING FULL CURSOR CLI TESTING")

        print("=" * 80)

        

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H2", "location": "test_runner.py:run_full_test_suite_entry", "message": "Entering run_full_test_suite", "timestamp": time.time()}) + "\n")

        # #endregion



        all_results = {}

        

        # 1. Тестирование всех моделей

        all_results["models_simple"] = self.test_all_models("simple")

        self.save_results(all_results["models_simple"], "models_simple.csv")

        

        # 2. Тестирование комбинаций флагов

        all_results["flags"] = self.test_flag_combinations("gemini-3-flash")

        self.save_results(all_results["flags"], "flags_test.csv")

        

        # 3. Генерация сводки

        summary = self.generate_summary(all_results)

        

        # Сохранение сводки

        summary_file = self.results_dir / "summary.json"

        with open(summary_file, 'w', encoding='utf-8') as f:

            json.dump(summary, f, indent=2, ensure_ascii=False)

        

        # Вывод сводки

        print("\n" + "=" * 80)

        print("TEST RESULTS SUMMARY")

        print("=" * 80)

        # #region agent log

        with open("d:/Space/codeAgent/.cursor/debug.log", "a", encoding="utf-8") as f:

            f.write(json.dumps({"sessionId": "debug-session", "runId": "run4", "hypothesisId": "H3", "location": "test_runner.py:generate_summary_exit", "message": "Exiting generate_summary", "data": {"summary": summary}, "timestamp": time.time()}) + "\n")

        # #endregion

        print(f"Total tests: {summary['total_tests']}")

        print(f"Successful: {summary['successful']} [OK]")

        print(f"Failed: {summary['failed']} [FAIL]")

        print(f"Billing errors: {summary['billing_errors']} [BILLING]")

        print(f"Timeouts: {summary['timeouts']} [TIMEOUT]")

        print(f"\nWorking models: {', '.join(summary['working_models'])}")

        print(f"\nRecommendations:")

        for rec in summary["recommendations"]:

            print(f"  - {rec}")

        print("\n" + "=" * 80)



if __name__ == "__main__":

    tester = CursorCLITester()

    tester.run_full_test_suite()
