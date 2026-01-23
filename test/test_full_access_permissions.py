"""
Тест проверки полного доступа Cursor CLI без запросов разрешений

Проверяет:
1. Наличие конфигурационных файлов
2. Корректность настроек разрешений
3. Наличие флагов --force и --approve-mcps в командах
4. Работу Cursor CLI с полным доступом
"""

import json
import pytest
from pathlib import Path
import sys

# Добавляем путь к src для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cursor_cli_interface import CursorCLIInterface, create_cursor_cli_interface
import yaml


class TestFullAccessPermissions:
    """Тесты проверки полного доступа"""
    
    @pytest.fixture
    def project_root(self):
        """Корневая директория проекта"""
        return Path(__file__).parent.parent
    
    @pytest.fixture
    def cursor_config_dir(self, project_root):
        """Директория .cursor"""
        return project_root / ".cursor"
    
    def test_cursor_config_directory_exists(self, cursor_config_dir):
        """Проверка существования директории .cursor"""
        assert cursor_config_dir.exists(), ".cursor директория не найдена"
        assert cursor_config_dir.is_dir(), ".cursor не является директорией"
        print(f"[OK] Директория .cursor существует: {cursor_config_dir}")
    
    def test_cli_config_file_exists(self, cursor_config_dir):
        """Проверка существования cli-config.json"""
        cli_config_file = cursor_config_dir / "cli-config.json"
        assert cli_config_file.exists(), "cli-config.json не найден"
        print(f"[OK] Файл cli-config.json существует: {cli_config_file}")
    
    def test_mcp_approvals_file_exists(self, cursor_config_dir):
        """Проверка существования mcp-approvals.json"""
        mcp_approvals_file = cursor_config_dir / "mcp-approvals.json"
        assert mcp_approvals_file.exists(), "mcp-approvals.json не найден"
        print(f"[OK] Файл mcp-approvals.json существует: {mcp_approvals_file}")
    
    def test_cli_config_structure(self, cursor_config_dir):
        """Проверка структуры cli-config.json"""
        cli_config_file = cursor_config_dir / "cli-config.json"
        
        with open(cli_config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Проверка основных полей
        assert "version" in config, "Отсутствует поле version"
        assert "permissions" in config, "Отсутствует поле permissions"
        assert "allow" in config["permissions"], "Отсутствует поле permissions.allow"
        assert "deny" in config["permissions"], "Отсутствует поле permissions.deny"
        
        # Проверка наличия разрешений
        allow_list = config["permissions"]["allow"]
        assert len(allow_list) > 0, "Список allow пустой"
        
        # Проверка наличия запретов для безопасности
        deny_list = config["permissions"]["deny"]
        assert len(deny_list) > 0, "Список deny пустой (небезопасно!)"
        
        print("[OK] Структура cli-config.json корректна")
        print(f"   - Разрешено операций: {len(allow_list)}")
        print(f"   - Запрещено операций: {len(deny_list)}")
    
    def test_cli_config_permissions(self, cursor_config_dir):
        """Проверка наличия необходимых разрешений"""
        cli_config_file = cursor_config_dir / "cli-config.json"
        
        with open(cli_config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        allow_list = config["permissions"]["allow"]
        
        # Проверка необходимых разрешений
        required_permissions = [
            "Shell(git)",
            "Shell(python)",
            "Shell(pytest)",
            "Read(src/**)",
            "Write(src/**)",
            "Read(docs/**)",
            "Write(docs/**)",
        ]
        
        for perm in required_permissions:
            assert perm in allow_list, f"Отсутствует необходимое разрешение: {perm}"
        
        print("[OK] Все необходимые разрешения присутствуют")
    
    def test_cli_config_security_denials(self, cursor_config_dir):
        """Проверка наличия запретов для безопасности"""
        cli_config_file = cursor_config_dir / "cli-config.json"
        
        with open(cli_config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        deny_list = config["permissions"]["deny"]
        
        # Проверка критичных запретов
        critical_denials = [
            "Write(**/*.env)",
            "Write(**/.env*)",
            "Write(**/credentials*)",
            "Shell(rm -rf /)",
        ]
        
        for denial in critical_denials:
            assert denial in deny_list, f"Отсутствует критичный запрет: {denial}"
        
        print("[OK] Все критичные запреты присутствуют")
    
    def test_mcp_approvals_structure(self, cursor_config_dir):
        """Проверка структуры mcp-approvals.json"""
        mcp_approvals_file = cursor_config_dir / "mcp-approvals.json"
        
        with open(mcp_approvals_file, 'r', encoding='utf-8') as f:
            approvals = json.load(f)
        
        # Проверка основных полей
        assert "approvals" in approvals, "Отсутствует поле approvals"
        
        # Проверка наличия одобрений
        approvals_dict = approvals["approvals"]
        assert len(approvals_dict) > 0, "Список одобрений пустой"
        
        # Проверка структуры каждого одобрения
        for server_name, approval_data in approvals_dict.items():
            assert "approved" in approval_data, f"Отсутствует поле approved для {server_name}"
            assert approval_data["approved"] is True, f"Сервер {server_name} не одобрен"
            assert "timestamp" in approval_data, f"Отсутствует timestamp для {server_name}"
        
        print("[OK] Структура mcp-approvals.json корректна")
        print(f"   - Одобрено серверов: {len(approvals_dict)}")
    
    def test_config_yaml_permissions_settings(self, project_root):
        """Проверка настроек разрешений в config.yaml"""
        config_file = project_root / "config" / "config.yaml"
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Проверка наличия настроек CLI
        assert "cursor" in config, "Отсутствует секция cursor в config.yaml"
        assert "cli" in config["cursor"], "Отсутствует секция cursor.cli в config.yaml"
        
        cli_config = config["cursor"]["cli"]
        
        # Проверка флагов автоматизации
        assert cli_config.get("auto_approve") is True, "auto_approve не установлен в True"
        assert cli_config.get("force_mode") is True, "force_mode не установлен в True"
        assert cli_config.get("approve_mcps") is True, "approve_mcps не установлен в True"
        
        print("[OK] Настройки автоматизации в config.yaml корректны")
    
    def test_cursor_cli_interface_flags(self):
        """Проверка наличия флагов --force и --approve-mcps в интерфейсе"""
        # Читаем исходный код cursor_cli_interface.py
        interface_file = Path(__file__).parent.parent / "src" / "cursor_cli_interface.py"
        
        with open(interface_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверка наличия флагов в коде
        assert "--force" in content, "Флаг --force не найден в cursor_cli_interface.py"
        assert "--approve-mcps" in content, "Флаг --approve-mcps не найден в cursor_cli_interface.py"
        
        # Проверка наличия в разных местах (Docker, WSL, локальный)
        assert content.count("--force") >= 3, "Флаг --force должен быть в нескольких местах"
        assert content.count("--approve-mcps") >= 3, "Флаг --approve-mcps должен быть в нескольких местах"
        
        print("[OK] Флаги --force и --approve-mcps присутствуют в cursor_cli_interface.py")
    
    def test_cursor_cli_interface_initialization(self):
        """Проверка инициализации CursorCLIInterface"""
        # Создаем интерфейс
        cli = create_cursor_cli_interface()
        
        assert cli is not None, "Не удалось создать CursorCLIInterface"
        assert isinstance(cli, CursorCLIInterface), "Неверный тип интерфейса"
        
        print("[OK] CursorCLIInterface успешно инициализирован")
        print(f"   - CLI доступен: {cli.cli_available}")
        print(f"   - Команда: {cli.cli_command}")
    
    def test_documentation_exists(self, project_root):
        """Проверка наличия документации по полному доступу"""
        docs_dir = project_root / "docs" / "integration"
        
        # Проверка основной документации
        full_access_doc = docs_dir / "full_access_setup.md"
        assert full_access_doc.exists(), "Документация full_access_setup.md не найдена"
        
        # Проверка быстрого старта
        quick_start_doc = docs_dir / "QUICK_START_FULL_ACCESS.md"
        assert quick_start_doc.exists(), "Документация QUICK_START_FULL_ACCESS.md не найдена"
        
        # Проверка README в .cursor
        cursor_readme = project_root / ".cursor" / "README.md"
        assert cursor_readme.exists(), "README.md в .cursor не найден"
        
        print("[OK] Вся документация по полному доступу присутствует")


def run_tests():
    """Запуск всех тестов"""
    print("\n" + "="*70)
    print("ТЕСТИРОВАНИЕ ПОЛНОГО ДОСТУПА CURSOR CLI")
    print("="*70 + "\n")
    
    # Запускаем pytest
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_tests()
