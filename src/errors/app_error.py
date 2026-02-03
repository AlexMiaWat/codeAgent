class AppError(Exception):
    """Base exception for application-specific errors."""

    def __init__(self, code: str, message: str, context: dict = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context if context is not None else {}

    def __str__(self):
        return f"[{self.code}] {self.message} - Context: {self.context}"
