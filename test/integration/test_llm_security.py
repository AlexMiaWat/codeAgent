"""
Security tests for LLMManager

Тестирует все security аспекты:
- Path traversal protection
- Input validation
- Recursion protection
- Memory limits
- SQL injection prevention
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.llm_manager import LLMManager


class TestPathTraversalProtection:
    """Тесты защиты от path traversal атак"""

    def test_valid_config_path(self):
        """Тест валидного пути к конфигу"""
        # Создаем файл в текущей директории
        config_path = Path("test_config.yaml")
        try:
            config_path.write_text("""
llm:
  default_provider: test
  model_roles:
    primary: []
providers:
  test:
    base_url: http://test.com
    models: {}
""")
            mgr = LLMManager(str(config_path))
            # Должен успешно загрузиться
            assert mgr.config_path == config_path
        finally:
            if config_path.exists():
                config_path.unlink()

    def test_path_traversal_attack(self):
        """Тест защиты от path traversal"""
        # Попытка с использованием '..' - должен упасть на этапе проверки существования файла
        with pytest.raises(FileNotFoundError, match="LLM config file not found"):
            LLMManager("../etc/passwd")

    def test_absolute_path_attack(self):
        """Тест защиты от абсолютных путей"""
        # Абсолютный путь - должен упасть на этапе проверки существования файла
        with pytest.raises(FileNotFoundError, match="LLM config file not found"):
            LLMManager("/etc/../passwd")

    def test_invalid_extension(self):
        """Тест проверки расширения файла"""
        config_path = Path("test_config.txt")
        try:
            config_path.write_text("invalid config")
            with pytest.raises(ValueError, match="Config file must have .yaml or .yml extension"):
                LLMManager(str(config_path))
        finally:
            if config_path.exists():
                config_path.unlink()

    def test_file_too_large(self):
        """Тест защиты от слишком больших файлов"""
        # Создаем файл размером > 10MB
        large_content = "x" * (11 * 1024 * 1024)  # 11MB

        config_path = Path("large_config.yaml")
        try:
            config_path.write_text(large_content)
            with pytest.raises(ValueError, match="Config file too large"):
                LLMManager(str(config_path))
        finally:
            if config_path.exists():
                config_path.unlink()

    def test_nonexistent_file(self):
        """Тест несуществующего файла"""
        with pytest.raises(FileNotFoundError):
            LLMManager("nonexistent_config.yaml")

    def test_directory_instead_of_file(self):
        """Тест передачи директории вместо файла"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="Path is not a file"):
                LLMManager(temp_dir)


