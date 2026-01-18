# Makefile for Code Agent project

.PHONY: help install install-dev install-test test test-unit test-integration test-slow test-coverage test-watch clean lint format check

help:
	@echo "Code Agent - Makefile commands:"
	@echo ""
	@echo "Installation:"
	@echo "  make install          - Install project dependencies"
	@echo "  make install-dev      - Install development dependencies"
	@echo "  make install-test     - Install test dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-slow        - Run slow tests"
	@echo "  make test-coverage    - Run tests with coverage report"
	@echo "  make test-watch       - Run tests in watch mode"
	@echo "  make test-parallel    - Run tests in parallel"
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
