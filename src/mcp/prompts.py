"""
Prompts Manager для MCP сервера.

Предоставляет промпты (prompts) для MCP протокола.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import ConfigLoader


@dataclass
class MCPPrompt:
    """MCP промпт."""
    name: str
    description: str
    arguments: Optional[List[Dict[str, Any]]] = None


@dataclass
class PromptResult:
    """Результат получения промпта."""
    description: str
    messages: List[Dict[str, Any]]


class PromptsManager:
    """
    Менеджер промптов для MCP сервера.

    Предоставляет готовые промпты для различных задач.
    """

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader
        self.logger = logging.getLogger(__name__)
        self.prompts: Dict[str, MCPPrompt] = {}
        self.prompt_templates: Dict[str, Dict[str, Any]] = {}

        self._initialize_prompts()

    def _initialize_prompts(self):
        """Инициализация доступных промптов."""
        # Промпт для анализа кода
        self.prompts["code_analysis"] = MCPPrompt(
            name="code_analysis",
            description="Анализ кода на наличие ошибок и улучшений",
            arguments=[
                {
                    "name": "code",
                    "description": "Код для анализа",
                    "required": True
                },
                {
                    "name": "language",
                    "description": "Язык программирования",
                    "required": False
                }
            ]
        )

        self.prompt_templates["code_analysis"] = {
            "description": "Анализ предоставленного кода",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": """Проанализируйте следующий код на наличие ошибок, проблем безопасности и возможностей улучшения:

Код:
{{code}}

{{#if language}}
Язык: {{language}}
{{/if}}

Пожалуйста, предоставьте:
1. Выявленные ошибки и проблемы
2. Рекомендации по улучшению
3. Оценку качества кода
4. Предложения по рефакторингу"""
                    }
                }
            ]
        }

        # Промпт для генерации тестов
        self.prompts["generate_tests"] = MCPPrompt(
            name="generate_tests",
            description="Генерация unit тестов для кода",
            arguments=[
                {
                    "name": "code",
                    "description": "Код для которого нужно сгенерировать тесты",
                    "required": True
                },
                {
                    "name": "language",
                    "description": "Язык программирования",
                    "required": False
                },
                {
                    "name": "framework",
                    "description": "Тестовый фреймворк (pytest, unittest, etc.)",
                    "required": False
                }
            ]
        )

        self.prompt_templates["generate_tests"] = {
            "description": "Генерация unit тестов",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": """Сгенерируйте unit тесты для следующего кода:

Код:
{{code}}

{{#if language}}
Язык: {{language}}
{{/if}}

{{#if framework}}
Тестовый фреймворк: {{framework}}
{{/if}}

Требования:
1. Покрыть основные функции и методы
2. Включить тесты для нормальных и граничных случаев
3. Добавить проверки на исключения
4. Обеспечить хорошее покрытие кода"""
                    }
                }
            ]
        }

        # Промпт для документирования
        self.prompts["generate_docs"] = MCPPrompt(
            name="generate_docs",
            description="Генерация документации для кода",
            arguments=[
                {
                    "name": "code",
                    "description": "Код для документирования",
                    "required": True
                },
                {
                    "name": "language",
                    "description": "Язык программирования",
                    "required": False
                },
                {
                    "name": "doc_format",
                    "description": "Формат документации (markdown, rst, etc.)",
                    "required": False
                }
            ]
        )

        self.prompt_templates["generate_docs"] = {
            "description": "Генерация документации",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": """Создайте подробную документацию для следующего кода:

Код:
{{code}}

{{#if language}}
Язык: {{language}}
{{/if}}

{{#if doc_format}}
Формат документации: {{doc_format}}
{{/if}}

Документация должна включать:
1. Описание назначения кода
2. API документацию для всех публичных функций/классов
3. Примеры использования
4. Зависимости и требования
5. Инструкции по установке и запуску"""
                    }
                }
            ]
        }

        # Промпт для отладки
        self.prompts["debug_help"] = MCPPrompt(
            name="debug_help",
            description="Помощь в отладке кода и решении проблем",
            arguments=[
                {
                    "name": "error_message",
                    "description": "Сообщение об ошибке",
                    "required": True
                },
                {
                    "name": "code_context",
                    "description": "Код и контекст где произошла ошибка",
                    "required": False
                },
                {
                    "name": "language",
                    "description": "Язык программирования",
                    "required": False
                }
            ]
        )

        self.prompt_templates["debug_help"] = {
            "description": "Помощь в отладке",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": """Помогите разобраться с следующей ошибкой:

Ошибка:
{{error_message}}

{{#if code_context}}
Контекст кода:
{{code_context}}
{{/if}}

{{#if language}}
Язык: {{language}}
{{/if}}

Пожалуйста, предоставьте:
1. Анализ причины ошибки
2. Возможные решения
3. Советы по предотвращению подобных ошибок
4. Рекомендации по улучшению кода"""
                    }
                }
            ]
        }

        self.logger.info(f"Initialized {len(self.prompts)} prompts")

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """
        Получить список всех доступных промптов.

        Returns:
            Список промптов в формате MCP
        """
        prompts_list = []
        for prompt in self.prompts.values():
            prompt_dict = {
                "name": prompt.name,
                "description": prompt.description
            }
            if prompt.arguments:
                prompt_dict["arguments"] = prompt.arguments
            prompts_list.append(prompt_dict)

        return prompts_list

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[PromptResult]:
        """
        Получить промпт по имени.

        Args:
            name: Имя промпта
            arguments: Аргументы для промпта

        Returns:
            Результат с промптом или None
        """
        if name not in self.prompt_templates:
            return None

        template = self.prompt_templates[name]
        args = arguments or {}

        try:
            # Простая шаблонизация (в продакшене использовать Jinja2)
            description = template["description"]
            messages = []

            for msg_template in template["messages"]:
                content = msg_template["content"]
                if isinstance(content, dict) and content.get("type") == "text":
                    text = content["text"]
                    # Замена плейсхолдеров
                    for key, value in args.items():
                        placeholder = "{{" + key + "}}"
                        text = text.replace(placeholder, str(value))

                        # Условные блоки (простая реализация)
                        if_key = "{{#if " + key + "}}"
                        end_if = "{{/if}}"
                        if value:
                            # Удаляем условные блоки, оставляем содержимое
                            while if_key in text and end_if in text:
                                start = text.find(if_key)
                                end = text.find(end_if, start) + len(end_if)
                                before = text[:start]
                                inside = text[start + len(if_key):end - len(end_if)]
                                after = text[end:]
                                text = before + inside + after
                        else:
                            # Удаляем условные блоки полностью
                            while if_key in text and end_if in text:
                                start = text.find(if_key)
                                end = text.find(end_if, start) + len(end_if)
                                before = text[:start]
                                after = text[end:]
                                text = before + after

                    content["text"] = text

                messages.append({
                    "role": msg_template["role"],
                    "content": content
                })

            return PromptResult(
                description=description,
                messages=messages
            )

        except Exception as e:
            self.logger.error(f"Error processing prompt template {name}: {e}")
            return None