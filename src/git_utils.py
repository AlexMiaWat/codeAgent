"""
Утилиты для работы с Git

Предоставляет функции для выполнения git команд напрямую из сервера,
без использования Cursor CLI.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Исключение для ошибок Git"""
    pass


def execute_git_command(
    command: List[str],
    working_dir: Optional[Path] = None,
    timeout: int = 30
) -> Tuple[bool, str, str]:
    """
    Выполнить git команду
    
    Args:
        command: Список аргументов команды (первый элемент - 'git')
        working_dir: Рабочая директория (если None - текущая)
        timeout: Таймаут выполнения (секунды)
    
    Returns:
        Кортеж (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command,
            cwd=str(working_dir) if working_dir else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        
        success = result.returncode == 0
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""
        
        return success, stdout, stderr
        
    except subprocess.TimeoutExpired:
        logger.error(f"Таймаут выполнения git команды: {' '.join(command)}")
        return False, "", f"Таймаут выполнения команды ({timeout} секунд)"
    except Exception as e:
        logger.error(f"Ошибка выполнения git команды: {e}")
        return False, "", str(e)


def get_current_branch(working_dir: Optional[Path] = None) -> Optional[str]:
    """
    Получить текущую ветку

    Args:
        working_dir: Рабочая директория

    Returns:
        Название текущей ветки или None при ошибке
    """
    success, stdout, stderr = execute_git_command(
        ["git", "branch", "--show-current"],
        working_dir=working_dir
    )

    if success and stdout:
        return stdout.strip()
    else:
        logger.warning(f"Не удалось получить текущую ветку: {stderr}")
        return None


def is_branch_allowed_for_auto_push(
    branch: Optional[str] = None,
    allowed_branches: Optional[List[str]] = None,
    working_dir: Optional[Path] = None
) -> bool:
    """
    Проверить, разрешена ли автоматическая отправка для текущей ветки

    Args:
        branch: Название ветки (если None - получить текущую)
        allowed_branches: Список разрешенных веток (если None - только 'smart')
        working_dir: Рабочая директория

    Returns:
        True если push разрешен для данной ветки
    """
    if not branch:
        branch = get_current_branch(working_dir)
        if not branch:
            logger.warning("Не удалось определить текущую ветку для проверки разрешений")
            return False

    # По умолчанию разрешена только ветка 'smart'
    if allowed_branches is None:
        allowed_branches = ["smart"]

    is_allowed = branch in allowed_branches

    if is_allowed:
        logger.debug(f"Автоматический push разрешен для ветки '{branch}'")
    else:
        logger.debug(f"Автоматический push запрещен для ветки '{branch}' (разрешены: {allowed_branches})")

    return is_allowed


def get_last_commit_info(working_dir: Optional[Path] = None) -> Optional[Dict[str, str]]:
    """
    Получить информацию о последнем коммите
    
    Args:
        working_dir: Рабочая директория
    
    Returns:
        Словарь с информацией о коммите или None при ошибке
    """
    # Получаем полный hash
    success_full, hash_full, _ = execute_git_command(
        ["git", "log", "-1", "--format=%H"],
        working_dir=working_dir
    )
    
    # Получаем короткий hash
    success_short, hash_short, _ = execute_git_command(
        ["git", "log", "-1", "--format=%h"],
        working_dir=working_dir
    )
    
    # Получаем сообщение коммита
    success_msg, commit_msg, _ = execute_git_command(
        ["git", "log", "-1", "--format=%s"],
        working_dir=working_dir
    )
    
    if success_full and success_short and success_msg:
        return {
            "hash_full": hash_full.strip(),
            "hash_short": hash_short.strip(),
            "message": commit_msg.strip()
        }
    else:
        logger.warning("Не удалось получить информацию о последнем коммите")
        return None


def check_commit_exists(commit_hash: str, working_dir: Optional[Path] = None) -> bool:
    """
    Проверить существование коммита
    
    Args:
        commit_hash: Hash коммита (полный или короткий)
        working_dir: Рабочая директория
    
    Returns:
        True если коммит существует
    """
    success, stdout, _ = execute_git_command(
        ["git", "cat-file", "-e", commit_hash],
        working_dir=working_dir
    )
    
    return success


def check_uncommitted_changes(working_dir: Optional[Path] = None) -> bool:
    """
    Проверить наличие незакоммиченных изменений
    
    Args:
        working_dir: Рабочая директория
    
    Returns:
        True если есть незакоммиченные изменения
    """
    success, stdout, _ = execute_git_command(
        ["git", "status", "--short"],
        working_dir=working_dir
    )
    
    if success:
        return bool(stdout.strip())
    else:
        logger.warning("Не удалось проверить статус git")
        return False


def check_unpushed_commits(working_dir: Optional[Path] = None, branch: Optional[str] = None) -> bool:
    """
    Проверить наличие неотправленных коммитов
    
    Args:
        working_dir: Рабочая директория
        branch: Название ветки (если None - текущая)
    
    Returns:
        True если есть неотправленные коммиты
    """
    if not branch:
        branch = get_current_branch(working_dir)
        if not branch:
            logger.warning("Не удалось определить текущую ветку для проверки неотправленных коммитов")
            return False
    
    # Проверяем разницу между локальной и удаленной веткой
    success, stdout, _ = execute_git_command(
        ["git", "log", f"origin/{branch}..{branch}", "--oneline"],
        working_dir=working_dir
    )
    
    if success:
        return bool(stdout.strip())
    else:
        # Если удаленная ветка не существует, считаем что есть неотправленные коммиты
        logger.debug(f"Не удалось сравнить с origin/{branch}, возможно ветка не существует на remote")
        return True


def push_to_remote(
    branch: Optional[str] = None,
    remote: str = "origin",
    working_dir: Optional[Path] = None,
    timeout: int = 60
) -> Tuple[bool, str, str]:
    """
    Отправить коммиты в удаленный репозиторий
    
    Args:
        branch: Название ветки (если None - текущая)
        remote: Название remote (по умолчанию 'origin')
        working_dir: Рабочая директория
        timeout: Таймаут выполнения (секунды)
    
    Returns:
        Кортеж (success, stdout, stderr)
    """
    if not branch:
        branch = get_current_branch(working_dir)
        if not branch:
            return False, "", "Не удалось определить текущую ветку"
    
    logger.info(f"Отправка коммитов в {remote}/{branch}")
    
    success, stdout, stderr = execute_git_command(
        ["git", "push", remote, branch],
        working_dir=working_dir,
        timeout=timeout
    )
    
    if success:
        logger.info(f"Коммиты успешно отправлены в {remote}/{branch}")
    else:
        logger.warning(f"Не удалось отправить коммиты в {remote}/{branch}: {stderr}")
    
    return success, stdout, stderr


def auto_push_after_commit(
    working_dir: Optional[Path] = None,
    remote: str = "origin",
    timeout: int = 60,
    allowed_branches: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Автоматически отправить коммиты после успешного коммита

    Проверяет:
    1. Разрешение push для текущей ветки
    2. Существование последнего коммита
    3. Наличие неотправленных коммитов
    4. Выполняет push

    Args:
        working_dir: Рабочая директория
        remote: Название remote
        timeout: Таймаут выполнения push
        allowed_branches: Список разрешенных веток для push (если None - только 'smart')

    Returns:
        Словарь с результатом операции
    """
    result: Dict[str, Any] = {
        "success": False,
        "branch": None,
        "commit_info": None,
        "push_success": False,
        "push_stdout": "",
        "push_stderr": "",
        "error": None
    }
    
    try:
        # Получаем текущую ветку
        branch = get_current_branch(working_dir)
        if not branch:
            result["error"] = "Не удалось определить текущую ветку"
            return result
        
        result["branch"] = branch

        # Проверяем разрешение для автоматического push в данной ветке
        if not is_branch_allowed_for_auto_push(branch, allowed_branches, working_dir):
            logger.info(f"Автоматический push пропущен: ветка '{branch}' не разрешена для авто-push")
            result["error"] = f"Автоматический push не разрешен для ветки '{branch}'"
            result["push_allowed"] = False
            return result

        result["push_allowed"] = True

        # Получаем информацию о последнем коммите
        commit_info = get_last_commit_info(working_dir)
        if not commit_info:
            result["error"] = "Не удалось получить информацию о последнем коммите (возможно, коммит не был создан)"
            return result
        
        result["commit_info"] = commit_info
        
        # Проверяем существование коммита
        if not check_commit_exists(commit_info["hash_full"], working_dir):
            result["error"] = f"Коммит {commit_info['hash_full']} не существует"
            return result
        
        # Проверяем наличие неотправленных коммитов
        has_unpushed = check_unpushed_commits(working_dir, branch)
        if not has_unpushed:
            logger.info(f"Нет неотправленных коммитов в ветке {branch}")
            result["success"] = True
            result["push_success"] = True
            result["push_stdout"] = "Нет неотправленных коммитов"
            return result
        
        # Выполняем push
        push_success, push_stdout, push_stderr = push_to_remote(
            branch=branch,
            remote=remote,
            working_dir=working_dir,
            timeout=timeout
        )
        
        result["push_success"] = push_success
        result["push_stdout"] = push_stdout
        result["push_stderr"] = push_stderr
        
        if push_success:
            result["success"] = True
            logger.info(f"Автоматический push выполнен успешно: {branch} -> {remote}/{branch}")
        else:
            result["error"] = f"Push не удался: {push_stderr}"
            logger.warning(f"Автоматический push не удался: {push_stderr}")
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при автоматическом push: {e}", exc_info=True)
        result["error"] = str(e)
        return result
