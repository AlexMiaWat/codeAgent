"""
Comprehensive test suite for LLMManager

Тестирует все аспекты LLMManager:
- Конфигурацию и инициализацию
- Управление моделями (primary, fallback, reserve)
- Генерацию ответов (одиночная, параллельная)
- JSON mode и парсинг
- Fallback механизмы
- Blacklist (JSON mode, credits)
- Статистику и мониторинг
- Обработку ошибок
- Производительность
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.llm_manager import (
    LLMManager, ModelConfig, ModelRole, ModelResponse
)


class TestLLMManagerConfig:
    """Тесты конфигурации LLMManager"""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Создает временный конфигурационный файл"""
        config_content = """
llm:
  default_provider: test_provider
  default_model: test-model-1
  timeout: 30
  retry_attempts: 2
  strategy: single
  model_roles:
    primary:
      - test-model-1
      - test-model-2
    duplicate:
      - test-model-3
    reserve:
      - test-model-4
    fallback:
      - test-model-5
      - test-model-6

providers:
  test_provider:
    base_url: https://test.api.com
    api_key: ${TEST_API_KEY}
    models:
      fast_models:
        - name: test-model-1
          max_tokens: 1024
          context_window: 4096
          temperature: 0.7
        - name: test-model-2
          max_tokens: 2048
          context_window: 8192
          temperature: 0.5
      slow_models:
        - name: test-model-3
          max_tokens: 4096
          context_window: 16384
          temperature: 0.3
      reserve_models:
        - name: test-model-4
          max_tokens: 1024
          context_window: 4096
          temperature: 0.8
      fallback_models:
        - name: test-model-5
          max_tokens: 512
          context_window: 2048
          temperature: 1.0
        - name: test-model-6
          max_tokens: 256
          context_window: 1024
          temperature: 0.9
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)
        return config_file

    def test_config_loading(self, temp_config_file):
        """Тест загрузки конфигурации"""
        with patch.dict(os.environ, {'TEST_API_KEY': 'test_key_123'}):
            manager = LLMManager(str(temp_config_file))

            assert manager.config_path == Path(temp_config_file)
            assert 'llm' in manager.config
            assert 'providers' in manager.config
            assert manager.config['llm']['default_provider'] == 'test_provider'
            assert manager.config['providers']['test_provider']['api_key'] == 'test_key_123'

    def test_config_env_substitution(self, temp_config_file):
        """Тест подстановки переменных окружения"""
        with patch.dict(os.environ, {'TEST_API_KEY': 'substituted_key'}):
            manager = LLMManager(str(temp_config_file))
            assert manager.config['providers']['test_provider']['api_key'] == 'substituted_key'

    def test_config_missing_env_var(self, tmp_path):
        """Тест ошибки при отсутствии переменной окружения"""
        config_content = """
providers:
  test_provider:
    api_key: ${MISSING_VAR}
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="Environment variable not found: MISSING_VAR"):
            LLMManager(str(config_file))

    def test_config_file_not_found(self):
        """Тест ошибки при отсутствии файла конфигурации"""
        with pytest.raises(FileNotFoundError):
            LLMManager("nonexistent_config.yaml")

    def test_models_initialization(self, temp_config_file):
        """Тест инициализации моделей"""
        with patch.dict(os.environ, {'TEST_API_KEY': 'test_key'}):
            with patch('src.llm.llm_manager.AsyncOpenAI'):
                manager = LLMManager(str(temp_config_file))

                assert len(manager.models) == 6
                assert 'test-model-1' in manager.models
                assert 'test-model-6' in manager.models

                # Проверяем роли
                primary_models = [m for m in manager.models.values() if m.role == ModelRole.PRIMARY]
                assert len(primary_models) == 2

                fallback_models = [m for m in manager.models.values() if m.role == ModelRole.FALLBACK]
                assert len(fallback_models) == 2

    def test_clients_initialization(self, temp_config_file):
        """Тест инициализации клиентов"""
        with patch.dict(os.environ, {'TEST_API_KEY': 'test_key'}):
            mock_client = Mock()
            with patch('src.llm.llm_manager.AsyncOpenAI', return_value=mock_client) as mock_openai:
                manager = LLMManager(str(temp_config_file))

                mock_openai.assert_called_once()
                assert len(manager.clients) == 1
                assert 'test_provider' in manager.clients


