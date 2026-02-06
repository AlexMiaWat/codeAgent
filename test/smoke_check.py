#!/usr/bin/env python3
"""
Smoke check для Code Agent.
Проверяет базовую работоспособность проекта: импорты, конфигурация, запуск сервера в тестовом режиме.
Запуск: python smoke_check.py
"""
import sys
import os
import importlib
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_imports():
    """Проверяем импорты основных модулей."""
    modules = [
        'src.config_loader',
        'src.todo_manager',
        'src.status_manager',
        'src.cursor_cli_interface',
        'src.llm.llm_manager',
        'src.git_utils',
        'src.server',
    ]
    for module in modules:
        try:
            importlib.import_module(module)
            logger.info(f"✅ Импорт {module} успешен")
        except ImportError as e:
            logger.error(f"❌ Ошибка импорта {module}: {e}")
            return False
    return True

def check_config():
    """Проверяем наличие и читаемость основных конфигурационных файлов."""
    config_files = [
        Path('config/config.yaml'),
        Path('config/llm_settings.yaml'),
        Path('.env.example'),
    ]
    for cf in config_files:
        if cf.exists():
            logger.info(f"✅ Конфигурационный файл {cf} существует")
            # Попробуем прочитать YAML, если это yaml
            if cf.suffix in ('.yaml', '.yml'):
                try:
                    import yaml
                    with open(cf, 'r', encoding='utf-8') as f:
                        yaml.safe_load(f)
                    logger.info(f"✅ Файл {cf} валиден YAML")
                except Exception as e:
                    logger.warning(f"⚠️  Файл {cf} не может быть прочитан как YAML: {e}")
        else:
            logger.warning(f"⚠️  Конфигурационный файл {cf} отсутствует (возможно, ожидается)")
    # Проверяем, что config.yaml содержит обязательные поля
    config_path = Path('config/config.yaml')
    if config_path.exists():
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            if config and 'project' in config:
                logger.info("✅ config.yaml содержит секцию 'project'")
            else:
                logger.warning("⚠️  config.yaml не содержит секцию 'project'")
        except Exception as e:
            logger.error(f"❌ Ошибка чтения config.yaml: {e}")
            return False
    return True

def check_server_start():
    """Пробуем запустить сервер в тестовом режиме (без фактического старта HTTP)."""
    # Импортируем сервер и проверяем, что классы могут быть созданы
    try:
        from src.server import ServerReloadException, SecurityError, CodeAgentServer
        logger.info("✅ Классы исключений сервера импортируются")
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта классов сервера: {e}")
        return False
    
    # Проверяем, что логгер инициализирован (не будет NameError)
    try:
        from src.server import logger as server_logger
        logger.info("✅ Логгер сервера доступен")
    except NameError as e:
        logger.error(f"❌ NameError в server.py: {e}")
        return False
    
    # Проверяем, что Flask доступен (если нет, сервер может работать в урезанном режиме)
    try:
        from flask import Flask
        logger.info("✅ Flask доступен")
    except ImportError:
        logger.warning("⚠️  Flask недоступен, HTTP сервер может не работать")
    
    # Проверяем, что Gemini импорт не ломает всё
    try:
        from src.agents.gemini_agent.gemini_cli_interface import create_gemini_cli_interface
        logger.info("✅ Gemini интерфейс доступен")
    except ImportError:
        logger.warning("⚠️  Gemini интерфейс недоступен (ожидается в средах без Gemini)")
    
    # Пытаемся создать экземпляр сервера (без запуска)
    try:
        # Инициализация сервера с минимальными параметрами
        # Временный перехват вывода логов, чтобы не засорять консоль
        import io
        import contextlib
        from unittest.mock import patch
        
        # Создаем временный поток для логов
        log_capture = io.StringIO()
        with contextlib.redirect_stderr(log_capture), \
             contextlib.redirect_stdout(log_capture), \
             patch('sys.argv', ['smoke_check.py']):  # мокаем аргументы командной строки
            server = CodeAgentServer()
            logger.info("✅ Экземпляр сервера создан успешно")
            
            # Проверяем наличие основных атрибутов
            required_attrs = ['config', 'status_manager', 'todo_manager', 'checkpoint_manager']
            for attr in required_attrs:
                if hasattr(server, attr):
                    logger.info(f"✅ Сервер имеет атрибут {attr}")
                else:
                    logger.warning(f"⚠️  Сервер не имеет атрибута {attr}")
            
            # Пробуем вызвать метод инициализации (если есть)
            if hasattr(server, 'initialize'):
                try:
                    server.initialize()
                    logger.info("✅ Инициализация сервера выполнена")
                except Exception as e:
                    logger.warning(f"⚠️  Инициализация сервера вызвала исключение (возможно ожидается): {e}")
                    
    except Exception as e:
        logger.error(f"❌ Ошибка при создании экземпляра сервера: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False
    
    return True

def main():
    logger.info("🚀 Запуск smoke check для Code Agent")
    success = True
    
    # 1. Импорты
    logger.info("--- Проверка импортов ---")
    if not check_imports():
        success = False
    
    # 2. Конфигурация
    logger.info("--- Проверка конфигурации ---")
    if not check_config():
        success = False
    
    # 3. Сервер
    logger.info("--- Проверка сервера ---")
    if not check_server_start():
        success = False
    
    # Итог
    logger.info("--- Итог ---")
    if success:
        logger.info("✅ Smoke check пройден успешно. Проект готов к работе.")
        sys.exit(0)
    else:
        logger.error("❌ Smoke check выявил проблемы. Требуется исправление.")
        sys.exit(1)

if __name__ == '__main__':
    main()