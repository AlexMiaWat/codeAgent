#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class CursorCLITester:
    def __init__(self, container_name: str = "cursor-agent-life", workspace: str = "/workspace"):
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
        
        return result
    
    def test_all_models(self, prompt_type: str = "simple") -> List[Dict]:
        """Протестировать все модели с базовой комбинацией флагов"""
        prompt = self.test_prompts[prompt_type]
        flags = ["-p", "--force", "--approve-mcps"]
        
        results = []
        print(f"\n=== Testing all models (prompt: {prompt_type}) ===")
        
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
            
            # Пауза между тестами
            time.sleep(2)
        
        return results
    
    def test_flag_combinations(self, model: str = "claude-haiku") -> List[Dict]:
        """Протестировать все комбинации флагов с одной моделью"""
        prompt = self.test_prompts["simple"]
        
        results = []
        print(f"\n=== Testing flag combinations (model: {model or 'auto'}) ===")
        
        for flags in self.flag_combinations:
            flags_str = " ".join(flags)
            print(f"Testing flags: {flags_str}")
            
            result = self.run_command(model, prompt, flags)
            result["flags"] = flags_str
            results.append(result)
            
            status = "[OK]" if result["success"] else "[FAIL]"
            print(f"  {status} Code: {result['return_code']}, Time: {result['duration']:.2f}s")
            
            time.sleep(2)
        
        return results
    
    def save_results(self, results: List[Dict], filename: str):
        """Сохранить результаты в CSV"""
        if not results:
            return
        
        filepath = self.results_dir / filename
        fieldnames = results[0].keys()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\nResults saved: {filepath}")
    
    def generate_summary(self, all_results: Dict[str, List[Dict]]) -> Dict:
        """Сгенерировать сводку результатов"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": sum(len(r) for r in all_results.values()),
            "successful": 0,
            "failed": 0,
            "billing_errors": 0,
            "timeouts": 0,
            "working_models": [],
            "working_combinations": [],
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
        
        return summary
    
    def run_full_test_suite(self):
        """Запустить полный набор тестов"""
        print("=" * 80)
        print("STARTING FULL CURSOR CLI TESTING")
        print("=" * 80)
        
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