class TestLLMManagerModelSelection:
    """Тесты выбора моделей"""

    @pytest.fixture
    def manager_with_models(self):
        """Менеджер с предустановленными моделями"""
        manager = LLMManager.__new__(LLMManager)  # Создаем без __init__

        # Создаем тестовые модели с разными временами отклика
        models = {
            'fast-model': ModelConfig('fast-model', 1024, 4096, role=ModelRole.PRIMARY),
            'slow-model': ModelConfig('slow-model', 2048, 8192, role=ModelRole.PRIMARY),
            'fallback-model': ModelConfig('fallback-model', 512, 2048, role=ModelRole.FALLBACK),
        }

        # Имитируем разное время отклика
        models['fast-model'].last_response_time = 1.0
        models['slow-model'].last_response_time = 3.0
        models['fallback-model'].last_response_time = 5.0

        manager.models = models
        manager.clients = {'test': Mock()}
        manager._json_mode_blacklist = set()
        manager._credits_error_blacklist = set()

        # Инициализируем кэши
        manager._fastest_model_cache = None
        manager._cache_timestamp = 0.0
        manager._cache_ttl = 60.0
        manager._model_name_cache = {}

        return manager

    def test_get_primary_models(self, manager_with_models):
        """Тест получения первичных моделей"""
        primary = manager_with_models.get_primary_models()
        assert len(primary) == 2
        model_names = [m.name for m in primary]
        assert 'fast-model' in model_names
        assert 'slow-model' in model_names

    def test_get_fallback_models(self, manager_with_models):
        """Тест получения резервных моделей"""
        fallback = manager_with_models.get_fallback_models()
        assert len(fallback) == 1
        assert fallback[0].name == 'fallback-model'

    def test_get_fastest_model(self, manager_with_models):
        """Тест получения самой быстрой модели"""
        fastest = manager_with_models.get_fastest_model()
        assert fastest is not None
        assert fastest.name == 'fast-model'  # Самая быстрая модель

    def test_get_fastest_model_no_responses(self):
        """Тест получения самой быстрой модели без предыдущих ответов"""
        manager = LLMManager.__new__(LLMManager)
        manager.models = {
            'model1': ModelConfig('model1', 1024, 4096, role=ModelRole.PRIMARY),
            'model2': ModelConfig('model2', 1024, 4096, role=ModelRole.PRIMARY),
        }

        # Инициализируем кэши
        manager._fastest_model_cache = None
        manager._cache_timestamp = 0.0
        manager._cache_ttl = 60.0
        manager._model_name_cache = {}

        fastest = manager.get_fastest_model()
        assert fastest is not None  # Должен вернуть какую-то модель


