"""
Tests for chat service / RAG.
"""

import sys
import os
import tempfile
import shutil
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from app.config import AppConfig
from app.database import Database, create_database
from app.ai.ollama_client import OllamaClient, MockEmbeddingProvider, EmbeddingProvider
from app.services.chat_service import ChatService
from app.services.indexing_service import RetrievalService


class TestChatService:
    """Tests for the chat service."""

    @pytest.fixture
    def setup(self):
        """Setup test database and services."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        config = AppConfig()
        config.set("database_path", db_path)
        config.set("chunk_size", 200)
        config.set("chunk_overlap", 20)
        config.set("retrieval_count", 3)

        create_database(db_path)
        db = Database(db_path)

        class MockOllamaClient:
            def generate_embedding(self, model, text):
                return [0.1] * 768

            def chat(self, model, messages, stream=False, options=None):
                return {"response": "This is a mock response about apples and oranges."}

            def is_available(self):
                return True

        ollama_client = MockOllamaClient()

        retrieval_service = RetrievalService(
            db,
            ollama_client,
            config,
        )

        chat_service = ChatService(
            db,
            ollama_client,
            retrieval_service,
            config,
        )

        yield {
            "db": db,
            "config": config,
            "chat_service": chat_service,
            "retrieval_service": retrieval_service,
            "temp_dir": temp_dir,
        }

        shutil.rmtree(temp_dir)

    def test_create_conversation(self, setup):
        """Test conversation creation."""
        chat_service = setup["chat_service"]

        conv_id = chat_service.create_new_conversation("Test Chat")

        assert conv_id is not None

        conversations = chat_service.list_conversations()
        assert len(conversations) == 1
        assert conversations[0]["title"] == "Test Chat"

    def test_add_message(self, setup):
        """Test adding messages to conversation."""
        chat_service = setup["chat_service"]

        conv_id = chat_service.create_new_conversation("Test Chat")
        msg_id = chat_service._add_conversation_message(
            conv_id, "user", "Hello?"
        )

        assert msg_id is not None

        messages = chat_service.get_conversation_history(conv_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello?"

    def test_ask_question(self, setup):
        """Test question answering."""
        temp_dir = setup["temp_dir"]
        db = setup["db"]
        chat_service = setup["chat_service"]

        from app.models import Document, Chunk

        # Create document
        doc = Document(
            id=1,
            filename="fruits.pdf",
            original_filename="fruits.pdf",
            file_path=os.path.join(temp_dir, "fruits.pdf"),
            file_size=100,
            file_type="pdf",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Create chunks about fruits
        emb = [0.1] * 768

        chunk1 = Chunk(
            id=1,
            document_id=doc.id,
            chunk_index=0,
            text="Apples are red fruits that grow on trees.",
            embedding=emb,
            created_at=datetime.now(),
        )
        chunk2 = Chunk(
            id=2,
            document_id=doc.id,
            chunk_index=1,
            text="Oranges are citrus fruits that are rich in vitamin C.",
            embedding=emb,
            created_at=datetime.now(),
        )

        # Store in database
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            emb_json = json.dumps(emb)

            cursor.execute("INSERT INTO documents (id, filename, original_filename, file_path, file_size, file_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (doc.id, doc.filename, doc.original_filename, doc.file_path, doc.file_size, doc.file_type,
                 doc.created_at.isoformat(), doc.updated_at.isoformat()))

            cursor.execute("INSERT INTO chunks (id, document_id, chunk_index, text, embedding, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (chunk1.id, chunk1.document_id, chunk1.chunk_index, chunk1.text, emb_json, chunk1.created_at.isoformat()))

            cursor.execute("INSERT INTO chunks (id, document_id, chunk_index, text, embedding, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (chunk2.id, chunk2.document_id, chunk2.chunk_index, chunk2.text, emb_json, chunk2.created_at.isoformat()))

            conn.commit()
        finally:
            conn.close()

        # Ask question
        result = chat_service.answer(
            question="What fruits are mentioned?",
        )

        assert "answer" in result
        assert "sources" in result
        assert len(result["sources"]) >= 1

        source = result["sources"][0]
        assert "document_name" in source
        assert "score" in source
        assert "text_preview" in source

    def test_ask_question_no_documents(self, setup):
        """Test question when no documents exist."""
        chat_service = setup["chat_service"]

        result = chat_service.answer(question="What is in my documents?")

        assert "answer" in result
        # Should return a message about no documents
        assert "indexed documents" in result["answer"].lower() or \
               "no documents" in result["answer"].lower()

    def test_delete_conversation(self, setup):
        """Test conversation deletion."""
        chat_service = setup["chat_service"]

        conv_id = chat_service.create_new_conversation("To Delete")

        # Verify it exists
        conversations = chat_service.list_conversations()
        assert len(conversations) == 1

        # Delete it
        conn = chat_service.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()
        finally:
            conn.close()

        # Verify it's gone
        conversations = chat_service.list_conversations()
        assert len(conversations) == 0


class TestChatServiceWithoutOllama:
    """Tests for chat service without Ollama."""

    @pytest.fixture
    def setup(self):
        """Setup test database and services with no Ollama."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        config = AppConfig()
        config.set("database_path", db_path)
        config.set("chunk_size", 200)
        config.set("chunk_overlap", 20)
        config.set("retrieval_count", 3)

        create_database(db_path)
        db = Database(db_path)

        retrieval_service = RetrievalService(
            db,
            MockEmbeddingProvider(768),
            config,
        )

        chat_service = ChatService(
            db,
            MockEmbeddingProvider(768),
            retrieval_service,
            config,
        )

        yield {
            "db": db,
            "config": config,
            "chat_service": chat_service,
            "retrieval_service": retrieval_service,
            "temp_dir": temp_dir,
        }

        shutil.rmtree(temp_dir)

    def test_answer_without_ollama(self, setup):
        """Test that answer works even without Ollama."""
        chat_service = setup["chat_service"]

        result = chat_service.answer(question="What is in my documents?")

        assert "answer" in result
        # Should have a fallback response
        assert len(result["answer"]) > 0
