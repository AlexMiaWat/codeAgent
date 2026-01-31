import os
import asyncio
import sys
import time
import re
import random
# Force UTF-8 for Windows console output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass # Python < 3.7

from typing import List, Dict, Any, Optional
try:
    from openai import AsyncOpenAI
    from tabulate import tabulate
except ImportError:
    print("Error: Required packages not installed. Please install: pip install openai tabulate")
    sys.exit(1)

# Configuration
KEYS_FILE = ".env.openai"
MAX_MODELS_L1 = 20
DELAY_L2 = 1.0
DELAY_L3 = 1.0
DELAY_L4 = 1.0
DELAY_L5 = 1.0

# Prompts
PROMPT_L2 = "Назови самых выдающихся людей и не только планеты земля, топ 5. Только перечили их через \",\" больше ничего не пиши!"
PROMPT_L3_TEMPLATE = "Для каких целей используют языковую модель {model_name} в сочетании с {max_tokens} токенов? Ответь 4мя словами"
PROMPT_L4_TASK = """
Напиши Python функцию `parse_log_line(line: str) -> dict`, которая парсит строку лога формата:
`[2024-03-20 10:15:30] ERROR [src.main:42] Connection failed: timeout`
Функция должна возвращать словарь с ключами: `timestamp`, `level`, `source`, `message`.
Используй модуль `re`. Если формат неверный, выбрось `ValueError`.
Только код функции, без примеров.
"""
PROMPT_L5_TASK = """
Ты Python-архитектор. Спроектируй workflow-executor: API 1k RPS, runs 2k/s peak, 100ms..12h. Stack: Py3.12, Postgres+Redis, без Kafka. Multi-tenant. Нельзя терять jobs, дубликаты возможны. OIDC + RBAC/ABAC + audit + secrets. Дай ответ строго:
ARCH(1-2 строки), DATA(3 табл+индексы), FLOW(6 шагов), IDEMP(1 строка), OBS(3 метрики+3 алерта), FAIL(1 строка).
"""

PROMPT_L4_JUDGE = """
Ты строгий Code Reviewer. Оцени код на Python по шкале 0-100.
Задача: Парсинг лога `[YYYY-MM-DD HH:MM:SS] LEVEL [source] message`.
Требования:
1. Использование модуля `re` (regex).
2. Обработка ошибок (ValueError при неверном формате).
3. Правильное извлечение всех 4 полей.
4. Отсутствие лишнего кода (print, main).

Ответ кандидата:
\"\"\"{answer}\"\"\"

Критерии снижения баллов:
- Нет regex (-30)
- Нет обработки ошибок (-20)
- Неверный паттерн regex (-30)
- Лишний код/комментарии (-10)

Верни ТОЛЬКО число (например: 85).
"""

# Static Token Map for models that don't report it
TOKEN_MAP = {
    "mistral-tiny": "32k",
    "mistral-small": "32k", 
    "mistral-medium": "32k",
    "open-mistral-nemo": "128k",
    "codestral-latest": "32k",
    "codestral-2501": "256k",
    "gpt-3.5-turbo": "16k",
    "gpt-4o": "128k",
    "gpt-4o-mini": "128k",
    "gemini-2.0-flash": "1M",
    "gemini-2.0-flash-exp": "1M",
    "gemini-2.0-flash-lite": "1M",
    "gemini-1.5-flash": "1M", 
    "gemini-1.5-pro": "2M",
    "gemma-2-9b": "8k",
    "llama-3-8b": "8k",
    "llama-3.1-8b": "128k",
    "claude-3-haiku": "200k",
    "claude-3.5-sonnet": "200k"
}