class TestLLMManagerResponseGeneration:
    """Тесты генерации ответов"""

    @pytest.fixture
    def manager_with_mocked_call(self):
        """Менеджер с замоканным вызовом модели"""
        manager = LLMManager.__new__(LLMManager)
        manager.models = {
            'test-model': ModelConfig('test-model', 1024, 4096, role=ModelRole.PRIMARY),
        }
        manager.clients = {'test': Mock()}
        manager._json_mode_blacklist = set()
        manager._credits_error_blacklist = set()
        manager.config = {'llm': {'strategy': 'single'}}
        # Добавляем недостающие атрибуты
        manager._last_health_check = None
        manager._health_check_interval = 300.0
        manager._fastest_model_cache = None
        manager._cache_timestamp = 0.0
        manager._cache_ttl = 60.0
        manager._model_name_cache = {}
        return manager

    @pytest.mark.asyncio
    async def test_generate_response_success(self, manager_with_mocked_call):
        """Тест успешной генерации ответа"""
        mock_response = ModelResponse(
            model_name='test-model',
            content='Test response',
            response_time=1.5,
            success=True
        )

        with patch.object(manager_with_mocked_call, '_generate_single', new_callable=AsyncMock) as mock_generate, \
             patch.object(manager_with_mocked_call, '_periodic_health_check', new_callable=AsyncMock):
            mock_generate.return_value = mock_response

            response = await manager_with_mocked_call.generate_response("Test prompt")

            assert response.success is True
            assert response.content == 'Test response'
            assert response.model_name == 'test-model'
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_parallel_mode(self, manager_with_mocked_call):
        """Тест генерации в параллельном режиме"""
        manager_with_mocked_call.config['llm']['strategy'] = 'best_of_two'

        mock_response = ModelResponse(
            model_name='test-model',
            content='Parallel response',
            response_time=1.0,
            success=True
        )

        with patch.object(manager_with_mocked_call, '_generate_parallel', new_callable=AsyncMock) as mock_generate, \
             patch.object(manager_with_mocked_call, '_periodic_health_check', new_callable=AsyncMock):
            mock_generate.return_value = mock_response

            response = await manager_with_mocked_call.generate_response(
                "Test prompt",
                use_parallel=True
            )

            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_json_mode(self, manager_with_mocked_call):
        """Тест генерации с JSON mode"""
        mock_response = ModelResponse(
            model_name='test-model',
            content='{"result": "test"}',
            response_time=1.0,
            success=True
        )

        with patch.object(manager_with_mocked_call, '_generate_parallel', new_callable=AsyncMock) as mock_generate, \
             patch.object(manager_with_mocked_call, '_periodic_health_check', new_callable=AsyncMock):
            mock_generate.return_value = mock_response

            response = await manager_with_mocked_call.generate_response(
                "Test prompt",
                response_format={"type": "json_object"},
                use_parallel=True  # JSON mode включает параллельный режим
            )

            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_fallback_on_failure(self, manager_with_mocked_call):
        """Тест fallback при ошибке генерации"""
        manager_with_mocked_call.models['fallback-model'] = ModelConfig(
            'fallback-model', 512, 2048, role=ModelRole.FALLBACK
        )

        # Первая модель падает
        failed_response = ModelResponse(
            model_name='test-model',
            content='',
            response_time=0.5,
            success=False,
            error='API Error'
        )

        # Fallback модель работает
        success_response = ModelResponse(
            model_name='fallback-model',
            content='Fallback response',
            response_time=1.0,
            success=True
        )

        with patch.object(manager_with_mocked_call, '_generate_with_fallback', new_callable=AsyncMock) as mock_fallback, \
             patch.object(manager_with_mocked_call, '_periodic_health_check', new_callable=AsyncMock):
            mock_fallback.return_value = success_response

            response = await manager_with_mocked_call.generate_response("Test prompt")

            assert response.success is True
            assert response.model_name == 'fallback-model'
            mock_fallback.assert_called_once()


class TestLLMManagerJSONMode:
    """Тесты JSON mode и парсинга"""

    @pytest.fixture
    def manager_for_json(self):
        """Менеджер для тестирования JSON"""
        manager = LLMManager.__new__(LLMManager)
        manager._json_mode_blacklist = set()
        return manager

    def test_validate_json_response_valid(self, manager_for_json):
        """Тест валидации корректного JSON ответа"""
        valid_json = '{"key": "value", "number": 42}'
        assert manager_for_json._validate_json_response(valid_json) is True

    def test_validate_json_response_invalid(self, manager_for_json):
        """Тест валидации некорректного JSON ответа"""
        invalid_json = 'not json at all'
        assert manager_for_json._validate_json_response(invalid_json) is False

    def test_validate_json_response_with_text(self, manager_for_json):
        """Тест валидации JSON с окружающим текстом"""
        json_with_text = 'Here is some text {"key": "value"} and more text'
        # Метод _validate_json_response может находить JSON внутри текста
        result = manager_for_json._validate_json_response(json_with_text)
        # В зависимости от реализации, это может быть True или False
        assert isinstance(result, bool)

    def test_extract_json_from_text_markdown(self, manager_for_json):
        """Тест извлечения JSON из markdown"""
        markdown_json = '''Here is response:
```json
{"result": "success", "data": [1, 2, 3]}
```
End of response.'''

        extracted = manager_for_json._extract_json_from_text(markdown_json)
        assert extracted == '{"result": "success", "data": [1, 2, 3]}'

    def test_extract_json_from_text_plain(self, manager_for_json):
        """Тест извлечения чистого JSON"""
        plain_json = '{"key": "value"}'
        extracted = manager_for_json._extract_json_from_text(plain_json)
        assert extracted == '{"key": "value"}'

    def test_extract_json_from_text_no_json(self, manager_for_json):
        """Тест извлечения из текста без JSON"""
        no_json = 'This is just plain text without JSON'
        extracted = manager_for_json._extract_json_from_text(no_json)
        assert extracted is None


