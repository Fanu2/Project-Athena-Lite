"""
Indexing Service - handles text extraction, chunking, and embedding generation.
Numpy import is lazy (only when needed).
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List

from app.database import Database
from app.config import AppConfig
from app.extractors import create_default_registry


logger = logging.getLogger(__name__)


class IndexingService:
    """Service for indexing documents: extract, chunk, embed, store."""

    def __init__(self, db: Database, embedding_provider, config: AppConfig):
        self.db = db
        self.embedding_provider = embedding_provider
        self.config = config
        self.extractors = create_default_registry()


    def index_document(self, doc, force: bool = False) -> List:
        """Index a document: extract text, chunk it, generate embeddings, store."""

        from app.models.document import Chunk

        if not force:
            existing = self._get_existing_chunks(doc.id)
            if existing > 0:
                logger.info(
                    f"Document {doc.id} already indexed, skipping"
                )
                return []


        extractor = self.extractors.get_extractor(
            doc.file_type
        )

        if not extractor:
            raise ValueError(
                f"No extractor for {doc.file_type}"
            )


        result = extractor.extract(
            Path(doc.file_path)
        )

        text = result.text if result else ""


        chunks = self._create_chunks(
            doc,
            text
        )


        # FIX: generate embeddings before storing
        embeddings = self._generate_embeddings(
            [chunk.text for chunk in chunks]
        )


        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM chunks WHERE document_id = ?",
                (doc.id,)
            )


            now_iso = datetime.now().isoformat()


            for i, chunk in enumerate(chunks):

                embedding = (
                    embeddings[i]
                    if i < len(embeddings)
                    else None
                )

                emb_list = (
                    embedding.tolist()
                    if hasattr(embedding, "tolist")
                    else embedding
                )

                emb_json = (
                    json.dumps(emb_list)
                    if emb_list is not None
                    else None
                )


                cursor.execute(
                    """
                    INSERT INTO chunks
                    (
                        document_id,
                        chunk_index,
                        text,
                        embedding,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        doc.id,
                        chunk.chunk_index,
                        chunk.text,
                        emb_json,
                        now_iso
                    )
                )


            conn.commit()


        finally:
            conn.close()


        logger.info(
            f"Indexed document {doc.id} with {len(chunks)} chunks"
        )

        return chunks



    def _create_chunks(self, doc, text: str) -> List:
        """Split text into chunks."""

        from app.models.document import Chunk


        chunk_size = self.config.chunk_size
        chunk_overlap = self.config.chunk_overlap


        sentences = re.split(
            r'(?<=[.!?])\s+',
            text
        )


        chunks = []
        current_chunk = []
        current_size = 0


        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue


            sentence_len = len(sentence)


            if (
                current_size + sentence_len > chunk_size
                and current_chunk
            ):

                chunk_text = " ".join(
                    current_chunk
                )

                chunks.append(
                    Chunk(
                        id=0,
                        document_id=doc.id,
                        chunk_index=len(chunks),
                        text=chunk_text,
                        embedding=None,
                        created_at=datetime.now(),
                    )
                )


                overlap_words = current_chunk[
                    -max(1, chunk_overlap // 10):
                ]

                current_chunk = overlap_words

                current_size = sum(
                    len(w)
                    for w in overlap_words
                )


            current_chunk.append(sentence)
            current_size += sentence_len + 1



        if current_chunk:

            chunks.append(
                Chunk(
                    id=0,
                    document_id=doc.id,
                    chunk_index=len(chunks),
                    text=" ".join(current_chunk),
                    embedding=None,
                    created_at=datetime.now(),
                )
            )


        return chunks or [
            Chunk(
                id=0,
                document_id=doc.id,
                chunk_index=0,
                text=text[:chunk_size],
                embedding=None,
                created_at=datetime.now(),
            )
        ]



    def _generate_embeddings(self, texts: List[str]):

        """Generate embeddings for texts."""

        if not self.embedding_provider:
            return [
                [0.0] * 768
                for _ in texts
            ]


        try:
            return self.embedding_provider.embed_batch(
                texts
            )

        except Exception as e:

            logger.warning(
                f"Embedding failed: {e}"
            )

            return [
                [0.0] * 768
                for _ in texts
            ]



    def _get_existing_chunks(self, doc_id: int):

        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*) as cnt
                FROM chunks
                WHERE document_id = ?
                """,
                (doc_id,)
            )

            row = cursor.fetchone()

            return row["cnt"]

        finally:
            conn.close()



class RetrievalService:
    """Service for semantic retrieval of document chunks."""

    def __init__(
        self,
        db: Database,
        embedding_provider,
        config: AppConfig
    ):

        self.db = db
        self.embedding_provider = embedding_provider
        self.config = config



    def search(
        self,
        query: str,
        limit: int = 5
    ) -> List[dict]:

        if not self.embedding_provider:
            return self._fallback_search(
                query,
                limit
            )


        try:

            query_emb = self.embedding_provider.embed(
                query
            )

        except Exception as e:

            logger.warning(
                f"Query embedding failed: {e}"
            )

            return self._fallback_search(
                query,
                limit
            )


        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT *
                FROM chunks
                WHERE embedding IS NOT NULL
                """
            )

            rows = cursor.fetchall()


            results = []


            for row in rows:

                emb = json.loads(
                    row["embedding"]
                )


                similarity = sum(
                    a * b
                    for a, b in zip(
                        query_emb,
                        emb
                    )
                )


                results.append(
                    {
                        "chunk_id": row["id"],
                        "document_id": row["document_id"],
                        "chunk_index": row["chunk_index"],
                        "text": row["text"],
                        "score": float(similarity),
                    }
                )


            results.sort(
                key=lambda x: x["score"],
                reverse=True
            )


            return results[:limit]


        finally:
            conn.close()



    def _fallback_search(
        self,
        query: str,
        limit: int
    ) -> List[dict]:

        query_words = set(
            query.lower().split()
        )


        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM chunks"
            )

            rows = cursor.fetchall()


            results = []


            for row in rows:

                text = row["text"].lower()

                matches = sum(
                    1
                    for w in query_words
                    if w in text
                )


                if matches:

                    results.append(
                        {
                            "chunk_id": row["id"],
                            "document_id": row["document_id"],
                            "chunk_index": row["chunk_index"],
                            "text": row["text"],
                            "score": matches / len(query_words),
                        }
                    )


            results.sort(
                key=lambda x: x["score"],
                reverse=True
            )

            return results[:limit]


        finally:
            conn.close()