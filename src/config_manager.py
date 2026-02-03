import yaml
import os

class ConfigurationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigurationManager, cls).__new__(cls)
            cls._instance._config = {}
        return cls._instance

    def load_config(self, config_path: str):
        if not os.path.exists(config_path):
            print(f"Warning: Configuration file not found at {config_path}")
            return

        try:
            with open(config_path, 'r') as f:
                self._config.update(yaml.safe_load(f))
            print(f"Configuration loaded successfully from {config_path}")
        except yaml.YAMLError as e:
            print(f"Error loading configuration from {config_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while loading configuration from {config_path}: {e}")

    def get(self, key: str, default=None):
        keys = key.split('.')
        val = self._config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def __str__(self):
        return f"ConfigurationManager current config: {self._config}"
