# Makefile for Code Agent project

.PHONY: help install install-dev install-test test test-unit test-integration test-slow test-coverage test-watch test-openrouter test-api test-cursor test-llm test-list clean lint format check

help:
	@echo "Code Agent - Makefile commands:"
	@echo ""
	@echo "Installation:"
	@echo "  make install          - Install project dependencies"
	@echo "  make install-dev      - Install development dependencies"
	@echo "  make install-test     - Install test dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests (pytest)"
	@echo "  make test-all         - Run all tests via unified runner"
	@echo "  make test-list        - List all available test categories"
	@echo "  make test-openrouter  - Run OpenRouter API tests"
	@echo "  make test-api         - Run HTTP API server tests"
	@echo "  make test-cursor      - Run Cursor integration tests"
	@echo "  make test-llm         - Run LLM core tests"
	@echo "  make test-unit        - Run unit tests only (pytest)"
	@echo "  make test-integration - Run integration tests only (pytest)"
	@echo "  make test-slow        - Run slow tests (pytest)"
	@echo "  make test-coverage    - Run tests with coverage report (pytest)"
	@echo "  make test-watch       - Run tests in watch mode (pytest)"
	@echo "  make test-parallel    - Run tests in parallel (pytest)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             - Run linters"
	@echo "  make format           - Format code with black"
	@echo "  make check            - Run all checks (lint + test)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove generated files"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     - Build Docker image"
	@echo "  make docker-test      - Run tests in Docker"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-test:
	pip install -e ".[test]"

# Testing targets
test:
	pytest test/ -v

test-unit:
	pytest test/ -v -m unit

test-integration:
	pytest test/ -v -m integration

test-slow:
	pytest test/ -v -m slow

test-coverage:
	pytest test/ --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	pytest-watch test/ -v

test-parallel:
	pytest test/ -v -n auto

# Unified test runner targets
test-all:
	python test/run_tests.py

test-list:
	python test/run_tests.py --list

test-openrouter:
	python test/run_tests.py --openrouter

test-api:
	python test/run_tests.py --api

test-cursor:
	python test/run_tests.py --cursor

test-llm:
	python test/run_tests.py --llm

test-validation:
	python test/run_tests.py --validation

test-checkpoint:
	python test/run_tests.py --checkpoint

test-full:
	python test/run_tests.py --full

# Code quality targets
lint:
	ruff check src/ test/
	mypy src/

format:
	black src/ test/
	ruff check --fix src/ test/

check: lint test

# Cleanup targets
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov/ .mypy_cache .ruff_cache 2>/dev/null || true
	rm -rf build/ dist/ 2>/dev/null || true

# Docker targets
docker-build:
	docker build -f docker/Dockerfile.agent -t code-agent:latest .

docker-test:
	docker run --rm code-agent:latest pytest test/ -v

# Development server
run:
	python -m src.server

# Quick check before commit
pre-commit: format lint test-unit
	@echo "Pre-commit checks passed!"