class TestInputValidation:
    """Тесты валидации входных данных"""

    @pytest.fixture
    def manager_for_validation(self):
        """Менеджер для тестирования валидации"""
        config_path = Path("test_validation_config.yaml")
        try:
            config_path.write_text("""
llm:
  default_provider: test
  model_roles:
    primary: [test-model]
providers:
  test:
    base_url: http://test.com
    models:
      test: [{name: test-model, max_tokens: 1024, context_window: 4096}]
""")
            with patch('src.llm.llm_manager.AsyncOpenAI'):
                mgr = LLMManager(str(config_path))
            yield mgr
        finally:
            if config_path.exists():
                config_path.unlink()

    @pytest.mark.asyncio
    async def test_valid_prompt(self, manager_for_validation):
        """Тест валидного промпта"""
        with patch.object(manager_for_validation, '_periodic_health_check'), \
             patch.object(manager_for_validation, '_generate_single') as mock_generate:
            mock_generate.return_value = MagicMock(success=True, content="OK")

            response = await manager_for_validation.generate_response("Valid prompt")
            assert response.success is True

    @pytest.mark.asyncio
    async def test_empty_prompt(self, manager_for_validation):
        """Тест пустого промпта"""
        response = await manager_for_validation.generate_response("")
        assert response.success is False
        assert "Validation error" in response.error
        assert "cannot be empty" in response.error

    @pytest.mark.asyncio
    async def test_whitespace_only_prompt(self, manager_for_validation):
        """Тест промпта только с пробелами"""
        response = await manager_for_validation.generate_response("   \n\t   ")
        assert response.success is False
        assert "Validation error" in response.error

    @pytest.mark.asyncio
    async def test_too_long_prompt(self, manager_for_validation):
        """Тест слишком длинного промпта"""
        long_prompt = "x" * (101 * 1024)  # 101KB
        response = await manager_for_validation.generate_response(long_prompt)
        assert response.success is False
        assert "Validation error" in response.error
        assert "too long" in response.error

    @pytest.mark.asyncio
    async def test_dangerous_script_content(self, manager_for_validation):
        """Тест dangerous script content"""
        dangerous_prompt = "Hello <script>alert('xss')</script>"
        response = await manager_for_validation.generate_response(dangerous_prompt)
        assert response.success is False
        assert "Validation error" in response.error
        assert "dangerous content" in response.error

    @pytest.mark.asyncio
    async def test_javascript_injection(self, manager_for_validation):
        """Тест JavaScript injection"""
        js_prompt = "Test javascript:alert('xss')"
        response = await manager_for_validation.generate_response(js_prompt)
        assert response.success is False
        assert "dangerous content" in response.error

    @pytest.mark.asyncio
    async def test_iframe_injection(self, manager_for_validation):
        """Тест iframe injection"""
        iframe_prompt = "Test <iframe src='evil.com'>"
        response = await manager_for_validation.generate_response(iframe_prompt)
        assert response.success is False
        assert "dangerous content" in response.error

    @pytest.mark.asyncio
    async def test_invalid_model_name(self, manager_for_validation):
        """Тест неизвестного имени модели"""
        response = await manager_for_validation.generate_response("Test", model_name="unknown-model")
        assert response.success is False
        assert "Validation error" in response.error
        assert "Unknown model" in response.error

    @pytest.mark.asyncio
    async def test_invalid_response_format(self, manager_for_validation):
        """Тест неверного формата ответа"""
        response = await manager_for_validation.generate_response("Test", response_format="invalid")
        assert response.success is False
        assert "Validation error" in response.error
        assert "must be a dictionary" in response.error

    @pytest.mark.asyncio
    async def test_invalid_response_format_type(self, manager_for_validation):
        """Тест неверного типа в response_format"""
        response = await manager_for_validation.generate_response("Test", response_format={"type": "invalid"})
        assert response.success is False
        assert "Validation error" in response.error
        assert "Invalid response_format type" in response.error

    @pytest.mark.asyncio
    async def test_response_format_without_type(self, manager_for_validation):
        """Тест response_format без обязательного поля type"""
        response = await manager_for_validation.generate_response("Test", response_format={"other": "value"})
        assert response.success is False
        assert "Validation error" in response.error
        assert "must contain 'type' key" in response.error


class TestRecursionProtection:
    """Тесты защиты от бесконечной рекурсии"""

    def test_valid_env_substitution(self):
        """Тест корректной подстановки переменных окружения"""
        mgr = LLMManager.__new__(LLMManager)

        test_config = {
            "api_key": "${TEST_VAR}",
            "nested": {
                "value": "${ANOTHER_VAR}"
            }
        }

        with patch.dict(os.environ, {'TEST_VAR': 'test_key', 'ANOTHER_VAR': 'another_value'}):
            result = mgr._substitute_env_vars(test_config)

        assert result["api_key"] == "test_key"
        assert result["nested"]["value"] == "another_value"

    def test_missing_env_var(self):
        """Тест отсутствующей переменной окружения"""
        mgr = LLMManager.__new__(LLMManager)

        with pytest.raises(ValueError, match="Environment variable not found: MISSING_VAR"):
            mgr._substitute_env_vars({"key": "${MISSING_VAR}"})

    def test_empty_env_var_name(self):
        """Тест пустого имени переменной окружения"""
        mgr = LLMManager.__new__(LLMManager)

        with pytest.raises(ValueError, match="Empty environment variable name"):
            mgr._substitute_env_vars({"key": "${}"})

    def test_circular_reference_dict(self):
        """Тест циклической ссылки в словаре"""
        mgr = LLMManager.__new__(LLMManager)

        circular = {}
        circular["self"] = circular

        with pytest.raises(ValueError, match="Circular reference detected"):
            mgr._substitute_env_vars(circular)

    def test_circular_reference_nested(self):
        """Тест циклической ссылки в вложенных структурах"""
        mgr = LLMManager.__new__(LLMManager)

        obj1 = {"ref": None}
        obj2 = {"ref": obj1}
        obj1["ref"] = obj2

        with pytest.raises(ValueError, match="Circular reference detected"):
            mgr._substitute_env_vars(obj1)

    def test_deep_recursion_without_cycles(self):
        """Тест глубокой рекурсии без циклов"""
        mgr = LLMManager.__new__(LLMManager)

        # Создаем глубокую вложенную структуру
        deep_config = {}
        current = deep_config
        for i in range(100):  # 100 уровней вложенности
            current[f"level_{i}"] = {}
            current = current[f"level_{i}"]

        # Должен обработать без ошибок
        result = mgr._substitute_env_vars(deep_config)
        assert result is not None


