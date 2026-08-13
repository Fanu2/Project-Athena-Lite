"""
Tests for database operations.
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.database import create_database, Database, document_row_to_domain, chunk_row_to_domain
from app.models.document import Document as DomainDocument
from app.models.document import Document, Chunk, Conversation, Message, SourceCitation
from app.models.document import Document as DomainDocument
from app.models.document import Conversation as DomainConversation, Message as DomainMessage


class TestDatabaseOperations:
    """Tests for database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        create_database(db_path)
        db = Database(db_path)
        yield db, temp_dir
        shutil.rmtree(temp_dir)

    def test_create_database(self, temp_db):
        """Test database creation."""
        db, _ = temp_db
        conn = db.get_connection()
        assert conn is not None
        conn.close()

    def test_document_crud(self, temp_db):
        """Test document CRUD operations."""
        db, _ = temp_db
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            now = "2024-01-01T00:00:00"

            # Create
            cursor.execute("""
                INSERT INTO documents (filename, original_filename, file_path, file_size, file_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test.pdf", "original.pdf", "/path/test.pdf", 1024, "pdf", now, now))
            conn.commit()

            cursor.execute("SELECT * FROM documents WHERE filename = ?", ("test.pdf",))
            doc = cursor.fetchone()
            assert doc is not None
            assert doc["filename"] == "test.pdf"

            # Read
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc["id"],))
            found = cursor.fetchone()
            assert found is not None
            assert found["filename"] == "test.pdf"

            # Update
            cursor.execute("UPDATE documents SET filename = ? WHERE id = ?", ("updated.pdf", doc["id"]))
            conn.commit()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc["id"],))
            updated = cursor.fetchone()
            assert updated["filename"] == "updated.pdf"

            # Delete
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc["id"],))
            conn.commit()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc["id"],))
            deleted = cursor.fetchone()
            assert deleted is None
        finally:
            conn.close()

    def test_chunk_crud(self, temp_db):
        """Test chunk CRUD operations."""
        db, _ = temp_db
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            now = "2024-01-01T00:00:00"

            # Create document first
            cursor.execute("""
                INSERT INTO documents (filename, original_filename, file_path, file_size, file_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test.pdf", "test.pdf", "/path/test.pdf", 1024, "pdf", now, now))
            conn.commit()
            doc_id = cursor.lastrowid

            # Create chunks
            import json
            emb = json.dumps([0.1] * 768)

            cursor.execute("""
                INSERT INTO chunks (document_id, chunk_index, text, embedding, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (doc_id, 0, "First chunk text", emb, now))

            cursor.execute("""
                INSERT INTO chunks (document_id, chunk_index, text, embedding, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (doc_id, 1, "Second chunk text", emb, now))
            conn.commit()

            # Read
            cursor.execute("SELECT * FROM chunks WHERE document_id = ?", (doc_id,))
            chunks = cursor.fetchall()
            assert len(chunks) == 2

            # Delete
            cursor.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            conn.commit()
            cursor.execute("SELECT * FROM chunks WHERE document_id = ?", (doc_id,))
            remaining = cursor.fetchall()
            assert len(remaining) == 0
        finally:
            conn.close()

    def test_conversation_crud(self, temp_db):
        """Test conversation CRUD operations."""
        db, _ = temp_db
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            now = "2024-01-01T00:00:00"

            # Create conversation
            cursor.execute("""
                INSERT INTO conversations (title, created_at, updated_at)
                VALUES (?, ?, ?)
            """, ("Test Conversation", now, now))
            conn.commit()
            conv_id = cursor.lastrowid

            # Create messages
            cursor.execute("""
                INSERT INTO messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
            """, (conv_id, "user", "Hello?", now))

            cursor.execute("""
                INSERT INTO messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
            """, (conv_id, "assistant", "Hi there!", now))
            conn.commit()

            # Read messages
            cursor.execute("SELECT * FROM messages WHERE conversation_id = ?", (conv_id,))
            messages = cursor.fetchall()
            assert len(messages) == 2

            # Delete conversation (cascade should delete messages)
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()
            cursor.execute("SELECT * FROM messages WHERE conversation_id = ?", (conv_id,))
            messages_after = cursor.fetchall()
            assert len(messages_after) == 0
        finally:
            conn.close()


class TestDatabaseQueries:
    """Tests for database queries."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        create_database(db_path)
        db = Database(db_path)
        yield db, temp_dir
        shutil.rmtree(temp_dir)

    def test_search_documents_by_name(self, temp_db):
        """Test searching documents by name."""
        db, _ = temp_db
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            now = "2024-01-01T00:00:00"

            cursor.execute("""
                INSERT INTO documents (filename, original_filename, file_path, file_size, file_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("doc1.pdf", "document_one.pdf", "/p1", 100, "pdf", now, now))

            cursor.execute("""
                INSERT INTO documents (filename, original_filename, file_path, file_size, file_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("doc2.pdf", "document_two.pdf", "/p2", 200, "pdf", now, now))
            conn.commit()

            cursor.execute("SELECT * FROM documents WHERE original_filename LIKE ?", ("%document%",))
            results = cursor.fetchall()
            assert len(results) == 2
        finally:
            conn.close()

    def test_get_document_chunks(self, temp_db):
        """Test getting chunks for a document."""
        db, _ = temp_db
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            now = "2024-01-01T00:00:00"

            # Create document
            cursor.execute("""
                INSERT INTO documents (filename, original_filename, file_path, file_size, file_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test.pdf", "test.pdf", "/test", 1024, "pdf", now, now))
            conn.commit()
            doc_id = cursor.lastrowid

            import json
            emb = json.dumps([0.1] * 768)

            for i in range(5):
                cursor.execute("""
                    INSERT INTO chunks (document_id, chunk_index, text, embedding, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (doc_id, i, f"Chunk {i} text", emb, now))
            conn.commit()

            cursor.execute("SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index", (doc_id,))
            chunks = cursor.fetchall()

            assert len(chunks) == 5
            assert chunks[0]["chunk_index"] == 0
            assert chunks[4]["chunk_index"] == 4
        finally:
            conn.close()


class TestModelConversions:
    """Tests for database model conversions."""

    def test_document_row_to_domain(self):
        """Test converting database row to domain Document."""
        row = {
            "id": 1,
            "filename": "test.pdf",
            "original_filename": "original.pdf",
            "file_path": "/path/test.pdf",
            "file_size": 1024,
            "file_type": "pdf",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        doc = document_row_to_domain(row)
        assert isinstance(doc, DomainDocument)
        assert doc.id == 1
        assert doc.filename == "test.pdf"
        assert doc.original_filename == "original.pdf"
        assert doc.file_size == 1024
        assert doc.file_type == "pdf"
        assert doc.file_path == "/path/test.pdf"

    def test_chunk_row_to_domain(self):
        """Test converting database row to domain Chunk."""
        import json
        row = {
            "id": 1,
            "document_id": 1,
            "chunk_index": 0,
            "text": "Test chunk text",
            "embedding": json.dumps([0.1] * 768),
            "created_at": "2024-01-01T00:00:00",
        }

        chunk = chunk_row_to_domain(row)
        from app.models.document import Chunk as DomainChunk
        assert isinstance(chunk, DomainChunk)
        assert chunk.id == 1
        assert chunk.document_id == 1
        assert chunk.chunk_index == 0
        assert chunk.text == "Test chunk text"
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 768