# Provider configurations
PROVIDERS = {
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "key_pattern": r"^sk-or-v1-[a-f0-9]{64}$",
        "priority_models": [
            "google/gemini-2.0-flash-001",
            "openai/gpt-3.5-turbo",
            "anthropic/claude-3-haiku",
            "mistralai/mistral-7b-instruct",
            "meta-llama/llama-3-8b-instruct"
        ]
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "key_pattern": r"^sk-[a-zA-Z0-9\-_]{20,}$",
        "priority_models": [
            "gpt-3.5-turbo",
            "gpt-4o-mini",
            "gpt-4"
        ]
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "key_pattern": r"^gsk_[a-zA-Z0-9]{50,}$",
        "priority_models": [
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma-7b-it"
        ]
    },
    "mistral": {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "key_pattern": r"^[a-zA-Z0-9]{32}$",
        "priority_models": [
            "mistral-tiny",
            "mistral-small",
            "open-mistral-7b",
            "codestral-latest"
        ]
    },
    "codestral": {
         "name": "Codestral",
         "base_url": "https://codestral.mistral.ai/v1", 
         "key_pattern": r"^[a-zA-Z0-9]{32}$",
         "priority_models": [
             "codestral-latest",
             "codestral-2205"
         ]
    },
    "google": {
        "name": "Google",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_pattern": r"^AIza[0-9A-Za-z\-_]{35}$",
        "priority_models": [
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ]
    },
    "cursor": {
        "name": "Cursor",
        "base_url": None, 
        "key_pattern": r"^key_[a-f0-9]{64}$",
        "priority_models": []
    }
}

def judge_l5_rule_based(answer: str) -> Dict[str, Any]:
    score = 0
    answer_lower = answer.lower()
    
    # Must-have (Senior indicators)
    if re.search(r'(pg|postgres).*source', answer_lower) or re.search(r'source.*(pg|postgres)', answer_lower): score += 2
    elif "postgres" in answer_lower: score += 1 # Partial credit for just mentioning Postgres

    if "idem" in answer_lower: score += 2
    if "uniq" in answer_lower: score += 1
    if "for update" in answer_lower or "lock" in answer_lower: score += 1
    if "backoff" in answer_lower and "jitter" in answer_lower: score += 1
    if "scheduler" in answer_lower or "scan" in answer_lower: score += 1
    if "run_age" in answer_lower or "age" in answer_lower or "p95" in answer_lower: score += 1
    if "heartbeat" in answer_lower: score += 1
    
    # Penalties
    if re.search(r'redis.*source', answer_lower): score -= 3
    if "tenant" not in answer_lower: score -= 1
    
    # Clamp
    score = max(0, min(10, score))
    
    # Grading
    if score >= 8: level = "🟢 SENIOR"
    elif score >= 5: level = "🟡 MIDDLE"
    elif score >= 3: level = "🟠 JUNIOR"
    else: level = "❌ FAILED"
    
    return {"score": score, "level": level}

