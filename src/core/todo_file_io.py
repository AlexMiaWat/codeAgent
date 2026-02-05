from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import yaml
import os

from .todo_item import TodoItem
from .types import TaskType
from src.utils.logging_utils import logger

class ITodoFileParser(ABC):
    """Interface for parsing todo file content into a list of TodoItem."""

    @abstractmethod
    def parse(self, content: str) -> List[TodoItem]:
        pass

class ITodoFileSerializer(ABC):
    """Interface for serializing a list of TodoItem into file content."""

    @abstractmethod
    def serialize(self, items: List[TodoItem]) -> str:
        pass

class TextTodoParser(ITodoFileParser):
    """Parses todo items from plain text content."""

    def parse(self, content: str) -> List[TodoItem]:
        items = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Определяем уровень вложенности по отступам
            level = len(line) - len(line.lstrip())
            level = level // 2  # Предполагаем отступ в 2 пробела

            # Убираем номера и маркеры списка
            text = re.sub(r'^\d+[.)]\s*', '', line)
            text = re.sub(r'^[-*+]\s+', '', text)
            
            done = False
            # Check for [x] or [ ]
            checkbox_match = re.match(r'^\[([ xX])\]\s*(.+)', text)
            if checkbox_match:
                done = checkbox_match.group(1).lower() == 'x'
                text = checkbox_match.group(2).strip()

            # Парсим комментарий (формат: текст  # комментарий)
            comment = None
            if '  # ' in text or ' # ' in text:
                parts = re.split(r'\s+#\s+', text, 1)
                if len(parts) == 2:
                    text = parts[0].strip()
                    comment = parts[1].strip()

            text = text.strip()

            if text:
                items.append(TodoItem(text, level=level, done=done, comment=comment))
        
        return items

class TextTodoSerializer(ITodoFileSerializer):
    """Serializes todo items to plain text content."""

    def serialize(self, items: List[TodoItem]) -> str:
        lines = []
        for item in items:
            indent = "  " * item.level
            status = "[x]" if item.done else "[ ]"
            if item.comment:
                lines.append(f"{indent}{status} {item.text}  # {item.comment}")
            else:
                lines.append(f"{indent}{status} {item.text}")
        
        content = "\n".join(lines)
        if lines:
            content += "\n"
        return content

class MarkdownTodoParser(ITodoFileParser):
    """Parses todo items from Markdown content."""

    def parse(self, content: str) -> List[TodoItem]:
        items = []
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            checkbox_match = re.match(r'^(\s*)- \[([ xX])\]\s*(.+?)(?:\s*<!--\s*(.+?)\s*-->)?\s*$', line)
            if checkbox_match:
                indent = len(checkbox_match.group(1))
                checked = checkbox_match.group(2).lower() == 'x'
                text = checkbox_match.group(3).strip()
                comment = checkbox_match.group(4) if checkbox_match.group(4) else None
                
                level = indent // 2
                items.append(TodoItem(text, level=level, done=checked, comment=comment))
            elif re.match(r'^\s*[-*+]\s+', line):
                level = (len(line) - len(line.lstrip())) // 2
                text_match = re.match(r'^\s*[-*+]\s+(.+?)(?:\s*<!--\s*(.+?)\s*-->)?$', line)
                if text_match:
                    text = text_match.group(1).strip()
                    comment = text_match.group(2) if text_match.group(2) else None
                    if text:
                        items.append(TodoItem(text, level=level, comment=comment))
        
        return items

class MarkdownTodoSerializer(ITodoFileSerializer):
    """Serializes todo items to Markdown content."""

    def serialize(self, items: List[TodoItem]) -> str:
        lines = []
        for item in items:
            indent = "  " * item.level
            checkbox = "[x]" if item.done else "[ ]"
            if item.comment:
                lines.append(f"{indent}- {checkbox} {item.text} <!-- {item.comment} -->")
            else:
                lines.append(f"{indent}- {checkbox} {item.text}")
        
        content = "\n".join(lines)
        if lines:
            content += "\n"
        return content

class YamlTodoParser(ITodoFileParser):
    """Parses todo items from YAML content."""

    def parse(self, content: str) -> List[TodoItem]:
        try:
            data = yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML content: {e}", exc_info=True)
            return []
        
        items = []
        def parse_items(items_data: List[Any], level: int = 0) -> None:
            for item_data in items_data:
                if isinstance(item_data, dict):
                    text = item_data.get('text', item_data.get('task', ''))
                    done = item_data.get('done', False)
                    comment = item_data.get('comment', None)
                    items.append(TodoItem(text, level=level, done=done, comment=comment))
                    
                    if 'children' in item_data:
                        parse_items(item_data['children'], level + 1)
                elif isinstance(item_data, str):
                    items.append(TodoItem(item_data, level=level))
        
        if 'tasks' in data:
            parse_items(data['tasks'])
        elif 'todo' in data:
            parse_items(data['todo'])
        elif isinstance(data, list):
            parse_items(data)
        
        return items

class YamlTodoSerializer(ITodoFileSerializer):
    """Serializes todo items to YAML content."""

    def serialize(self, items: List[TodoItem]) -> str:
        tasks = []
        for item in items:
            task_data = {
                "text": item.text,
                "done": item.done
            }
            if item.level > 0:
                task_data["level"] = item.level
            if item.comment:
                task_data["comment"] = item.comment
            tasks.append(task_data)
        
        data = {"tasks": tasks}
        content = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return content
