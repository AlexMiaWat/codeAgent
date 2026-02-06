"""
Утилиты для безопасности и защиты чувствительных данных
"""

import re
import logging
from typing import Any, Dict, List, Union


def sanitize_for_logging(data: Union[str, Dict[str, Any], List[Any], Any]) -> Union[str, Dict[str, Any], List[Any], Any]:
    """
    Удаляет чувствительные данные из данных для безопасного логирования
    
    Заменяет значения ключей, содержащих чувствительные слова, на '***REDACTED***'
    
    Args:
        data: Данные для санитизации (строка, словарь, список или другой тип)
    
    Returns:
        Санитизированные данные
    """
    # Список ключевых слов, которые указывают на чувствительные данные
    sensitive_keywords = [
        'api_key', 'apikey', 'api-key',
        'password', 'passwd', 'pwd',
        'token', 'secret', 'secret_key',
        'access_token', 'refresh_token',
        'auth', 'authorization',
        'credential', 'credentials',
        'private_key', 'privatekey',
        'session_id', 'sessionid',
        'bearer'
    ]
    
    if isinstance(data, dict):
        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            # Проверяем, содержит ли ключ чувствительное слово
            key_lower = str(key).lower()
            is_sensitive = any(keyword in key_lower for keyword in sensitive_keywords)
            
            if is_sensitive:
                # Если значение - строка, показываем только длину
                if isinstance(value, str):
                    sanitized[key] = f"***REDACTED*** (length: {len(value)})"
                else:
                    sanitized[key] = "***REDACTED***"
            else:
                # Рекурсивно обрабатываем вложенные структуры
                sanitized[key] = sanitize_for_logging(value)
        
        return sanitized
    
    elif isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]
    
    elif isinstance(data, str):
        # Проверяем, не содержит ли строка похожий на API ключ паттерн
        # Паттерны для различных типов ключей
        api_key_patterns = [
            r'sk-[a-zA-Z0-9]{20,}',  # OpenAI/Anthropic ключи
            r'sk-or-v1-[a-zA-Z0-9]{20,}',  # OpenRouter ключи
            r'sk-ant-[a-zA-Z0-9]{20,}',  # Anthropic ключи
            r'[a-zA-Z0-9]{32,}',  # Общий паттерн для длинных ключей
        ]
        
        for pattern in api_key_patterns:
            if re.search(pattern, data):
                return f"***REDACTED*** (matches API key pattern, length: {len(data)})"
        
        return data
    
    else:
        # Для других типов возвращаем как есть
        return data

_SECRET_VALUE_PATTERNS = [
    # Key=value or Key: value patterns
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|pwd|authorization|bearer)\b([\s:=]+)([^\s,;]+)"),
    # Bearer tokens
    re.compile(r"(?i)\b(bearer)\s+([A-Za-z0-9._-]{8,})"),
    # Common API key formats
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}"),
    re.compile(r"sk-ant-[A-Za-z0-9]{20,}"),
]


def redact_secrets_in_text(text: str) -> str:
    # Redact secrets in a log message string.
    if not isinstance(text, str) or not text:
        return text
    redacted = text
    for pattern in _SECRET_VALUE_PATTERNS:
        def _repl(match: re.Match) -> str:
            if match.lastindex and match.lastindex >= 3:
                key = match.group(1)
                sep = match.group(2)
                return f"{key}{sep}***REDACTED***"
            if match.lastindex and match.lastindex >= 2:
                key = match.group(1)
                return f"{key} ***REDACTED***"
            return "***REDACTED***"
        redacted = pattern.sub(_repl, redacted)
    return redacted


class SensitiveDataFilter(logging.Filter):
    # Logging filter that redacts secrets from messages and args.
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redact_secrets_in_text(record.msg)
            else:
                record.msg = sanitize_for_logging(record.msg)

            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: sanitize_for_logging(v) if not isinstance(v, str) else redact_secrets_in_text(v) for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        sanitize_for_logging(a) if not isinstance(a, str) else redact_secrets_in_text(a)
                        for a in record.args
                    )
        except Exception:
            return True
        return True



def redact_sensitive_string(value: str, show_length: bool = True) -> str:
    """
    Скрывает чувствительную строку, оставляя только длину
    
    Args:
        value: Строка для скрытия
        show_length: Показывать ли длину строки
    
    Returns:
        Скрытая строка
    """
    if not isinstance(value, str):
        return "***REDACTED***"
    
    if show_length:
        return f"***REDACTED*** (length: {len(value)})"
    else:
        return "***REDACTED***"
