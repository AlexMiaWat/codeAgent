# ConfigurationManager Component

## Overview
The `ConfigurationManager` is a singleton class responsible for loading and managing application configurations from YAML files. It provides a centralized way to access configuration parameters throughout the application.

## Features
- **Singleton Pattern**: Ensures only one instance of the ConfigurationManager exists.
- **YAML Configuration**: Supports loading configurations from YAML files.
- **Hierarchical Access**: Allows accessing configuration parameters using dot notation (e.g., `manager.get('database.host')`).
- **Default Values**: Provides an option to return a default value if a key is not found.
- **Error Handling**: Gracefully handles cases where the configuration file is not found or is malformed.

## Usage
### Initialization
The `ConfigurationManager` is a singleton, so you can get the instance directly:
```python
from src.config_manager import ConfigurationManager

config_manager = ConfigurationManager()
```

### Loading Configuration
Load a configuration file:
```python
config_manager.load_config('path/to/your/config.yaml')
```

### Accessing Configuration Values
Access values using the `get` method:
```python
database_host = config_manager.get('database.host', 'localhost')
port = config_manager.get('server.port', 8080)
```
