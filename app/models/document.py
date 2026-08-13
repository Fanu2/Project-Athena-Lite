"""
Model classes for Local AI Document Assistant.
Using plain dataclasses for simplicity.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any


@dataclass
class Document:
    """Represents a document in the system."""
    id: int = 0
    filename: str = ""
    original_filename: str = ""
    file_path: str = ""
    file_size: int = 0
    file_type: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def size_display(self) -> str:
        """Human-readable file size."""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"


@dataclass
class Chunk:
    """Represents a text chunk from a document."""
    id: int = 0
    document_id: int = 0
    chunk_index: int = 0
    text: str = ""
    embedding: Optional[List[float]] = None
    page_number: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def preview(self) -> str:
        """Short preview of the chunk text."""
        if len(self.text) > 100:
            return self.text[:100] + "..."
        return self.text


@dataclass
class Conversation:
    """Represents a chat conversation."""
    id: int = 0
    title: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def message_count(self) -> int:
        """Number of messages in this conversation."""
        return 0  # Would need to query database


@dataclass
class Message:
    """Represents a message in a conversation."""
    id: int = 0
    conversation_id: int = 0
    role: str = ""  # "user" or "assistant"
    content: str = ""
    tokens_used: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SourceCitation:
    """Represents a source citation for an answer."""
    id: int = 0
    message_id: int = 0
    document_id: int = 0
    chunk_index: int = 0
    score: float = 0.0
    text_preview: str = ""
    page_number: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