class KeyTester:
    def __init__(self, raw_line: str, index: int):
        self.index = index
        self.raw_line = raw_line.strip()
        self.var_name = ""
        self.api_key = ""
        self._parse_line()
        self.provider_key = self._detect_provider()
        self.provider_config = PROVIDERS.get(self.provider_key, PROVIDERS["openai"])

        if self.provider_key == "cursor":
            self.client = None 
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.provider_config["base_url"]
            )
        
        self.model_metadata = {} 

    def _parse_line(self):
        if "=" in self.raw_line:
            parts = self.raw_line.split("=", 1)
            self.var_name = parts[0].strip()
            self.api_key = parts[1].strip()
        else:
            self.api_key = self.raw_line
            self.var_name = "UNKNOWN"
        self.api_key = self.api_key.strip('"').strip("'")

    def _detect_provider(self) -> str:
        key = self.api_key
        name = self.var_name.upper()

        if key.startswith("sk-or-"): return "openrouter"
        if key.startswith("gsk_"): return "groq"
        if key.startswith("sk-svcacct-") or key.startswith("sk-proj-"): return "openai"
        if key.startswith("key_"): return "cursor"
        if key.startswith("AIza"): return "google"
        
        if "OPENROUTER" in name: return "openrouter"
        if "GROQ" in name: return "groq"
        if "CURSOR" in name: return "cursor"
        if "CODESTRAL" in name: return "codestral"
        if "MISTRAL" in name: return "mistral"
        if "GEMENI" in name or "GEMINI" in name or "GOOGLE" in name or "VERTEX" in name: return "google"
        if "OPENAI" in name: return "openai"

        if len(key) == 32 and key.isalnum() and not key.startswith("sk-"):
            return "mistral"
        if key.startswith("AQ") and "." in key:
            return "google"

        return "openai"

    def validate_format(self) -> bool:
        pattern = self.provider_config.get("key_pattern")
        if pattern:
            return bool(re.match(pattern, self.api_key))
        return True

    def _get_max_tokens(self, model_id: str, model_obj: Any) -> str:
        # 1. Check dynamic info
        if hasattr(model_obj, 'context_window'): return str(model_obj.context_window)
        if hasattr(model_obj, 'context_length'): return str(model_obj.context_length)
        if hasattr(model_obj, 'top_provider') and isinstance(model_obj.top_provider, dict):
            return str(model_obj.top_provider.get('context_length', '?'))
        
        # 2. Check Static Map (Fuzzy match)
        for k, v in TOKEN_MAP.items():
            if k in model_id:
                return v
        
        return "?"

    async def get_available_models(self) -> List[Any]:
        if not self.client: return []
        try:
            response = await self.client.models.list()
            for m in response.data:
                self.model_metadata[m.id] = {
                    "max_tokens": self._get_max_tokens(m.id, m)
                }
            return response.data
        except Exception:
            return []

    async def test_generation_simple(self, model: str) -> bool:
        """Level 1: Simple 'Hi' test."""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                timeout=8.0
            )
            return bool(response.choices and response.choices[0].message.content)
        except Exception:
            return False

    async def test_generation_full(self, model: str) -> Dict[str, Any]:
        """Level 2: Complex prompt test."""
        result = {"model": model, "status": "FAIL", "time_l1": 0.0, "time_l2": 0.0, "content": "", "error": None}
        try:
            start = time.time()
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": PROMPT_L2}],
                max_tokens=300, 
                timeout=30.0
            )
            elapsed = time.time() - start
            result["time_l2"] = round(elapsed, 2)
            content = response.choices[0].message.content
            if content:
                result["status"] = "OK"
                result["content"] = content.strip()
            else:
                result["status"] = "EMPTY"
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "ERROR"
        return result

    async def test_generation_l3(self, model: str, max_tokens_str: str) -> Dict[str, Any]:
        """Level 3: Specific context question."""
        prompt = PROMPT_L3_TEMPLATE.format(model_name=model, max_tokens=max_tokens_str)
        result = {"model": model, "status": "FAIL", "time_l3": 0.0, "content": "", "error": None}
        try:
            start = time.time()
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                timeout=30.0
            )
            elapsed = time.time() - start
            result["time_l3"] = round(elapsed, 2)
            content = response.choices[0].message.content
            if content:
                result["status"] = "OK"
                result["content"] = content.strip()
            else:
                result["status"] = "EMPTY"
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "ERROR"
        return result

    async def test_generation_l4(self, model: str) -> Dict[str, Any]:
        """Level 4: Coding Task."""
        result = {"model": model, "status": "FAIL", "time_l4": 0.0, "content": "", "error": None}
        try:
            start = time.time()
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": PROMPT_L4_TASK}],
                max_tokens=300,
                timeout=40.0
            )
            elapsed = time.time() - start
            result["time_l4"] = round(elapsed, 2)
            content = response.choices[0].message.content
            if content:
                result["status"] = "OK"
                result["content"] = content.strip()
            else:
                result["status"] = "EMPTY"
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "ERROR"
        return result

    async def test_generation_l5(self, model: str) -> Dict[str, Any]:
        """Level 5: Architecture Task."""
        result = {"model": model, "status": "FAIL", "time_l5": 0.0, "content": "", "error": None, "l5_score": 0, "l5_level": "FAIL"}
        try:
            start = time.time()
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": PROMPT_L5_TASK}],
                max_tokens=600,
                timeout=60.0
            )
            elapsed = time.time() - start
            result["time_l5"] = round(elapsed, 2)
            content = response.choices[0].message.content
            if content:
                result["status"] = "OK"
                result["content"] = content.strip()
                # Auto-judge immediately
                judge_res = judge_l5_rule_based(content)
                result["l5_score"] = judge_res["score"]
                result["l5_level"] = judge_res["level"]
            else:
                result["status"] = "EMPTY"
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "ERROR"
        return result

    # Add judge capability
    async def judge_answer(self, model: str, answer_to_judge: str) -> int:
        try:
            prompt = PROMPT_L4_JUDGE.format(answer=answer_to_judge)
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                timeout=20.0
            )
            content = response.choices[0].message.content.strip()
            # Extract number
            match = re.search(r'\d+', content)
            if match:
                score = int(match.group())
                return min(100, max(0, score)) # Clamp
            return 50 # Default if no number
        except:
            return 0

    async def run_test(self) -> Dict[str, Any]:
        result = {
            "id": self.index,
            "provider": self.provider_config["name"],
            "key_preview": f"...{self.api_key[-6:]}" if len(self.api_key) > 6 else self.api_key,
            "valid_format": False,
            "final_results": [], # Will hold L4+L5 complete results
            "tester_instance": self # Reference to self for judging later
        }

        if self.provider_key == "cursor": return result
        if not self.validate_format(): return result
        result["valid_format"] = True

        # 1. Get Models
        model_objects = await self.get_available_models()
        available_model_ids = [m.id for m in model_objects]
        
        # Select models for L1 
        target_models_l1 = []
        if available_model_ids:
            priority = self.provider_config.get("priority_models", [])
            for p in priority:
                if p in available_model_ids: target_models_l1.append(p)
                else:
                    for av in available_model_ids:
                        if av.endswith(f"/{p}") or av == f"models/{p}":
                            target_models_l1.append(av)
                            break
            # Теперь добавляем все оставшиеся модели, не ограничивая их количество
            for m in available_model_ids:
                if m not in target_models_l1: target_models_l1.append(m)
        else:
            target_models_l1 = self.provider_config.get("priority_models", [])[:3]

        target_models_l1 = list(set(target_models_l1))
        
        print(f"Key #{self.index} ({self.provider_config['name']}): Testing {len(target_models_l1)} models (Level 1)...")
        
        # L1
        passed_l1 = []
        for model in target_models_l1:
            start = time.time()
            if await self.test_generation_simple(model):
                passed_l1.append({"model": model, "time_l1": round(time.time() - start, 2)})
            await asyncio.sleep(0.1)

        print(f"  > Key #{self.index}: {len(passed_l1)} passed L1. Starting L2...")

        # L2
        passed_l2 = []
        for item in passed_l1:
            model = item["model"]
            l2_res = await self.test_generation_full(model)
            l2_res.update(item)
            l2_res["max_tokens"] = self.model_metadata.get(model, {}).get("max_tokens", "?")
            if l2_res["status"] == "OK": passed_l2.append(l2_res)
            await asyncio.sleep(DELAY_L2)

        print(f"  > Key #{self.index}: {len(passed_l2)} passed L2. Starting L3...")

        # L3
        passed_l3 = []
        for item in passed_l2:
            l3_res = await self.test_generation_l3(item["model"], item["max_tokens"])
            item["time_l3"] = l3_res["time_l3"]
            item["content_l3"] = l3_res["content"]
            if l3_res["status"] == "OK": passed_l3.append(item)
            await asyncio.sleep(DELAY_L3)

        print(f"  > Key #{self.index}: {len(passed_l3)} passed L3. Starting L4 (Intellect)...")

        # L4
        passed_l4 = []
        for item in passed_l3:
            l4_res = await self.test_generation_l4(item["model"])
            item["time_l4"] = l4_res["time_l4"]
            item["content_l4"] = l4_res["content"]
            if l4_res["status"] == "OK":
                passed_l4.append(item)
            await asyncio.sleep(DELAY_L4)
            
        print(f"  > Key #{self.index}: {len(passed_l4)} passed L4. Starting L5 (Architecture)...")

        # L5
        for item in passed_l4:
            l5_res = await self.test_generation_l5(item["model"])
            item["time_l5"] = l5_res["time_l5"]
            item["content_l5"] = l5_res["content"]
            item["l5_score"] = l5_res["l5_score"]
            item["l5_level"] = l5_res["l5_level"]
            item["total_time"] = item["time_l1"] + item["time_l2"] + item["time_l3"] + item["time_l4"] + item["time_l5"]
            if l5_res["status"] == "OK":
                result["final_results"].append(item)
            await asyncio.sleep(DELAY_L5)

        return result

