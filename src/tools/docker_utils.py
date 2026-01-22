"""
Docker Utils - простая проверка доступности Docker
Упрощено: убрана избыточная абстракция, оставлена только базовая проверка
"""

import subprocess
import logging

logger = logging.getLogger(__name__)


def is_docker_available() -> bool:
    """
    Проверяет доступность Docker

    Returns:
        bool: True если Docker доступен, False в противном случае
    """
    try:
        # Проверяем, что команда docker доступна и daemon работает
        result = subprocess.run(
            ['docker', 'info'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0

    except Exception:
        return False