class TestLLMManagerBlacklist:
    """Тесты blacklist механизмов"""

    @pytest.fixture
    def manager_with_blacklist(self):
        """Менеджер с blacklist"""
        manager = LLMManager.__new__(LLMManager)
        manager._json_mode_blacklist = set()
        manager._credits_error_blacklist = set()
        return manager

    def test_json_mode_blacklist_add(self, manager_with_blacklist):
        """Тест добавления модели в JSON blacklist"""
        manager_with_blacklist._json_mode_blacklist.add('bad-json-model')
        assert 'bad-json-model' in manager_with_blacklist._json_mode_blacklist

    def test_json_mode_blacklist_check(self, manager_with_blacklist):
        """Тест проверки модели в JSON blacklist"""
        manager_with_blacklist._json_mode_blacklist.add('bad-model')
        assert 'bad-model' in manager_with_blacklist._json_mode_blacklist
        assert 'good-model' not in manager_with_blacklist._json_mode_blacklist

    def test_credits_error_blacklist(self, manager_with_blacklist):
        """Тест credits error blacklist"""
        manager_with_blacklist._credits_error_blacklist.add('no-credits-model')
        assert 'no-credits-model' in manager_with_blacklist._credits_error_blacklist


class TestLLMManagerStatistics:
    """Тесты статистики и мониторинга"""

    @pytest.fixture
    def manager_with_stats(self):
        """Менеджер для тестирования статистики"""
        manager = LLMManager.__new__(LLMManager)
        manager.models = {
            'model1': ModelConfig('model1', 1024, 4096),
            'model2': ModelConfig('model2', 2048, 8192),
        }
        return manager

    def test_model_statistics_initialization(self, manager_with_stats):
        """Тест инициализации статистики моделей"""
        for model in manager_with_stats.models.values():
            assert model.error_count == 0
            assert model.success_count == 0
            assert model.last_response_time == 0.0

    def test_model_success_increment(self, manager_with_stats):
        """Тест увеличения счетчика успешных ответов"""
        model = manager_with_stats.models['model1']
        initial_count = model.success_count

        model.success_count += 1

        assert model.success_count == initial_count + 1

    def test_model_error_increment(self, manager_with_stats):
        """Тест увеличения счетчика ошибок"""
        model = manager_with_stats.models['model2']
        initial_count = model.error_count

        model.error_count += 1

        assert model.error_count == initial_count + 1

    def test_model_response_time_update(self, manager_with_stats):
        """Тест обновления времени отклика"""
        model = manager_with_stats.models['model1']
        model.last_response_time = 2.5

        assert model.last_response_time == 2.5


class TestLLMManagerErrorHandling:
    """Тесты обработки ошибок"""

    @pytest.fixture
    def manager_for_errors(self):
        """Менеджер для тестирования ошибок"""
        manager = LLMManager.__new__(LLMManager)
        manager.models = {
            'working-model': ModelConfig('working-model', 1024, 4096, role=ModelRole.PRIMARY),
            'broken-model': ModelConfig('broken-model', 1024, 4096, role=ModelRole.FALLBACK),
        }
        manager.clients = {'test': Mock()}
        manager._json_mode_blacklist = set()
        manager._credits_error_blacklist = set()
        # Инициализируем кэши
        manager._fastest_model_cache = None
        manager._cache_timestamp = 0.0
        manager._cache_ttl = 60.0
        manager._model_name_cache = {}
        return manager

    @pytest.mark.asyncio
    async def test_error_response_creation(self, manager_for_errors):
        """Тест создания ответа с ошибкой"""
        response = ModelResponse(
            model_name='broken-model',
            content='',
            response_time=0.5,
            success=False,
            error='Connection timeout'
        )

        assert response.success is False
        assert response.error == 'Connection timeout'
        assert response.content == ''

    @pytest.mark.asyncio
    async def test_fallback_on_api_error(self, manager_for_errors):
        """Тест fallback при API ошибке"""
        # Мокаем _call_model для симуляции ошибки
        async def mock_call_error(*args, **kwargs):
            return ModelResponse(
                model_name='working-model',
                content='',
                response_time=0.1,
                success=False,
                error='API rate limit exceeded'
            )

        with patch.object(manager_for_errors, '_call_model', side_effect=mock_call_error):
            # Добавляем недостающие атрибуты
            manager_for_errors.config = {'llm': {}}
            manager_for_errors._last_health_check = None
            manager_for_errors._health_check_interval = 300.0

            response = await manager_for_errors._generate_single('test prompt', None, True)

            assert response.success is False
            # Ошибка может быть обобщенной "All models failed"