async def main():
    if not os.path.exists(KEYS_FILE):
        print(f"Error: {KEYS_FILE} not found.")
        return

    with open(KEYS_FILE, "r") as f:
        lines = [line.strip() for line in f.readlines()]
    
    valid_lines = [l for l in lines if l and not l.startswith("#") and "MODEL_NAME" not in l and "USE_VERTEXAI" not in l]

    print(f"Found {len(valid_lines)} keys. Starting Deep Test Pipeline (L1->L5)...\n")

    testers = [KeyTester(line, i+1) for i, line in enumerate(valid_lines)]
    tasks = [t.run_test() for t in testers]
    
    results = await asyncio.gather(*tasks)
    
    # Harvest Candidates for Judging
    candidates = []
    potential_judges = [] # List of (Tester, ModelName) tuples
    
    for r in results:
        for t in r["final_results"]:
            candidate = {
                "provider": r["provider"],
                "key": r["key_preview"],
                "model": t["model"],
                "max_tokens": t.get("max_tokens", "?"),
                "l1": t["time_l1"], "l2": t["time_l2"], "l3": t["time_l3"], "l4": t["time_l4"], "l5": t["time_l5"],
                "total": t["total_time"],
                "content_l4": t["content_l4"],
                "content_l5": t["content_l5"],
                "l5_level": t["l5_level"],
                "l5_score": t["l5_score"],
                "snippet": f"L5 Level: {t['l5_level']}\nL4: {t['content_l4']}\nL5: {t['content_l5']}",
                "thinking_score": 0
            }
            candidates.append(candidate)
            # Add to potential judges list if it's a capable model
            m_lower = t["model"].lower()
            if "gpt-4" in m_lower or "gemini-2" in m_lower or "mistral-large" in m_lower or "claude" in m_lower or "codestral" in m_lower:
                potential_judges.append((r["tester_instance"], t["model"]))

    # Select Judges (3 unique providers if possible)
    judges = []
    seen_providers = set()
    # Sort potential judges by reliability (heuristic)
    random.shuffle(potential_judges)
    
    for tester, model in potential_judges:
        if tester.provider_config["name"] not in seen_providers:
            judges.append((tester, model))
            seen_providers.add(tester.provider_config["name"])
        if len(judges) >= 3: break
    
    # Fill if needed
    if len(judges) < 3 and potential_judges:
        for tester, model in potential_judges:
            if (tester, model) not in judges:
                judges.append((tester, model))
            if len(judges) >= 3: break

    judge_names = [f"{j[0].provider_config['name']}:{j[1]}" for j in judges]
    print(f"\nSelected {len(judges)} Judges: {judge_names}")

    # Run Evaluation
    print("Running Intellectual Evaluation (Thinking Score)...")
    for cand in candidates:
        scores = []
        if not judges:
            cand["thinking_score"] = 0
            continue
            
        for tester, model in judges:
            s = await tester.judge_answer(model, cand["content_l4"])
            scores.append(s)
            await asyncio.sleep(0.5) # Avoid rate limits on judges
        
        avg_score = sum(scores) / len(scores) if scores else 0
        cand["thinking_score"] = int(avg_score)
        print(f"  > {cand['model']} score: {cand['thinking_score']}%")

    print("\n\n" + "="*80)
    print("🏆 FINAL WINNERS SUMMARY (Sorted by Seniority -> Thinking -> Fastest Time) 🏆")
    print("="*80)
    
    if not candidates:
        print("No models passed all levels.")
        return

    # Sort: 1. L5 Score (Desc) (Matches Level), 2. Thinking Score (Desc), 3. Total Time (Asc)
    candidates.sort(key=lambda x: (-x["l5_score"], -x["thinking_score"], x["total"]))

    # Table
    headers = ["Provider", "Model", "Tokens", "Level (L5)", "Thinking", "L1", "L2", "L3", "L4", "L5", "Total(s)", "Response Snippet"]
    rows = []
    for w in candidates:
        ctx = w["max_tokens"]
        try:
            if ctx != "?" and int(ctx) >= 1000: ctx = f"{int(ctx)//1000}k"
        except: pass

        rows.append([
            w["provider"],
            w["model"], 
            ctx,
            w["l5_level"],
            f"{w['thinking_score']}%",
            w["l1"], w["l2"], w["l3"], w["l4"], w["l5"],
            round(w["total"], 2),
            w["snippet"] # Removed truncation
        ])
    
    print(tabulate(rows, headers=headers, tablefmt="fancy_grid"))

if __name__ == "__main__":
    asyncio.run(main())
