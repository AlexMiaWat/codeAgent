#!/usr/bin/env python3
"""
Тесты Docker конфигурации Smart Agent
Проверяет правильность настройки Docker для Smart Agent
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml


def test_docker_compose_agent_structure():
    """Тест структуры docker-compose.agent.yml"""
    print("🐳 Тестирование структуры docker-compose.agent.yml...")

    try:
        # Загружаем docker-compose.agent.yml
        with open('docker/docker-compose.agent.yml', 'r', encoding='utf-8') as f:
            compose_config = yaml.safe_load(f)

        # Проверяем наличие секции services
        assert 'services' in compose_config, "Секция services отсутствует в docker-compose"
        assert 'agent' in compose_config['services'], "Сервис agent отсутствует"

        agent_service = compose_config['services']['agent']

        # Проверяем обязательные поля сервиса
        required_fields = ['build', 'image', 'container_name', 'volumes', 'working_dir', 'environment']
        for field in required_fields:
            assert field in agent_service, f"Поле {field} отсутствует в сервисе agent"

        # Проверяем build контекст
        build_config = agent_service['build']
        assert 'context' in build_config, "context отсутствует в build"
        assert build_config['context'] == '..', "context должен быть '..' (корень проекта)"

        # Проверяем Dockerfile
        assert 'dockerfile' in build_config, "dockerfile отсутствует в build"
        assert build_config['dockerfile'] == 'docker/Dockerfile.agent', "dockerfile должен быть 'docker/Dockerfile.agent'"

        # Проверяем volumes
        volumes = agent_service['volumes']
        assert len(volumes) >= 3, "Должно быть минимум 3 volume монтирования"

        # Проверяем наличие volume для проекта
        project_volume_found = False
        agent_home_volume_found = False
        ssh_volume_found = False

        for volume in volumes:
            if '../../life:/workspace:rw' in volume:
                project_volume_found = True
            if 'agent-home:/root' in volume:
                agent_home_volume_found = True
            if '.ssh:/root/.ssh:rw' in volume or '/.ssh' in volume:
                ssh_volume_found = True

        assert project_volume_found, "Volume для монтирования проекта life отсутствует"
        assert agent_home_volume_found, "Volume agent-home отсутствует"
        assert ssh_volume_found, "Volume для SSH ключей отсутствует"

        print("✅ Структура docker-compose.agent.yml корректна")
        print(f"   Сервис: {agent_service['container_name']}")
        print(f"   Image: {agent_service['image']}")
        print(f"   Volumes: {len(volumes)}")

        return True

    except Exception as e:
        print(f"❌ Ошибка проверки структуры docker-compose: {e}")
        return False


def test_dockerfile_agent_structure():
    """Тест структуры Dockerfile.agent"""
    print("\n🏗️  Тестирование структуры Dockerfile.agent...")

    try:
        # Читаем Dockerfile
        with open('docker/Dockerfile.agent', 'r', encoding='utf-8') as f:
            dockerfile_content = f.read()

        # Проверяем базовый образ
        assert 'FROM ubuntu:22.04' in dockerfile_content, "Базовый образ должен быть ubuntu:22.04"

        # Проверяем установку зависимостей
        required_packages = ['curl', 'bash', 'git', 'ca-certificates', 'openssh-client']
        for package in required_packages:
            assert f'    {package} \\' in dockerfile_content, f"Пакет {package} не устанавливается"

        # Проверяем установку Cursor CLI
        assert 'curl https://cursor.com/install' in dockerfile_content, "Установка Cursor CLI отсутствует"

        # Проверяем переменные окружения
        assert 'ENV AGENT_WORKING_DIR=/workspace' in dockerfile_content, "AGENT_WORKING_DIR не установлена"
        assert 'ENV AGENT_HOME=/root' in dockerfile_content, "AGENT_HOME не установлена"

        # Проверяем создание скрипта запуска
        assert 'RUN cat > /start.sh' in dockerfile_content, "Скрипт запуска /start.sh не создается"

        # Проверяем HEALTHCHECK
        assert 'HEALTHCHECK' in dockerfile_content, "HEALTHCHECK отсутствует"

        # Проверяем CMD
        assert 'CMD ["/start.sh"]' in dockerfile_content, "CMD не указывает на /start.sh"

        print("✅ Структура Dockerfile.agent корректна")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки структуры Dockerfile: {e}")
        return False


def test_docker_compose_environment_variables():
    """Тест переменных окружения в docker-compose"""
    print("\n🌍 Тестирование переменных окружения в docker-compose...")

    try:
        with open('docker/docker-compose.agent.yml', 'r', encoding='utf-8') as f:
            compose_config = yaml.safe_load(f)

        agent_service = compose_config['services']['agent']
        environment = agent_service.get('environment', [])

        # Проверяем наличие обязательных переменных
        required_env_vars = [
            'AGENT_WORKING_DIR=/workspace',
            'AGENT_HOME=/root'
        ]

        # Проверяем переменные окружения с fallback
        conditional_env_vars = [
            'CURSOR_API_KEY=${CURSOR_API_KEY:-}',
            'LANG=C.utf8',
            'LC_ALL=C.utf8'
        ]

        for env_var in required_env_vars + conditional_env_vars:
            assert env_var in environment, f"Переменная окружения {env_var} отсутствует"

        print("✅ Переменные окружения в docker-compose корректны")
        print(f"   Всего переменных: {len(environment)}")

        return True

    except Exception as e:
        print(f"❌ Ошибка проверки переменных окружения: {e}")
        return False


def test_docker_compose_networking():
    """Тест настроек сети и портов в docker-compose"""
    print("\n🌐 Тестирование настроек сети в docker-compose...")

    try:
        with open('docker/docker-compose.agent.yml', 'r', encoding='utf-8') as f:
            compose_config = yaml.safe_load(f)

        agent_service = compose_config['services']['agent']

        # Проверяем отсутствие exposed портов (агент не должен открывать порты)
        assert 'ports' not in agent_service, "Сервис agent не должен экспортировать порты"

        # Проверяем restart policy
        assert 'restart' in agent_service, "restart policy отсутствует"
        assert agent_service['restart'] == 'unless-stopped', "restart должен быть 'unless-stopped'"

        # Проверяем logging
        assert 'logging' in agent_service, "logging конфигурация отсутствует"
        logging_config = agent_service['logging']
        assert logging_config['driver'] == 'json-file', "logging driver должен быть 'json-file'"

        print("✅ Настройки сети и логирования корректны")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки сетевых настроек: {e}")
        return False


def test_docker_compose_volumes_config():
    """Тест конфигурации volumes в docker-compose"""
    print("\n💾 Тестирование конфигурации volumes в docker-compose...")

    try:
        with open('docker/docker-compose.agent.yml', 'r', encoding='utf-8') as f:
            compose_config = yaml.safe_load(f)

        # Проверяем volumes на уровне compose файла
        assert 'volumes' in compose_config, "volumes секция отсутствует в корне compose файла"

        compose_volumes = compose_config['volumes']
        assert 'agent-home' in compose_volumes, "volume agent-home отсутствует"
        assert compose_volumes['agent-home']['driver'] == 'local', "agent-home должен использовать local driver"

        # Проверяем volumes в сервисе
        agent_service = compose_config['services']['agent']
        service_volumes = agent_service['volumes']

        # Проверяем конкретные монтирования
        expected_mounts = {
            'project': '../../life:/workspace:rw',
            'agent_home': 'agent-home:/root',
            'ssh_keys': '${HOME}/.ssh:/root/.ssh:rw'
        }

        for mount_type, expected_mount in expected_mounts.items():
            found = False
            for volume in service_volumes:
                if expected_mount in volume:
                    found = True
                    break
            assert found, f"Монтирование {mount_type} ({expected_mount}) отсутствует"

        print("✅ Конфигурация volumes корректна")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки volumes: {e}")
        return False


def test_docker_smart_agent_integration():
    """Тест интеграции Docker с конфигурацией Smart Agent"""
    print("\n🔗 Тестирование интеграции Docker с Smart Agent...")

    try:
        # Загружаем конфигурацию Smart Agent
        from config.config_loader import ConfigLoader
        config = ConfigLoader.load_config()

        cursor_config = config.get('cursor', {})
        cli_config = cursor_config.get('cli', {})

        # Проверяем, что CLI путь указывает на Docker
        cli_path = cli_config.get('cli_path', '')
        assert cli_path == 'docker-compose-agent', "cli_path должен быть 'docker-compose-agent' для Docker интеграции"

        # Проверяем, что Docker интеграция включена
        assert cursor_config.get('interface_type') == 'cli', "interface_type должен быть 'cli' для Docker"

        # Проверяем наличие Docker в allow_shell
        permissions = cursor_config.get('permissions', {})
        allow_shell = permissions.get('allow_shell', [])

        docker_commands = ['docker', 'docker-compose']
        for cmd in docker_commands:
            assert cmd in allow_shell, f"Команда {cmd} отсутствует в allow_shell"

        print("✅ Интеграция Docker с Smart Agent корректна")
        print(f"   CLI path: {cli_path}")
        print(f"   Interface type: {cursor_config.get('interface_type')}")

        return True

    except Exception as e:
        print(f"❌ Ошибка проверки интеграции Docker: {e}")
        return False


def test_docker_compose_validation():
    """Тест валидации docker-compose файла"""
    print("\n✅ Тестирование валидации docker-compose файла...")

    try:
        import subprocess

        # Проверяем синтаксис docker-compose файла
        result = subprocess.run(
            ['docker-compose', '-f', 'docker/docker-compose.agent.yml', 'config', '--quiet'],
            capture_output=True,
            text=True,
            cwd='.'
        )

        if result.returncode == 0:
            print("✅ Синтаксис docker-compose.agent.yml валиден")
        else:
            print(f"❌ Ошибка валидации docker-compose: {result.stderr}")
            return False

        # Альтернативная проверка через docker compose (новая версия)
        try:
            result2 = subprocess.run(
                ['docker', 'compose', '-f', 'docker/docker-compose.agent.yml', 'config', '--quiet'],
                capture_output=True,
                text=True,
                cwd='.'
            )

            if result2.returncode == 0:
                print("✅ Синтаксис валиден для docker compose (новая версия)")
            else:
                print(f"⚠️  docker compose config вернул ошибку: {result2.stderr}")

        except FileNotFoundError:
            print("⚠️  docker compose (новая версия) недоступен")

        return True

    except FileNotFoundError:
        print("⚠️  docker-compose недоступен, валидация пропущена")
        return True  # Не считаем ошибкой отсутствие docker-compose на тестовой машине
    except Exception as e:
        print(f"❌ Ошибка валидации docker-compose: {e}")
        return False


def test_docker_start_script_analysis():
    """Тест анализа скрипта запуска Docker контейнера"""
    print("\n📜 Тестирование анализа скрипта запуска...")

    try:
        with open('docker/Dockerfile.agent', 'r', encoding='utf-8') as f:
            dockerfile_content = f.read()

        # Ищем начало скрипта
        start_script_start = dockerfile_content.find('RUN cat > /start.sh << \'EOF\'')
        if start_script_start == -1:
            print("❌ Скрипт /start.sh не найден в Dockerfile")
            return False

        # Извлекаем скрипт (грубая оценка)
        script_content = dockerfile_content[start_script_start:]

        # Проверяем наличие ключевых компонентов скрипта
        required_script_elements = [
            'log()',
            'SSH directory found',
            'Cursor Agent Container Started',
            'while true',
            'sleep 3600'
        ]

        for element in required_script_elements:
            if element not in script_content:
                print(f"❌ Элемент скрипта '{element}' отсутствует")
                return False

        # Проверяем, что скрипт делает chmod +x
        assert 'chmod +x /start.sh' in dockerfile_content, "chmod +x для /start.sh отсутствует"

        print("✅ Скрипт запуска /start.sh корректен")
        return True

    except Exception as e:
        print(f"❌ Ошибка анализа скрипта запуска: {e}")
        return False


def test_docker_healthcheck_config():
    """Тест конфигурации HEALTHCHECK в Dockerfile"""
    print("\n💚 Тестирование HEALTHCHECK конфигурации...")

    try:
        with open('docker/Dockerfile.agent', 'r', encoding='utf-8') as f:
            dockerfile_content = f.read()

        # Проверяем наличие HEALTHCHECK
        assert 'HEALTHCHECK' in dockerfile_content, "HEALTHCHECK отсутствует"

        # Проверяем параметры HEALTHCHECK
        healthcheck_line = [line for line in dockerfile_content.split('\n') if line.strip().startswith('HEALTHCHECK')][0]

        required_params = ['--interval=1m', '--timeout=3s', '--start-period=5s', '--retries=3']
        for param in required_params:
            assert param in healthcheck_line, f"Параметр {param} отсутствует в HEALTHCHECK"

        # Проверяем команду проверки здоровья
        assert 'ps aux | grep -v grep | grep -q "start.sh"' in healthcheck_line, "Команда проверки здоровья некорректна"

        print("✅ HEALTHCHECK конфигурация корректна")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки HEALTHCHECK: {e}")
        return False


def main():
    """Основная функция тестирования Docker конфигурации"""
    print("🐳 Начало тестирования Docker конфигурации Smart Agent\n")

    results = []

    # Тестируем компоненты Docker конфигурации
    results.append(("Docker Compose Agent Structure", test_docker_compose_agent_structure()))
    results.append(("Dockerfile Agent Structure", test_dockerfile_agent_structure()))
    results.append(("Docker Compose Environment Variables", test_docker_compose_environment_variables()))
    results.append(("Docker Compose Networking", test_docker_compose_networking()))
    results.append(("Docker Compose Volumes Config", test_docker_compose_volumes_config()))
    results.append(("Docker Smart Agent Integration", test_docker_smart_agent_integration()))
    results.append(("Docker Compose Validation", test_docker_compose_validation()))
    results.append(("Docker Start Script Analysis", test_docker_start_script_analysis()))
    results.append(("Docker Healthcheck Config", test_docker_healthcheck_config()))

    # Итоги тестирования
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ DOCKER КОНФИГУРАЦИИ SMART AGENT")
    print("="*70)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print("40")
        if success:
            passed += 1

    print(f"\n📈 ИТОГО: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Docker конфигурация Smart Agent работает корректно.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется дополнительная настройка.")
        return 1


if __name__ == "__main__":
    sys.exit(main())