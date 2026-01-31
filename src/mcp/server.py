"""
MCP Server для Code Agent.

Реализует Model Context Protocol для предоставления доступа к ресурсам проекта.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import ConfigLoader
from .auth import AuthManager, User
from .resources import ResourceManager
from .cache import CacheManager
from .metrics import MetricsManager
from .tools import ToolsManager
from .prompts import PromptsManager


# MCP Protocol Models
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPNotification(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPInitializeRequest(BaseModel):
    protocolVersion: str
    capabilities: Dict[str, Any]
    clientInfo: Dict[str, str]


class MCPServerCapabilities(BaseModel):
    resources: Dict[str, Any] = {"subscribe": True, "listChanged": True}
    tools: Dict[str, Any] = {"listChanged": True}
    prompts: Dict[str, Any] = {"listChanged": True}
    logging: Dict[str, Any] = {}


class MCPServerInfo(BaseModel):
    name: str
    version: str


class MCPInitializeResult(BaseModel):
    protocolVersion: str
    capabilities: MCPServerCapabilities
    serverInfo: MCPServerInfo


# API Models
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]
    expires_in: int


class LogoutRequest(BaseModel):
    token: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class MCPServer:
    """
    MCP Server для предоставления контекста проекта Code Agent.
    """

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader
        self.logger = logging.getLogger(__name__)

        # Инициализация компонентов
        self.auth_manager = AuthManager(config_loader)
        self.resource_manager = ResourceManager(config_loader)
        self.cache_manager = CacheManager(config_loader)
        self.metrics_manager = MetricsManager(config_loader)
        self.tools_manager = ToolsManager(config_loader)
        self.prompts_manager = PromptsManager(config_loader)

        # FastAPI приложение
        self.app = FastAPI(
            title="Code Agent MCP Server",
            version="0.1.0",
            description="Model Context Protocol Server для Code Agent",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        self.setup_middleware()
        self.setup_routes()
        self.setup_exception_handlers()

        # WebSocket соединения
        self.active_connections: Dict[str, WebSocket] = {}
        self.request_handlers: Dict[str, Callable] = {}

        # Контекст текущих задач для интеграции с основной системой
        self.current_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_results: Dict[str, Dict[str, Any]] = {}

        self.setup_request_handlers()

    # Методы для интеграции с основной системой
    def update_task_context(self, task_id: str, context: Dict[str, Any]):
        """
        Обновление контекста задачи.

        Args:
            task_id: ID задачи
            context: Контекст задачи (описание, статус, приоритет и т.д.)
        """
        self.current_tasks[task_id] = {
            **context,
            "updated_at": datetime.utcnow().isoformat(),
            "mcp_context": True
        }
        self.logger.info(f"Task context updated: {task_id}")

    def get_task_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение контекста задачи.

        Args:
            task_id: ID задачи

        Returns:
            Контекст задачи или None
        """
        return self.current_tasks.get(task_id)

    def get_all_tasks_context(self) -> Dict[str, Dict[str, Any]]:
        """
        Получение контекста всех активных задач.

        Returns:
            Словарь с контекстами задач
        """
        return self.current_tasks.copy()

    def update_task_result(self, task_id: str, result: Dict[str, Any]):
        """
        Обновление результата выполнения задачи.

        Args:
            task_id: ID задачи
            result: Результат выполнения
        """
        self.task_results[task_id] = {
            **result,
            "completed_at": datetime.utcnow().isoformat()
        }
        self.logger.info(f"Task result updated: {task_id}")

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение результата выполнения задачи.

        Args:
            task_id: ID задачи

        Returns:
            Результат выполнения или None
        """
        return self.task_results.get(task_id)

    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """
        Очистка завершенных задач старше указанного времени.

        Args:
            max_age_hours: Максимальный возраст в часах
        """
        import datetime
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=max_age_hours)

        # Очистка завершенных задач
        to_remove = []
        for task_id, result in self.task_results.items():
            if "completed_at" in result:
                completed_at = datetime.datetime.fromisoformat(result["completed_at"])
                if completed_at < cutoff:
                    to_remove.append(task_id)

        for task_id in to_remove:
            self.current_tasks.pop(task_id, None)
            self.task_results.pop(task_id, None)

        if to_remove:
            self.logger.info(f"Cleaned up {len(to_remove)} completed tasks")

    def setup_exception_handlers(self):
        """Настройка глобальных обработчиков исключений."""

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": "HTTP_EXCEPTION",
                    "message": exc.detail,
                    "status_code": exc.status_code
                }
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            self.logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "details": str(exc) if self.config.get("development.debug_mode", False) else None
                }
            )

    def setup_middleware(self):
        """Настройка middleware для FastAPI."""
        # Получаем разрешенные origins из конфигурации
        allowed_origins = self.config.get("server.allowed_origins", ["http://localhost:3000"])

        # Настройка CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
        )

        # Настройка rate limiting
        limiter = Limiter(key_func=get_remote_address)
        self.app.state.limiter = limiter
        self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        self.app.add_middleware(SlowAPIMiddleware)

    def setup_routes(self):
        """Настройка маршрутов FastAPI."""
        security = HTTPBearer()

        async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
            """Получение текущего пользователя из токена."""
            token = credentials.credentials
            user = self.auth_manager.validate_token(token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid authentication token")
            return user

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            # Проверяем состояние компонентов
            components_status = {
                "auth_manager": "healthy",
                "resource_manager": "healthy",
                "cache_manager": "healthy",
                "metrics_manager": "healthy",
                "tools_manager": "healthy",
                "prompts_manager": "healthy"
            }

            # Проверяем компоненты на ошибки
            try:
                self.auth_manager.cleanup_expired_tokens()
            except Exception as e:
                components_status["auth_manager"] = f"error: {e}"
                self.logger.warning(f"Auth manager health check failed: {e}")

            try:
                cache_stats = self.cache_manager.get_stats()
            except Exception as e:
                components_status["cache_manager"] = f"error: {e}"
                self.logger.warning(f"Cache manager health check failed: {e}")

            # Определяем общий статус
            overall_status = "healthy" if all(
                status == "healthy" for status in components_status.values()
            ) else "degraded"

            return {
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "server": "Code Agent MCP Server",
                "version": "0.1.0",
                "active_connections": len(self.active_connections),
                "components": components_status,
                "tasks_context": len(self.current_tasks),
                "tasks_results": len(self.task_results)
            }

        @self.app.post("/auth/login", response_model=LoginResponse)
        async def login(request: Request, login_data: LoginRequest):
            """Эндпоинт для входа в систему."""
            # Rate limiting для входа
            limiter = getattr(request.app.state, 'limiter', None)
            if limiter:
                await limiter.limit("5/minute")(request)

            result = self.auth_manager.login(login_data.username, login_data.password)
            if not result:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            return LoginResponse(**result)

        @self.app.post("/auth/logout")
        async def logout(logout_data: LogoutRequest, current_user: User = Depends(get_current_user)):
            """Эндпоинт для выхода из системы."""
            success = self.auth_manager.logout(logout_data.token)
            return {"success": success, "message": "Logged out successfully"}

        @self.app.websocket("/mcp")
        async def mcp_websocket(websocket: WebSocket, token: str = None):
            """MCP WebSocket endpoint."""
            await websocket.accept()

            # Аутентификация
            if token and not await self.auth_manager.validate_token(token):
                await websocket.send_json({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,
                        "message": "Authentication failed"
                    }
                })
                await websocket.close()
                return

            connection_id = str(uuid.uuid4())
            self.active_connections[connection_id] = websocket

            try:
                while True:
                    data = await websocket.receive_text()
                    try:
                        request = MCPRequest.parse_raw(data)
                        response = await self.handle_request(request, connection_id)
                        if response:
                            await websocket.send_json(response.dict())
                    except Exception as e:
                        self.logger.error(f"Error handling request: {e}")
                        error_response = MCPResponse(
                            id=request.id if 'request' in locals() else None,
                            error={
                                "code": -32603,
                                "message": str(e)
                            }
                        )
                        await websocket.send_json(error_response.dict())

            except WebSocketDisconnect:
                self.logger.info(f"WebSocket disconnected: {connection_id}")
            finally:
                self.active_connections.pop(connection_id, None)

    def setup_request_handlers(self):
        """Настройка обработчиков MCP запросов."""
        self.request_handlers = {
            "initialize": self.handle_initialize,
            "resources/list": self.handle_resources_list,
            "resources/read": self.handle_resources_read,
            "resources/subscribe": self.handle_resources_subscribe,
            "tools/list": self.handle_tools_list,
            "tools/call": self.handle_tools_call,
            "prompts/list": self.handle_prompts_list,
            "prompts/get": self.handle_prompts_get,
        }

    async def handle_request(self, request: MCPRequest, connection_id: str) -> Optional[MCPResponse]:
        """Обработка MCP запроса."""
        self.metrics_manager.increment_counter("mcp_requests_total")

        handler = self.request_handlers.get(request.method)
        if not handler:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method '{request.method}' not found"
                }
            )

        try:
            result = await handler(request.params or {}, connection_id)
            return MCPResponse(id=request.id, result=result)
        except Exception as e:
            self.logger.error(f"Error in handler {request.method}: {e}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32603,
                    "message": str(e)
                }
            )

    async def handle_initialize(self, params: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
        """Обработка запроса инициализации."""
        self.logger.info(f"MCP Initialize from connection {connection_id}")

        return MCPInitializeResult(
            protocolVersion="2024-11-05",  # Текущая версия MCP протокола
            capabilities=MCPServerCapabilities(),
            serverInfo=MCPServerInfo(
                name="Code Agent MCP Server",
                version="0.1.0"
            )
        ).dict()

    async def handle_resources_list(self, params: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
        """Обработка запроса списка ресурсов."""
        resources = await self.resource_manager.list_resources()
        return {"resources": resources}

    async def handle_resources_read(self, params: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
        """Обработка запроса чтения ресурса."""
        uri = params.get("uri")
        if not uri:
            raise ValueError("URI parameter required")

        content = await self.resource_manager.read_resource(uri)
        return {"contents": [content]}

    async def handle_resources_subscribe(self, params: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
        """Обработка запроса подписки на ресурсы."""
        uri = params.get("uri")
        if not uri:
            raise ValueError("URI parameter required")

        # В будущем реализовать подписку на изменения
        return {}

    async def handle_tools_list(self, params: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
        """Обработка запроса списка инструментов."""
        tools = await self.tools_manager.list_tools()
        return {"tools": tools}

    async def handle_tools_call(self, params: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
        """Обработка вызова инструмента."""
        tool_name = params.get("name")
        tool_arguments = params.get("arguments", {})

        if not tool_name:
            raise ValueError("Tool name is required")

        result = await self.tools_manager.call_tool(tool_name, tool_arguments)

        return {
            "content": result.content,
            "isError": result.is_error
        }

    async def handle_prompts_list(self, params: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
        """Обработка запроса списка промптов."""
        prompts = await self.prompts_manager.list_prompts()
        return {"prompts": prompts}

    async def handle_prompts_get(self, params: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
        """Обработка запроса получения промпта."""
        prompt_name = params.get("name")
        prompt_arguments = params.get("arguments", {})

        if not prompt_name:
            raise ValueError("Prompt name is required")

        prompt_result = await self.prompts_manager.get_prompt(prompt_name, prompt_arguments)

        if not prompt_result:
            raise ValueError(f"Prompt '{prompt_name}' not found")

        return {
            "description": prompt_result.description,
            "messages": prompt_result.messages
        }

        # Новые endpoints для интеграции с основной системой

        @self.app.get("/tasks")
        async def get_tasks(current_user: User = Depends(get_current_user)):
            """Получение списка активных задач."""
            return {
                "tasks": self.get_all_tasks_context(),
                "count": len(self.current_tasks)
            }

        @self.app.get("/tasks/{task_id}")
        async def get_task(task_id: str, current_user: User = Depends(get_current_user)):
            """Получение контекста конкретной задачи."""
            task_context = self.get_task_context(task_id)
            if not task_context:
                raise HTTPException(status_code=404, detail="Task not found")

            return {"task": task_context}

        @self.app.post("/tasks/{task_id}/result")
        async def get_task_result_endpoint(task_id: str, current_user: User = Depends(get_current_user)):
            """Получение результата выполнения задачи."""
            task_result = self.get_task_result(task_id)
            if not task_result:
                raise HTTPException(status_code=404, detail="Task result not found")

            return {"result": task_result}

        @self.app.post("/tasks/{task_id}/update")
        async def update_task_context_endpoint(task_id: str, context: Dict[str, Any],
                                              current_user: User = Depends(get_current_user)):
            """Обновление контекста задачи (для внутренней интеграции)."""
            # Проверка прав (только admin может обновлять контекст)
            if current_user.role != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")

            self.update_task_context(task_id, context)
            return {"status": "updated", "task_id": task_id}

        @self.app.delete("/tasks/completed")
        async def cleanup_tasks_endpoint(current_user: User = Depends(get_current_user)):
            """Очистка завершенных задач."""
            if current_user.role != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")

            self.cleanup_completed_tasks()
            return {"status": "cleaned"}

    async def broadcast_notification(self, notification: MCPNotification):
        """Отправка уведомления всем активным соединениям."""
        for connection in self.active_connections.values():
            try:
                await connection.send_json(notification.dict())
            except Exception as e:
                self.logger.error(f"Error sending notification: {e}")

    async def start_server(self, host: str = "localhost", port: int = 3000):
        """Запуск MCP сервера с graceful shutdown."""
        self.logger.info(f"Starting MCP Server on {host}:{port}")

        # Настройка сигналов для graceful shutdown
        import signal
        import asyncio
        from contextlib import asynccontextmanager

        shutdown_event = asyncio.Event()

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            shutdown_event.set()

        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)

        try:
            # Создаем задачу для сервера
            server_task = asyncio.create_task(server.serve())

            # Создаем задачу для ожидания shutdown сигнала
            shutdown_task = asyncio.create_task(shutdown_event.wait())

            # Ждем завершения любой из задач
            done, pending = await asyncio.wait(
                [server_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Отменяем pending задачи
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Если завершилась задача сервера с исключением, пробрасываем его
            if server_task in done and not server_task.cancelled():
                try:
                    await server_task
                except Exception as e:
                    self.logger.error(f"MCP server error: {e}")
                    raise

        except Exception as e:
            self.logger.error(f"Failed to start MCP server: {e}")
            raise
        finally:
            # Graceful shutdown
            self.logger.info("MCP Server shutting down...")
            await server.shutdown()

            # Очищаем ресурсы
            self.active_connections.clear()
            self.request_handlers.clear()

            # Очищаем истекшие токены
            self.auth_manager.cleanup_expired_tokens()

            self.logger.info("MCP Server shutdown complete")

    def run_server(self, host: str = "localhost", port: int = 3000):
        """Запуск сервера в синхронном режиме."""
        asyncio.run(self.start_server(host, port))