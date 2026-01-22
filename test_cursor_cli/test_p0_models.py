#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование P0 моделей: auto и grok
"""
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime

class P0ModelTester:
    def __init__(self, container_name: str = "cursor-agent", workspace: str = "/workspace"):
        self.container_name = container_name
        self.workspace = workspace
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
        
        # P0 модели для тестирования
        self.p0_models = ["auto", "grok"]
        
        # Тестовые промпты разной сложности
        self.test_prompts = {
            "simple": "Создай файл test_simple.txt с текстом 'Hello World'",
            "medium": "Создай простую функцию валидации email на Python в файле validate_email.py",
            "complex": "Создай REST API endpoint с аутентификацией в файле api.py"
        }
    
    def run_test(self, model: str, prompt: str, test_name: str, timeout: int = 120) -> Dict:
        """Выполнить один тест"""
        cmd_parts = ["docker", "exec", self.container_name, "bash", "-c"]
        
        # Формируем команду agent
        agent_cmd = ["cd", self.workspace, "&&", "/root/.local/bin/agent"]
        
        # Добавляем модель
        agent_cmd.extend(["--model", model])
        
        # Добавляем флаги
        agent_cmd.extend(["-p", f'"{prompt}"', "--force", "--approve-mcps"])
        
        # Объединяем в bash команду
        bash_cmd = " ".join(agent_cmd)
        cmd_parts.append(bash_cmd)
        
        start_time = time.time()
        result = {
            "test_name": test_name,
            "model": model,
            "prompt_type": "simple",  # Определить из prompt
            "command": bash_cmd,
            "success": False,
            "return_code": None,
            "duration": None,
            "stdout": "",
            "stderr": "",
            "billing_error": False,
            "timeout": False,
            "error": None,
            "timestamp": datetime.now().isoformat()
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
            result["stdout"] = proc.stdout[:1000]  # Первые 1000 символов
            result["stderr"] = proc.stderr[:1000]
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
    
    def test_all_p0_models(self):
        """Протестировать все P0 модели со всеми типами промптов"""
        print("=" * 80)
        print("TESTING P0 MODELS: auto and grok")
        print("=" * 80)
        
        all_results = []
        
        for model in self.p0_models:
            print(f"\n{'='*80}")
            print(f"Testing model: {model}")
            print(f"{'='*80}")
            
            for prompt_type, prompt in self.test_prompts.items():
                test_name = f"{model}_{prompt_type}"
                print(f"\n  Test: {test_name}")
                print(f"  Prompt: {prompt[:60]}...")
                
                result = self.run_test(model, prompt, test_name)
                all_results.append(result)
                
                # Вывод результата
                status = "[OK]" if result["success"] else "[FAIL]"
                if result["billing_error"]:
                    status = "[BILLING]"
                if result["timeout"]:
                    status = "[TIMEOUT]"
                
                print(f"  Result: {status}")
                print(f"  Code: {result['return_code']}, Time: {result['duration']:.2f}s")
                
                if result["success"] and result["stdout"]:
                    print(f"  Output: {result['stdout'][:100]}...")
                elif result["stderr"]:
                    print(f"  Error: {result['stderr'][:200]}...")
                
                # Пауза между тестами
                time.sleep(3)
        
        # Сохранение результатов
        results_file = self.results_dir / "p0_models_test.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*80}")
        print("RESULTS SUMMARY")
        print(f"{'='*80}")
        
        # Статистика
        total = len(all_results)
        successful = sum(1 for r in all_results if r["success"])
        failed = total - successful
        billing_errors = sum(1 for r in all_results if r["billing_error"])
        timeouts = sum(1 for r in all_results if r["timeout"])
        
        print(f"Total tests: {total}")
        print(f"Successful: {successful} [OK]")
        print(f"Failed: {failed} [FAIL]")
        print(f"Billing errors: {billing_errors} [BILLING]")
        print(f"Timeouts: {timeouts} [TIMEOUT]")
        
        # Результаты по моделям
        print(f"\nBy model:")
        for model in self.p0_models:
            model_results = [r for r in all_results if r["model"] == model]
            model_success = sum(1 for r in model_results if r["success"])
            avg_time = sum(r["duration"] for r in model_results) / len(model_results) if model_results else 0
            print(f"  {model}: {model_success}/{len(model_results)} successful, avg time: {avg_time:.2f}s")
        
        # Результаты по типам промптов
        print(f"\nBy prompt type:")
        for prompt_type in self.test_prompts.keys():
            prompt_results = [r for r in all_results if prompt_type in r["test_name"]]
            prompt_success = sum(1 for r in prompt_results if r["success"])
            print(f"  {prompt_type}: {prompt_success}/{len(prompt_results)} successful")
        
        print(f"\nResults saved to: {results_file}")
        print(f"{'='*80}")
        
        return all_results


if __name__ == "__main__":
    tester = P0ModelTester()
    tester.test_all_p0_models()
