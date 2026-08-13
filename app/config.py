"""
Application settings module.
Loads configuration from config file and environment variables.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AppConfig:
    """Application configuration manager."""

    DEFAULT_CONFIG_DIR = Path.home() / ".local_ai_assistant"
    DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
    DEFAULT_DB_PATH = DEFAULT_CONFIG_DIR / "assistant.db"
    DEFAULT_DOCUMENTS_DIR = DEFAULT_CONFIG_DIR / "documents"

    def __init__(self, config_file: Optional[Path] = None):
        self._config_file = config_file or self.DEFAULT_CONFIG_FILE
        self._config: dict = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from file."""
        if self._config_file.exists():
            try:
                with open(self._config_file, "r") as f:
                    self._config = json.load(f)
                logger.info(f"Loaded config from {self._config_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load config: {e}")
                self._config = {}
        else:
            logger.info("No config file found, using defaults")

        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        if os.environ.get("OLLAMA_BASE_URL"):
            self._config["ollama_base_url"] = os.environ["OLLAMA_BASE_URL"]
        if os.environ.get("OLLAMA_MODEL"):
            self._config["ollama_model"] = os.environ["OLLAMA_MODEL"]
        if os.environ.get("EMBEDDING_MODEL"):
            self._config["embedding_model"] = os.environ["EMBEDDING_MODEL"]
        if os.environ.get("DATABASE_PATH"):
            self._config["database_path"] = os.environ["DATABASE_PATH"]

    def save(self) -> None:
        """Save configuration to file."""
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._config_file, "w") as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Saved config to {self._config_file}")
        except IOError as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key: str, default: any = None) -> any:
        """Get a configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value: any) -> None:
        """Set a configuration value and save."""
        self._config[key] = value
        self.save()

    @property
    def ollama_base_url(self) -> str:
        """Get the Ollama API base URL."""
        return self.get("ollama_base_url", "http://localhost:11434")

    @property
    def ollama_model(self) -> str:
        """Get the default Ollama model."""
        return self.get("ollama_model", "qwen2.5:1.5b")

    @property
    def embedding_model(self) -> str:
        """Get the embedding model name."""
        return self.get("embedding_model", "nomic-embed-text:latest")

    @property
    def model_temperature(self) -> float:
        """Get the model temperature."""
        return float(self.get("model_temperature", 0.0))

    @property
    def database_path(self) -> str:
        """Get the database file path."""
        return str(self.get("database_path", self.DEFAULT_DB_PATH))

    @property
    def documents_dir(self) -> Path:
        """Get the documents directory."""
        return Path(self.get("documents_dir", self.DEFAULT_DOCUMENTS_DIR))

    @property
    def chunk_size(self) -> int:
        """Get the chunk size in characters."""
        return int(self.get("chunk_size", 500))

    @property
    def chunk_overlap(self) -> int:
        """Get the chunk overlap in characters."""
        return int(self.get("chunk_overlap", 50))

    @property
    def retrieval_count(self) -> int:
        """Get the maximum number of chunks to retrieve per query."""
        return int(self.get("retrieval_count", 5))

    @property
    def max_context_length(self) -> int:
        """Get the maximum context length for LLM."""
        return int(self.get("max_context_length", 8000))

    def to_dict(self) -> dict:
        """Export configuration as dictionary."""
        return {
            "ollama_base_url": self.ollama_base_url,
            "ollama_model": self.ollama_model,
            "embedding_model": self.embedding_model,
            "model_temperature": self.model_temperature,
            "database_path": self.database_path,
            "documents_dir": str(self.documents_dir),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "retrieval_count": self.retrieval_count,
            "max_context_length": self.max_context_length,
        }