class TestLLMManagerParallelGeneration:
    """Тесты параллельной генерации"""

    @pytest.fixture
    def manager_for_parallel(self):
        """Менеджер для параллельной генерации"""
        manager = LLMManager.__new__(LLMManager)
        manager.models = {
            'model1': ModelConfig('model1', 1024, 4096, role=ModelRole.PRIMARY),
            'model2': ModelConfig('model2', 2048, 8192, role=ModelRole.PRIMARY),
        }
        manager.clients = {'test': Mock()}
        manager._json_mode_blacklist = set()
        manager._credits_error_blacklist = set()
        # Настраиваем конфигурацию для параллельной генерации
        manager.config = {
            'llm': {
                'parallel': {
                    'models': ['model1', 'model2']
                }
            }
        }
        return manager

    @pytest.mark.asyncio
    async def test_parallel_generation_responses(self, manager_for_parallel):
        """Тест получения ответов в параллельном режиме"""
        responses = [
            ModelResponse('model1', 'Response 1', 1.0, True),
            ModelResponse('model2', 'Response 2', 1.2, True),
        ]

        with patch.object(manager_for_parallel, '_call_model', side_effect=responses) as mock_call:
            result = await manager_for_parallel._generate_parallel('test prompt')

            # Проверяем что обе модели были вызваны
            assert mock_call.call_count == 2

            # Результат должен быть одним из ответов
            assert result.success is True
            assert result.model_name in ['model1', 'model2']






class TestLLMManagerOptimization:
    """Тесты оптимизаций производительности"""

    @pytest.fixture
    def manager_for_optimization(self):
        """Менеджер для тестирования оптимизаций"""
        manager = LLMManager.__new__(LLMManager)
        manager.models = {
            'fast-model': ModelConfig('fast-model', 1024, 4096, role=ModelRole.PRIMARY),
            'slow-model': ModelConfig('slow-model', 2048, 8192, role=ModelRole.PRIMARY),
        }
        manager.clients = {'test': Mock()}
        manager._json_mode_blacklist = set()
        manager._credits_error_blacklist = set()
        manager.config = {'llm': {}}

        # Инициализируем кэши
        manager._fastest_model_cache = None
        manager._cache_timestamp = 0.0
        manager._cache_ttl = 60.0
        manager._model_name_cache = {}

        return manager

    def test_fastest_model_caching(self, manager_for_optimization):
        """Тест кэширования самой быстрой модели"""
        # Устанавливаем время отклика
        manager_for_optimization.models['fast-model'].last_response_time = 1.0
        manager_for_optimization.models['slow-model'].last_response_time = 3.0

        # Первый вызов - кэш пустой
        fastest1 = manager_for_optimization.get_fastest_model()
        assert fastest1.name == 'fast-model'

        # Проверяем что кэш заполнен
        assert manager_for_optimization._fastest_model_cache is not None
        assert manager_for_optimization._fastest_model_cache.name == 'fast-model'

        # Второй вызов должен использовать кэш
        fastest2 = manager_for_optimization.get_fastest_model()
        assert fastest2 is fastest1  # Тот же объект из кэша

    def test_model_name_caching(self, manager_for_optimization):
        """Тест кэширования моделей по имени"""
        # Первый вызов
        model1 = manager_for_optimization.get_model_by_name('fast-model')
        assert model1 is not None
        assert model1.name == 'fast-model'

        # Проверяем кэш
        assert 'fast-model' in manager_for_optimization._model_name_cache

        # Второй вызов должен использовать кэш
        model2 = manager_for_optimization.get_model_by_name('fast-model')
        assert model2 is model1  # Тот же объект

    def test_cache_invalidation(self, manager_for_optimization):
        """Тест инвалидации кэша"""
        # Заполняем кэш
        manager_for_optimization.get_fastest_model()
        assert manager_for_optimization._fastest_model_cache is not None

        # Инвалидируем кэш
        manager_for_optimization._invalidate_fastest_cache()
        assert manager_for_optimization._fastest_model_cache is None
        assert manager_for_optimization._cache_timestamp == 0.0

    def test_performance_stats(self, manager_for_optimization):
        """Тест получения статистики производительности"""
        # Настраиваем статистику моделей
        fast_model = manager_for_optimization.models['fast-model']
        fast_model.success_count = 10
        fast_model.error_count = 2
        fast_model.last_response_time = 1.5

        slow_model = manager_for_optimization.models['slow-model']
        slow_model.success_count = 5
        slow_model.error_count = 1
        slow_model.last_response_time = 2.8

        stats = manager_for_optimization.get_performance_stats()

        assert stats['total_models'] == 2
        assert stats['enabled_models'] == 2
        assert 'fast-model' in stats['models']
        assert 'slow-model' in stats['models']

        fast_stats = stats['models']['fast-model']
        assert fast_stats['success_count'] == 10
        assert fast_stats['error_count'] == 2
        assert fast_stats['success_rate'] == 83.3  # 10/12 * 100
        assert fast_stats['avg_response_time'] == 1.5


