"""
Tests for indexing service.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.config import AppConfig
from app.database import Database, create_database
from app.services.indexing_service import IndexingService, RetrievalService


class TestIndexingService:
    """Tests for the indexing service."""

    @pytest.fixture
    def setup(self):
        """Setup test database and services."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        config = AppConfig()
        config.set("database_path", db_path)
        config.set("chunk_size", 200)
        config.set("chunk_overlap", 20)

        create_database(db_path)
        db = Database(db_path)

        class MockOllamaClient:
            def generate_embedding(self, model, text):
                return [0.1] * 768

        ollama_client = MockOllamaClient()

        indexing_service = IndexingService(
            db,
            ollama_client,
            config,
        )

        yield {
            "db": db,
            "config": config,
            "indexing_service": indexing_service,
            "temp_dir": temp_dir,
        }

        shutil.rmtree(temp_dir)

    def test_chunk_splitting(self, setup):
        """Test that text is split into chunks correctly."""
        indexing_service = setup["indexing_service"]

        from app.models.document import Document as DomainDocument, Chunk as DomainChunk
        from datetime import datetime

        doc = DomainDocument(
            id=1,
            filename="test.txt",
            original_filename="test.txt",
            file_path="/fake/path/test.txt",
            file_size=100,
            file_type="txt",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        text = "This is sentence one. This is sentence two. This is sentence three."

        chunks = indexing_service._create_chunks(doc, text)

        assert len(chunks) >= 1
        assert all(len(c.text) > 0 for c in chunks)

    def test_embedding_generation(self, setup):
        """Test embedding generation."""
        indexing_service = setup["indexing_service"]
        from app.ai.ollama_client import MockEmbeddingProvider
        indexing_service.embedding_provider = MockEmbeddingProvider(768)

        embeddings = indexing_service._generate_embeddings(["test text"])

        assert len(embeddings) == 1
        assert len(embeddings[0]) == 768

    def test_index_document_workflow(self, setup):
        """Test full document indexing workflow."""
        temp_dir = setup["temp_dir"]
        db = setup["db"]
        indexing_service = setup["indexing_service"]

        from app.models.document import Document as DomainDocument
        from datetime import datetime

        doc = DomainDocument(
            id=1,
            filename="test.txt",
            original_filename="test.txt",
            file_path=os.path.join(temp_dir, "test.txt"),
            file_size=100,
            file_type="txt",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Create actual file for extraction
        with open(doc.file_path, "w") as f:
            f.write("This is a test document. It has multiple sentences. " * 20)

        # Get the text extractor and extract
        from app.extractors import create_default_registry
        registry = create_default_registry()
        extractor = registry.get_extractor('txt')

        if extractor:
            result = extractor.extract(Path(doc.file_path))
            chunks = indexing_service.index_document(doc, force=True)

            assert len(chunks) > 0

            # Verify in database
            conn = db.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as cnt FROM chunks WHERE document_id = ?", (doc.id,))
                row = cursor.fetchone()
                assert row["cnt"] == len(chunks)
            finally:
                conn.close()
        else:
            pytest.skip("Text extractor not available")


class TestRetrievalService:
    """Tests for the retrieval service."""

    @pytest.fixture
    def setup(self):
        """Setup test database and services."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        config = AppConfig()
        config.set("database_path", db_path)
        config.set("retrieval_count", 5)

        create_database(db_path)
        db = Database(db_path)

        class MockOllamaClient:
            def generate_embedding(self, model, text):
                return [0.1] * 768

        ollama_client = MockOllamaClient()

        retrieval_service = RetrievalService(
            db,
            ollama_client,
            config,
        )

        yield {
            "db": db,
            "config": config,
            "retrieval_service": retrieval_service,
            "temp_dir": temp_dir,
        }

        shutil.rmtree(temp_dir)

    def test_search_no_results(self, setup):
        """Test search with no documents."""
        retrieval_service = setup["retrieval_service"]
        results = retrieval_service.search("test query")
        assert len(results) == 0

    def test_search_with_results(self, setup):
        """Test search returns results for indexed documents."""
        temp_dir = setup["temp_dir"]
        db = setup["db"]
        retrieval_service = setup["retrieval_service"]

        from app.models.document import Document as DomainDocument, Chunk as DomainChunk
        from datetime import datetime
        import json

        doc = DomainDocument(
            id=1,
            filename="test.pdf",
            original_filename="test.pdf",
            file_path=os.path.join(temp_dir, "test.pdf"),
            file_size=100,
            file_type="pdf",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        emb1 = [0.1] * 768
        emb2 = [0.9] * 768

        chunk1 = DomainChunk(
            id=1,
            document_id=doc.id,
            chunk_index=0,
            text="Important information about apples",
            embedding=emb1,
            created_at=datetime.now(),
        )
        chunk2 = DomainChunk(
            id=2,
            document_id=doc.id,
            chunk_index=1,
            text="Important information about oranges",
            embedding=emb2,
            created_at=datetime.now(),
        )

        conn = db.get_connection()
        try:
            cursor = conn.cursor()

            emb1_json = json.dumps(emb1)
            emb2_json = json.dumps(emb2)

            now = datetime.now().isoformat()
            cursor.execute("INSERT INTO documents (id, filename, original_filename, file_path, file_size, file_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (doc.id, doc.filename, doc.original_filename, doc.file_path, doc.file_size, doc.file_type, now, now))

            cursor.execute("INSERT INTO chunks (id, document_id, chunk_index, text, embedding, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (chunk1.id, chunk1.document_id, chunk1.chunk_index, chunk1.text, emb1_json, now))

            cursor.execute("INSERT INTO chunks (id, document_id, chunk_index, text, embedding, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (chunk2.id, chunk2.document_id, chunk2.chunk_index, chunk2.text, emb2_json, now))

            conn.commit()
        finally:
            conn.close()

        results = retrieval_service.search("apples", limit=2)

        assert len(results) >= 1
        assert results[0]['text'] == chunk1.text
