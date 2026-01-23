#!/usr/bin/env python3
"""
Скрипт для проверки ссылок в документации

Проверяет существование файлов, на которые ссылаются markdown документы.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Корень проекта
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


def find_markdown_links(content: str, file_path: Path) -> List[Tuple[str, str]]:
    """
    Находит все markdown ссылки в содержимом файла
    
    Returns:
        Список кортежей (текст ссылки, путь)
    """
    links = []
    
    # Паттерн для markdown ссылок: [текст](путь)
    pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    
    for match in re.finditer(pattern, content):
        link_text = match.group(1)
        link_path = match.group(2)
        
        # Пропускаем внешние ссылки (http/https)
        if link_path.startswith('http://') or link_path.startswith('https://'):
            continue
        
        # Пропускаем якоря (#)
        if link_path.startswith('#'):
            continue
        
        links.append((link_text, link_path))
    
    return links


def resolve_link_path(link_path: str, base_file: Path) -> Path:
    """
    Разрешает путь ссылки относительно базового файла
    
    Args:
        link_path: Путь из ссылки
        base_file: Файл, в котором находится ссылка
    
    Returns:
        Абсолютный путь к файлу
    """
    # Убираем якоря и параметры
    clean_path = link_path.split('#')[0].split('?')[0]
    
    # Если путь абсолютный от корня проекта
    if clean_path.startswith('/'):
        return PROJECT_ROOT / clean_path.lstrip('/')
    
    # Относительный путь
    base_dir = base_file.parent
    # Правильная нормализация относительного пути с .. компонентами
    combined = base_dir / clean_path
    parts = list(combined.parts)
    normalized = []

    for part in parts:
        if part == '..':
            if normalized:
                normalized.pop()  # Убираем предыдущий компонент
        elif part != '.':
            normalized.append(part)

    normalized_path = Path(*normalized)
    resolved = (PROJECT_ROOT / normalized_path).resolve()

    return resolved


def check_documentation_links() -> Tuple[int, int]:
    """
    Проверяет все ссылки в документации
    
    Returns:
        Кортеж (количество проверенных ссылок, количество ошибок)
    """
    total_links = 0
    broken_links = 0
    broken_files = []
    
    # Находим все markdown файлы
    md_files = list(DOCS_DIR.rglob('*.md'))
    
    print(f"Проверка ссылок в {len(md_files)} файлах документации...\n")
    
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding='utf-8')
            links = find_markdown_links(content, md_file)
            
            for link_text, link_path in links:
                total_links += 1
                resolved_path = resolve_link_path(link_path, md_file)
                
                if not resolved_path.exists():
                    broken_links += 1
                    broken_files.append({
                        'file': str(md_file.relative_to(PROJECT_ROOT)),
                        'link_text': link_text,
                        'link_path': link_path,
                        'resolved_path': str(resolved_path.relative_to(PROJECT_ROOT))
                    })
                    print(f"❌ {md_file.relative_to(PROJECT_ROOT)}")
                    print(f"   Ссылка: [{link_text}]({link_path})")
                    print(f"   Ожидаемый путь: {resolved_path.relative_to(PROJECT_ROOT)}")
                    print()
        
        except Exception as e:
            print(f"⚠️  Ошибка при обработке {md_file}: {e}")
    
    # Итоговая статистика
    print("=" * 70)
    print(f"Проверено ссылок: {total_links}")
    print(f"Сломанных ссылок: {broken_links}")
    print(f"Процент успешных: {((total_links - broken_links) / total_links * 100) if total_links > 0 else 0:.1f}%")
    print("=" * 70)
    
    if broken_links > 0:
        print("\n📋 Список сломанных ссылок:")
        for item in broken_files[:20]:  # Показываем первые 20
            print(f"  - {item['file']}: [{item['link_text']}]({item['link_path']})")
        if len(broken_files) > 20:
            print(f"  ... и еще {len(broken_files) - 20} ссылок")
    
    return total_links, broken_links


if __name__ == "__main__":
    total, broken = check_documentation_links()
    sys.exit(1 if broken > 0 else 0)
