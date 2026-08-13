"""
SQLAlchemy database models for Local AI Document Assistant.
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, ForeignKey, LargeBinary
)
from sqlalchemy.orm import declarative_base, relationship, Session

Base = declarative_base()


class DocumentModel(Base):
    """SQLAlchemy model for documents."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    chunks = relationship("ChunkModel", back_populates="document", cascade="all, delete-orphan")
    citations = relationship("SourceCitationModel", back_populates="document")

    def to_doc(self) -> "Document":
        from app.models.document import Document
        return Document(
            id=self.id,
            filename=self.filename,
            original_filename=self.original_filename,
            file_path=self.file_path,
            file_size=self.file_size,
            file_type=self.file_type,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class ChunkModel(Base):
    """SQLAlchemy model for document chunks."""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(LargeBinary, nullable=True)  # Store as BLOB
    created_at = Column(DateTime, default=datetime.now)

    document = relationship("DocumentModel", back_populates="chunks")

    def to_chunk(self) -> "Chunk":
        from app.models.document import Chunk
        return Chunk(
            id=self.id,
            document_id=self.document_id,
            chunk_index=self.chunk_index,
            text=self.text,
            embedding=self.embedding,
            created_at=self.created_at,
        )


class ConversationModel(Base):
    """SQLAlchemy model for conversations."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")

    def to_conversation(self) -> "Conversation":
        from app.models.conversation import Conversation
        return Conversation(
            id=self.id,
            title=self.title,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class MessageModel(Base):
    """SQLAlchemy model for conversation messages."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    conversation = relationship("ConversationModel", back_populates="messages")
    citations = relationship("SourceCitationModel", back_populates="message", cascade="all, delete-orphan")

    def to_message(self) -> "Message":
        from app.models.conversation import Message
        return Message(
            id=self.id,
            conversation_id=self.conversation_id,
            role=self.role,
            content=self.content,
            tokens_used=self.tokens_used,
            created_at=self.created_at,
        )


class SourceCitationModel(Base):
    """SQLAlchemy model for source citations."""
    __tablename__ = "source_citations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    text_preview = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    message = relationship("MessageModel", back_populates="citations")
    document = relationship("DocumentModel", back_populates="citations")

    def to_source_citation(self) -> "SourceCitation":
        from app.models.document import SourceCitation
        return SourceCitation(
            id=self.id,
            message_id=self.message_id,
            document_id=self.document_id,
            chunk_index=self.chunk_index,
            score=self.score,
            text_preview=self.text_preview,
            page_number=self.page_number,
        )


class SettingModel(Base):
    """SQLAlchemy model for application settings."""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(200), nullable=False, unique=True)
    value = Column(Text, nullable=False)


def create_database(db_path: str) -> None:
    """Create database and tables."""
    from sqlalchemy import create_engine
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    logger.info(f"Database created at {db_path}")


def get_engine(db_path: str):
    """Get SQLAlchemy engine."""
    from sqlalchemy import create_engine
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session_factory(db_path: str):
    """Get session factory."""
    from sqlalchemy.orm import sessionmaker
    engine = get_engine(db_path)
    return sessionmaker(bind=engine)


def get_session(db_path: str) -> Session:
    """Get a database session."""
    factory = get_session_factory(db_path)
    return factory()


# Import models at bottom to avoid circular imports
from app.models.document import Document, Chunk, SourceCitation
from app.models.conversation import Conversation, Message
