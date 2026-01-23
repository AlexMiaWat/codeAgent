"""
Реализации репортёров результатов качества
"""

from .console_reporter import ConsoleReporter
from .file_reporter import FileReporter

__all__ = [
    'ConsoleReporter',
    'FileReporter'
]