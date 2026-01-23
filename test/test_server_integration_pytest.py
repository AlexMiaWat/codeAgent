#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграционные тесты сервера с автоматическим запуском через pytest
"""

import pytest
import requests


class TestServerIntegration:
    """Интеграционные тесты HTTP сервера"""

    @pytest.mark.requires_server
    def test_health_endpoint(self):
        """Тест health endpoint"""
        response = requests.get("http://127.0.0.1:3456/health", timeout=5)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"

    @pytest.mark.requires_server
    def test_root_endpoint(self):
        """Тест root endpoint"""
        response = requests.get("http://127.0.0.1:3456/", timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "port" in data
        assert "session_id" in data
        assert data["port"] == 3456

    @pytest.mark.requires_server
    def test_status_endpoint(self):
        """Тест status endpoint"""
        response = requests.get("http://127.0.0.1:3456/status", timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert "server" in data
        assert "tasks" in data

        server_info = data["server"]
        assert "status" in server_info
        assert "project_dir" in server_info

    @pytest.mark.requires_server
    def test_stop_endpoint(self):
        """Тест stop endpoint"""
        response = requests.post("http://127.0.0.1:3456/stop", timeout=5)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "message" in data