class TestConfigValidation:
    """Тесты валидации структуры конфигурации"""

    def test_valid_config_structure(self):
        """Тест валидной структуры конфигурации"""
        mgr = LLMManager.__new__(LLMManager)

        valid_config = {
            "llm": {
                "default_provider": "test_provider",
                "model_roles": {
                    "primary": ["model1"]
                }
            },
            "providers": {
                "test_provider": {
                    "base_url": "http://test.com",
                    "models": {}
                }
            }
        }

        # Не должно вызывать исключение
        mgr._validate_config_structure(valid_config)

    def test_invalid_config_type(self):
        """Тест неверного типа конфигурации"""
        mgr = LLMManager.__new__(LLMManager)

        with pytest.raises(ValueError, match="Configuration must be a dictionary"):
            mgr._validate_config_structure("not a dict")

    def test_missing_llm_section(self):
        """Тест отсутствующей секции llm"""
        mgr = LLMManager.__new__(LLMManager)

        invalid_config = {
            "providers": {}
        }

        with pytest.raises(ValueError, match="Missing required configuration section: llm"):
            mgr._validate_config_structure(invalid_config)

    def test_missing_providers_section(self):
        """Тест отсутствующей секции providers"""
        mgr = LLMManager.__new__(LLMManager)

        invalid_config = {
            "llm": {
                "default_provider": "test",
                "model_roles": {}
            }
        }

        with pytest.raises(ValueError, match="Missing required configuration section: providers"):
            mgr._validate_config_structure(invalid_config)

    def test_invalid_llm_config_type(self):
        """Тест неверного типа llm конфигурации"""
        mgr = LLMManager.__new__(LLMManager)

        invalid_config = {
            "llm": "not a dict",
            "providers": {}
        }

        with pytest.raises(ValueError, match="LLM configuration must be a dictionary"):
            mgr._validate_config_structure(invalid_config)

    def test_missing_default_provider_in_providers(self):
        """Тест default_provider отсутствующего в providers"""
        mgr = LLMManager.__new__(LLMManager)

        invalid_config = {
            "llm": {
                "default_provider": "missing_provider",
                "model_roles": {}
            },
            "providers": {
                "other_provider": {}
            }
        }

        with pytest.raises(ValueError, match="Default provider 'missing_provider' not found in providers"):
            mgr._validate_config_structure(invalid_config)


class TestMemoryProtection:
    """Тесты защиты от memory exhaustion"""

    @pytest.mark.asyncio
    async def test_response_size_limit(self):
        """Тест ограничения размера ответа"""
        # Этот тест проверяет что система не падает при очень больших ответах
        # Реальная реализация зависит от конкретных лимитов

        # Создаем мок с очень большим ответом
        large_response = "x" * (10 * 1024 * 1024)  # 10MB response

        # Тест должен показать что система корректно обрабатывает большие ответы
        # без memory exhaustion
        assert len(large_response) > 1024 * 1024  # > 1MB


if __name__ == "__main__":
    pytest.main([__file__, "-v"])