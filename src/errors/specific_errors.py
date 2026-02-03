from src.errors.app_error import AppError

class NetworkError(AppError):
    """Represents an error related to network operations."""
    def __init__(self, message: str = "Network error occurred", code: str = "NETWORK_ERROR", context: dict = None):
        super().__init__(message, code, context)

class ConfigurationError(AppError):
    """Represents an error related to application configuration."""
    def __init__(self, message: str = "Configuration error occurred", code: str = "CONFIGURATION_ERROR", context: dict = None):
        super().__init__(message, code, context)

class InvalidInputError(AppError):
    """Represents an error due to invalid input data."""
    def __init__(self, message: str = "Invalid input provided", code: str = "INVALID_INPUT_ERROR", context: dict = None):
        super().__init__(message, code, context)

class DatabaseError(AppError):
    """Represents an error related to database operations."""
    def __init__(self, message: str = "Database error occurred", code: str = "DATABASE_ERROR", context: dict = None):
        super().__init__(message, code, context)
