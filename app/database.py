"""
Database module using plain SQLite (no SQLAlchemy dependency).
Tables: documents, chunks, conversations, messages, source_citations, settings
Uses sqlite3 which is part of Python standard library.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


def dict_factory(cursor, row):
    """Convert SQLite row to dict."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class Database:
    """Database manager using SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_directory()
        self._initialize_tables()

    def _ensure_directory(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _initialize_tables(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tokens_used INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS source_citations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    score REAL NOT NULL,
                    text_preview TEXT,
                    page_number INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL
                )
            """)

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def create_database(db_path: str):
    """Create database and tables."""
    Database(db_path)


# Model conversion helpers (used by tests)
def document_row_to_domain(row: dict):
    """Convert database row to domain Document."""
    from app.models.document import Document as DomainDocument
    return DomainDocument(
        id=row["id"],
        filename=row["filename"],
        original_filename=row["original_filename"],
        file_path=row["file_path"],
        file_size=row["file_size"],
        file_type=row["file_type"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def chunk_row_to_domain(row: dict):
    """Convert database row to domain Chunk."""
    from app.models.document import Chunk as DomainChunk
    embedding = None
    if row.get("embedding"):
        try:
            embedding = json.loads(row["embedding"])
        except:
            pass
    return DomainChunk(
        id=row["id"],
        document_id=row["document_id"],
        chunk_index=row["chunk_index"],
        text=row["text"],
        embedding=embedding,
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def conversation_row_to_domain(row: dict):
    """Convert database row to domain Conversation."""
    from app.models.conversation import Conversation as DomainConversation
    return DomainConversation(
        id=row["id"],
        title=row["title"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def message_row_to_domain(row: dict):
    """Convert database row to domain Message."""
    from app.models.conversation import Message as DomainMessage
    return DomainMessage(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=row["role"],
        content=row["content"],
        tokens_used=row.get("tokens_used"),
        created_at=datetime.fromisoformat(row["created_at"]),
    )
