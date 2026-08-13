"""
Main entry point - Local AI Document Assistant.
"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.config import AppConfig
from app.database import Database, create_database
from app.ui.main_window import MainWindow


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize and run the application."""
    logger.info("Starting Local AI Document Assistant")

    config = AppConfig()

    try:
        create_database(config.database_path)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        print(f"Error: Failed to create database at {config.database_path}")
        print("Please ensure the directory is writable.")
        sys.exit(1)

    db = Database(config.database_path)
    logger.info(f"Database ready at {config.database_path}")

    db_dir = Path(config.documents_dir)
    db_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Documents directory: {db_dir}")

    app = QApplication(sys.argv)

    from app.ai.ollama_client import OllamaClient, EmbeddingProvider, MockEmbeddingProvider

    ollama_client = OllamaClient(config.ollama_base_url)
    if ollama_client.is_available():
        logger.info(f"Connected to Ollama at {config.ollama_base_url}")
        llm_client = ollama_client
        embedding_provider = EmbeddingProvider(ollama_client, config.embedding_model)
    else:
        logger.warning("Ollama not available, using mock services")
        llm_client = None
        embedding_provider = MockEmbeddingProvider(768)

    try:
        window = MainWindow(app, config, db, llm_client, embedding_provider)
        window.show()
        logger.info("Application window opened")
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Failed to create application window: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
