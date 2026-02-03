
from typing import Dict, Type, Callable, Any

class BaseError(Exception):
    """Base class for custom errors."""
    def __init__(self, message: str = "An unexpected error occurred"):
        self.message = message
        super().__init__(self.message)

class NetworkError(BaseError):
    """Error specific to network issues."""
    def __init__(self, message: str = "Network connection failed"):
        super().__init__(message)

class DatabaseError(BaseError):
    """Error specific to database operations."""
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message)

class ConfigError(BaseError):
    """Error specific to configuration issues."""
    def __init__(self, message: str = "Configuration error"):
        super().__init__(message)

class ErrorHandler:
    """
    Handles errors with specific recovery strategies.
    """
    def __init__(self):
        self._recovery_strategies: Dict[Type[BaseError], Callable[..., Any]] = {}

    def register_strategy(self, error_type: Type[BaseError], strategy: Callable[..., Any]):
        """
        Registers a recovery strategy for a given error type.
        """
        self._recovery_strategies[error_type] = strategy

    def handle_error(self, error: BaseError, *args, **kwargs) -> Any:
        """
        Handles an error by executing its registered recovery strategy.
        If no specific strategy is found, a default handling mechanism is used.
        """
        strategy = self._recovery_strategies.get(type(error))
        if strategy:
            print(f"Handling error: {error.message} with specific strategy.")
            return strategy(error, *args, **kwargs)
        else:
            print(f"Handling error: {error.message} with default strategy.")
            return self._default_recovery(error, *args, **kwargs)

    def _default_recovery(self, error: BaseError, *args, **kwargs) -> Any:
        """
        Default recovery strategy if no specific one is registered.
        This can include logging the error, retrying, or raising it again.
        """
        print(f"Default recovery for error: {error.message}. Logging and re-raising.")
        # In a real application, this would involve detailed logging
        raise error # Re-raise after logging, or perform other default actions

# Example Recovery Strategies
def retry_strategy(error: BaseError, retries: int = 3, delay: int = 1, **kwargs):
    """
    A simple retry strategy.
    """
    print(f"Attempting retry for {error.message}. Retries left: {retries}")
    if retries > 0:
        # In a real scenario, you'd re-attempt the failed operation here
        print(f"Simulating retry after {delay} seconds...")
        # time.sleep(delay) # Uncomment for actual delay
        return {"status": "retrying", "retries_left": retries - 1}
    else:
        print(f"Max retries reached for {error.message}. Failing.")
        raise error

def fallback_strategy(error: BaseError, fallback_data: Any = None, **kwargs):
    """
    A fallback strategy that returns default data or a safe state.
    """
    print(f"Executing fallback strategy for {error.message}.")
    return {"status": "fallback_data", "data": fallback_data}

def notify_admin_strategy(error: BaseError, admin_email: str = "admin@example.com", **kwargs):
    """
    A strategy to notify an administrator about a critical error.
    """
    print(f"Notifying admin ({admin_email}) about critical error: {error.message}.")
    # In a real application, this would send an email or an alert
    return {"status": "admin_notified", "email": admin_email}

if __name__ == "__main__":
    handler = ErrorHandler()

    # Registering strategies
    handler.register_strategy(NetworkError, retry_strategy)
    handler.register_strategy(DatabaseError, notify_admin_strategy)

    print("\n--- Testing NetworkError with retry strategy ---")
    try:
        # Simulate an operation that might raise a NetworkError
        raise NetworkError("Failed to connect to the API server")
    except BaseError as e:
        # We can pass additional arguments to the strategy if needed
        result = handler.handle_error(e, retries=2)
        print(f"Handler result: {result}")
        try:
            # Simulate another retry failure
            if result and result.get("status") == "retrying" and result.get("retries_left") == 1:
                raise NetworkError("Still failing to connect after retry")
        except BaseError as e_inner:
            result_inner = handler.handle_error(e_inner, retries=1)
            print(f"Handler result after second retry: {result_inner}")
            try:
                # Final retry failure, should re-raise
                if result_inner and result_inner.get("status") == "retrying" and result_inner.get("retries_left") == 0:
                    raise NetworkError("Final connection attempt failed")
            except BaseError as e_final:
                print("Expect this to re-raise:")
                try:
                    handler.handle_error(e_final, retries=0)
                except BaseError as re_raised_error:
                    print(f"Caught re-raised error: {re_raised_error.message}")

    print("\n--- Testing DatabaseError with notify admin strategy ---")
    try:
        # Simulate a critical database error
        raise DatabaseError("Could not write to the primary database")
    except BaseError as e:
        result = handler.handle_error(e, admin_email="devops@example.com")
        print(f"Handler result: {result}")

    print("\n--- Testing ConfigError with default strategy (no specific registration) ---")
    try:
        # Simulate a configuration error (no specific strategy registered)
        raise ConfigError("Missing API key in environment variables")
    except BaseError as e:
        print("Expect this to be handled by default and re-raise:")
        try:
            handler.handle_error(e)
        except BaseError as re_raised_error:
            print(f"Caught re-raised error: {re_raised_error.message}")

    print("\n--- Testing with an unknown error type and default strategy ---")
    class UnknownError(BaseError):
        pass

    try:
        raise UnknownError("Something truly unexpected happened")
    except BaseError as e:
        print("Expect this to be handled by default and re-raise:")
        try:
            handler.handle_error(e)
        except BaseError as re_raised_error:
            print(f"Caught re-raised error: {re_raised_error.message}")
