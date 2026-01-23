"""
JsonValidator - валидация JSON ответов

Ответственность:
- Синтаксическая валидация
- Schema validation
- Извлечение JSON из текста
- Обработка malformed ответов
"""

import json
import logging
import re
from typing import Optional, Any, Dict
from .types import IJsonValidator

logger = logging.getLogger(__name__)


class JsonValidator(IJsonValidator):
    """
    Валидатор JSON ответов - проверяет и извлекает JSON из ответов моделей

    Предоставляет:
    - Синтаксическую валидацию JSON
    - Извлечение JSON из текста с markdown или другими обертками
    - Обработку malformed ответов
    - Schema validation (в будущем)
    """

    def __init__(self):
        """Инициализация валидатора"""
        # Паттерны для извлечения JSON из текста
        self.json_patterns = [
            r'```json\s*\n(.*?)\n```',  # ```json ... ```
            r'```\s*\n(\{.*?\})\s*\n```',  # ``` { ... } ```
            r'(\{[^{}]*\{[^{}]*\}[^{}]*\})',  # Вложенные объекты
            r'(\{[^{}]*\})',  # Простые объекты
            r'(\[[^\[\]]*\])',  # Массивы
        ]

    def validate_json(self, content: str) -> bool:
        """
        Проверить валидность JSON

        Args:
            content: Строка для проверки

        Returns:
            True если это валидный JSON
        """
        if not content or not content.strip():
            return False

        try:
            json.loads(content.strip())
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    def extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Извлечь JSON из текста с различными обертками

        Args:
            text: Текст, содержащий JSON

        Returns:
            Извлеченный JSON или None если не найден
        """
        if not text:
            return None

        # Сначала пробуем распарсить весь текст как JSON
        if self.validate_json(text):
            return text.strip()

        # Пробуем различные паттерны извлечения
        for pattern in self.json_patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
            for match in matches:
                candidate = match.strip()
                if self.validate_json(candidate):
                    logger.debug(f"Extracted JSON using pattern: {pattern}")
                    return candidate

        # Если ничего не найдено, пробуем найти JSON-подобные структуры
        # Удаляем лишние символы и пробуем распарсить
        cleaned_text = self._clean_json_text(text)
        if cleaned_text and self.validate_json(cleaned_text):
            return cleaned_text

        logger.warning(f"Could not extract valid JSON from text: {text[:200]}...")
        return None

    def _clean_json_text(self, text: str) -> Optional[str]:
        """
        Очистить текст от лишних символов для извлечения JSON

        Args:
            text: Текст для очистки

        Returns:
            Очищенный текст или None
        """
        if not text:
            return None

        # Удаляем markdown обертки
        text = re.sub(r'```\w*\s*\n?', '', text)
        text = re.sub(r'```\s*$', '', text)

        # Удаляем лишние пробелы и переносы
        text = text.strip()

        # Если текст начинается с {, пробуем найти конец }
        if text.startswith('{'):
            brace_count = 0
            end_pos = 0
            for i, char in enumerate(text):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break

            if end_pos > 0:
                candidate = text[:end_pos]
                if self.validate_json(candidate):
                    return candidate

        # Аналогично для массивов
        elif text.startswith('['):
            bracket_count = 0
            end_pos = 0
            for i, char in enumerate(text):
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_pos = i + 1
                        break

            if end_pos > 0:
                candidate = text[:end_pos]
                if self.validate_json(candidate):
                    return candidate

        return None

    def validate_and_extract(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Проверить и извлечь JSON из контента

        Args:
            content: Контент для проверки

        Returns:
            (is_valid, extracted_json)
        """
        extracted = self.extract_json_from_text(content)
        if extracted:
            return True, extracted
        return False, None

    def fix_malformed_json(self, content: str) -> Optional[str]:
        """
        Попытаться исправить malformed JSON

        Args:
            content: Malformed JSON

        Returns:
            Исправленный JSON или None
        """
        if not content:
            return None

        try:
            # Пробуем добавить отсутствующие закрывающие скобки
            content = content.strip()

            # Считаем скобки
            open_braces = content.count('{')
            close_braces = content.count('}')
            open_brackets = content.count('[')
            close_brackets = content.count(']')

            # Добавляем недостающие закрывающие скобки
            while open_braces > close_braces:
                content += '}'
                close_braces += 1

            while open_brackets > close_brackets:
                content += ']'
                close_brackets += 1

            # Проверяем исправленный JSON
            if self.validate_json(content):
                logger.debug("Fixed malformed JSON by adding closing brackets")
                return content

        except Exception as e:
            logger.debug(f"Could not fix malformed JSON: {e}")

        return None