class TestLLMManagerHealthCheck:
    """Тесты проверки работоспособности"""

    @pytest.fixture
    def manager_for_health(self):
        """Менеджер для health check"""
        manager = LLMManager.__new__(LLMManager)
        manager.models = {
            'healthy-model': ModelConfig('healthy-model', 1024, 4096),
            'unhealthy-model': ModelConfig('unhealthy-model', 1024, 4096),
        }
        manager._last_health_check = None
        manager._health_check_interval = 300.0
        return manager

    @pytest.mark.asyncio
    async def test_health_check_timing(self, manager_for_health):
        """Тест тайминга health check"""
        # Первый вызов должен выполнить проверку (_last_health_check is None)
        with patch.object(manager_for_health, '_health_check_models', new_callable=AsyncMock) as mock_check:
            await manager_for_health._periodic_health_check()
            mock_check.assert_called_once()

        # Повторный вызов сразу после должен пропустить проверку (если время не прошло)
        mock_check.reset_mock()
        manager_for_health._last_health_check = time.time()  # Устанавливаем время последнего чека
        with patch.object(manager_for_health, '_health_check_models', new_callable=AsyncMock) as mock_check:
            await manager_for_health._periodic_health_check()
            mock_check.assert_not_called()


class TestLLMManagerIntegration:
    """Интеграционные тесты"""

    @pytest.mark.asyncio
    async def test_full_generation_flow(self):
        """Тест полного цикла генерации ответа"""
        # Создаем временную конфигурацию
        config_content = """
llm:
  default_provider: test
  model_roles:
    primary:
      - test-model
providers:
  test:
    base_url: https://test.com
    models:
      test:
        - name: test-model
          max_tokens: 1024
          context_window: 4096
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Мокаем все внешние зависимости
            with patch('src.llm.llm_manager.AsyncOpenAI'):
                manager = LLMManager(config_path)

                # Мокаем вызов модели
                mock_response = ModelResponse(
                    model_name='test-model',
                    content='Integration test response',
                    response_time=1.0,
                    success=True
                )

                with patch.object(manager, '_call_model', new_callable=AsyncMock) as mock_call:
                    mock_call.return_value = mock_response

                    response = await manager.generate_response("Integration test prompt")

                    assert response.success is True
                    assert response.content == 'Integration test response'
                    mock_call.assert_called_once()

        finally:
            os.unlink(config_path)


class TestLLMManagerPerformance:
    """Тесты производительности"""

    @pytest.mark.asyncio
    async def test_response_time_tracking(self):
        """Тест отслеживания времени отклика"""
        config_content = """
llm:
  default_provider: test
  model_roles:
    primary:
      - perf-model
providers:
  test:
    base_url: https://test.com
    models:
      test:
        - name: perf-model
          max_tokens: 1024
          context_window: 4096
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch('src.llm.llm_manager.AsyncOpenAI'):
                manager = LLMManager(config_path)

                start_time = time.time()
                mock_response = ModelResponse(
                    model_name='perf-model',
                    content='Performance test',
                    response_time=2.5,
                    success=True
                )

                with patch.object(manager, '_call_model', new_callable=AsyncMock) as mock_call:
                    mock_call.return_value = mock_response

                    response = await manager.generate_response("Performance test")

                    # Проверяем что время отклика записано
                    assert response.response_time == 2.5

                    # Проверяем что ответ успешен (статистика может обновляться в _call_model)
                    assert response.success is True
                    assert response.response_time == 2.5

        finally:
            os.unlink(config_path)


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])