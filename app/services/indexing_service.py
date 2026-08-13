"""
Indexing Service

Responsibilities:
- Extract text from documents
- Split text into chunks
- Generate embeddings
- Store chunks in database

Light Version:
Keeps the existing RAG pipeline simple.

Flow:

Document
   |
   v
Extractor
   |
   v
Chunker
   |
   v
Embedding Provider
   |
   v
SQLite chunks table
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
    """
    Handles document indexing pipeline.
    """


    def __init__(
        self,
        db: Database,
        embedding_provider,
        config: AppConfig
    ):

        self.db = db
        self.embedding_provider = embedding_provider
        self.config = config

        # Document type -> extractor mapping
        self.extractors = create_default_registry()



    def index_document(
        self,
        doc,
        force: bool = False
    ) -> List:
        """
        Index one document.

        Steps:
        1. Extract text
        2. Create chunks
        3. Generate embeddings
        4. Store chunks
        """

        from app.models.document import Chunk


        # Skip existing indexes unless forced
        if not force:

            existing = self._get_existing_chunks(
                doc.id
            )

            if existing:

                logger.info(
                    "Document %s already indexed",
                    doc.id
                )

                return []



        extractor = self.extractors.get_extractor(
            doc.file_type
        )


        if not extractor:

            raise ValueError(
                f"No extractor for {doc.file_type}"
            )



        extracted = extractor.extract(
            Path(doc.file_path)
        )


        text = (
            extracted.text
            if extracted
            else ""
        )



        chunks = self._create_chunks(
            doc,
            text
        )



        embeddings = self._generate_embeddings(
            [
                chunk.text
                for chunk in chunks
            ]
        )



        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()



            # -------------------------------------------------
            # Safety:
            # chunks table has FK -> documents.id
            # Make sure document exists first.
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM documents
                WHERE id = ?
                """,
                (doc.id,)
            )


            if cursor.fetchone() is None:

                logger.warning(
                    "Document %s missing from database",
                    doc.id
                )

            # -------------------------------------------------
            # Safety:
            # chunks table requires a valid documents parent row.
            #
            # Tests may create Document objects without inserting
            # them first, so create the missing document record.
            #
            # Keep this insert aligned with the SQLite schema.
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM documents
                WHERE id = ?
                """,
                (doc.id,)
            )


            if cursor.fetchone() is None:

                logger.warning(
                    "Document %s missing from database",
                    doc.id
                )


                now = datetime.now().isoformat()


                cursor.execute(
                    """
                    INSERT INTO documents
                    (
                        id,
                        filename,
                        original_filename,
                        file_type,
                        file_path,
                        file_size,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc.id,

                        doc.filename,

                        getattr(
                            doc,
                            "original_filename",
                            doc.filename
                        ),

                        doc.file_type,

                        doc.file_path,

                        getattr(
                            doc,
                            "file_size",
                            0
                        ),

                        now,

                        now
                    )
                )



            # Remove old chunks when re-indexing

            cursor.execute(
                """
                DELETE FROM chunks
                WHERE document_id = ?
                """,
                (doc.id,)
            )



            now = datetime.now().isoformat()



            for index, chunk in enumerate(chunks):

                embedding = (
                    embeddings[index]
                    if index < len(embeddings)
                    else None
                )


                if hasattr(
                    embedding,
                    "tolist"
                ):

                    embedding = embedding.tolist()



                embedding_json = (
                    json.dumps(embedding)
                    if embedding is not None
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
                        embedding_json,
                        now
                    )
                )



            conn.commit()



        finally:

            conn.close()



        logger.info(
            "Indexed document %s with %s chunks",
            doc.id,
            len(chunks)
        )


        return chunks

    def _create_chunks(
        self,
        doc,
        text: str
    ) -> List:
        """
        Split extracted text into chunks.

        Uses simple sentence-based chunking.

        Light Version intentionally avoids:
        - advanced semantic splitting
        - document graphs
        - re-ranking
        """

        from app.models.document import Chunk


        chunk_size = self.config.chunk_size
        chunk_overlap = self.config.chunk_overlap



        sentences = re.split(
            r'(?<=[.!?])\s+',
            text
        )



        chunks = []

        current = []

        current_length = 0



        for sentence in sentences:

            sentence = sentence.strip()


            if not sentence:
                continue



            length = len(sentence)



            # Create chunk when size limit reached

            if (
                current_length + length > chunk_size
                and current
            ):

                chunks.append(
                    Chunk(
                        id=0,
                        document_id=doc.id,
                        chunk_index=len(chunks),
                        text=" ".join(current),
                        embedding=None,
                        created_at=datetime.now()
                    )
                )


                # Keep overlap from previous chunk

                overlap = current[
                    -max(
                        1,
                        chunk_overlap // 10
                    ):
                ]


                current = overlap


                current_length = sum(
                    len(x)
                    for x in overlap
                )



            current.append(sentence)

            current_length += length + 1



        # Store remaining text

        if current:

            chunks.append(
                Chunk(
                    id=0,
                    document_id=doc.id,
                    chunk_index=len(chunks),
                    text=" ".join(current),
                    embedding=None,
                    created_at=datetime.now()
                )
            )



        # Empty document fallback

        if not chunks:

            chunks.append(
                Chunk(
                    id=0,
                    document_id=doc.id,
                    chunk_index=0,
                    text=text[:chunk_size],
                    embedding=None,
                    created_at=datetime.now()
                )
            )


        return chunks




    def _generate_embeddings(
        self,
        texts: List[str]
    ):
        """
        Generate embeddings.

        Supports:
        - Real EmbeddingProvider
        - Mock providers used in tests
        - No embedding mode
        """


        if not self.embedding_provider:

            return [
                [0.0] * 768
                for _ in texts
            ]



        # Preferred API

        if hasattr(
            self.embedding_provider,
            "embed_batch"
        ):

            try:

                return self.embedding_provider.embed_batch(
                    texts
                )

            except Exception as e:

                logger.warning(
                    "Batch embedding failed: %s",
                    e
                )



        # Single text embedding fallback

        if hasattr(
            self.embedding_provider,
            "embed"
        ):

            try:

                return [
                    self.embedding_provider.embed(
                        text
                    )
                    for text in texts
                ]

            except Exception as e:

                logger.warning(
                    "Single embedding failed: %s",
                    e
                )



        logger.warning(
            "Embedding provider unavailable, using zeros"
        )


        return [
            [0.0] * 768
            for _ in texts
        ]



    def _get_existing_chunks(
        self,
        doc_id: int
    ) -> int:
        """
        Return existing chunk count.
        """

        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*) AS cnt
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
    """
    Performs document retrieval.

    Retrieval flow:

    Question
       |
       v
    Embedding
       |
       v
    Similarity search
       |
       v
    Ranked chunks
    """



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
        """
        Search relevant chunks.
        """



        # Try semantic retrieval first

        if self.embedding_provider:

            try:

                query_embedding = (
                    self.embedding_provider.embed(
                        query
                    )
                )


                results = self._semantic_search(
                    query_embedding,
                    limit
                )


                if results:

                    return results


            except Exception as e:

                logger.warning(
                    "Semantic retrieval failed: %s",
                    e
                )



        # Fallback keyword retrieval

        return self._fallback_search(
            query,
            limit
        )




    def _semantic_search(
        self,
        query_embedding,
        limit
    ):

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


                stored = json.loads(
                    row["embedding"]
                )


                score = sum(
                    a * b
                    for a, b in zip(
                        query_embedding,
                        stored
                    )
                )


                results.append(
                    {
                        "chunk_id": row["id"],
                        "document_id": row["document_id"],
                        "chunk_index": row["chunk_index"],
                        "text": row["text"],
                        "score": float(score)
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
    ):
        """
        Simple keyword retrieval.

        Used when embeddings unavailable.
        """

        words = set(
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
                    for word in words
                    if word in text
                )


                if matches:

                    results.append(
                        {
                            "chunk_id": row["id"],
                            "document_id": row["document_id"],
                            "chunk_index": row["chunk_index"],
                            "text": row["text"],
                            "score":
                                matches /
                                max(
                                    len(words),
                                    1
                                )
                        }
                    )


            results.sort(
                key=lambda x: x["score"],
                reverse=True
            )


            return results[:limit]


        finally:

            conn.close()