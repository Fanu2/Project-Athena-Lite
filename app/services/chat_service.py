"""
Chat Service - handles RAG question answering.

Light Version responsibilities:
- Conversation persistence
- User/assistant message storage
- Retrieval augmented answering
- Ollama chat generation
- Source metadata for citations

Intentionally NOT included:
- Agents
- Memory system
- Plugins
- Advanced workflows
"""

import logging
from datetime import datetime
from typing import List, Dict, Any


from app.database import Database
from app.config import AppConfig
from app.services.indexing_service import RetrievalService


logger = logging.getLogger(__name__)


class ChatService:
    """
    Main chat application service.

    Flow:

    User Question
          |
          v
      RetrievalService
          |
          v
      Context Builder
          |
          v
        Ollama
          |
          v
      Answer + Sources
    """


    def __init__(
        self,
        db: Database,
        llm_client,
        retrieval_service: RetrievalService,
        config: AppConfig
    ):

        self.db = db
        self.llm_client = llm_client
        self.retrieval_service = retrieval_service
        self.config = config



    # -------------------------------------------------
    # Conversation Management
    # -------------------------------------------------

    def create_new_conversation(
        self,
        title: str = "New Conversation"
    ) -> int:
        """Create and return a conversation ID."""

        now = datetime.now().isoformat()

        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO conversations
                (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    title,
                    now,
                    now
                )
            )

            conn.commit()

            return cursor.lastrowid

        finally:
            conn.close()



    def list_conversations(self) -> List[dict]:
        """Return all conversations."""

        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT *
                FROM conversations
                ORDER BY updated_at DESC
                """
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

        finally:
            conn.close()



    def get_conversation_history(
        self,
        conv_id: int
    ) -> List[dict]:
        """
        Return messages for a conversation.

        Used by:
        - UI history loading
        - Tests
        """

        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT *
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conv_id,)
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "conversation_id": row["conversation_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        finally:
            conn.close()



    def _add_conversation_message(
        self,
        conv_id: int,
        role: str,
        content: str
    ) -> int:
        """
        Save a message.

        Kept as public internal API because
        existing UI/tests use this method.
        """

        now = datetime.now().isoformat()

        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO messages
                (
                    conversation_id,
                    role,
                    content,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    conv_id,
                    role,
                    content,
                    now
                )
            )


            cursor.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE id = ?
                """,
                (
                    now,
                    conv_id
                )
            )


            conn.commit()

            return cursor.lastrowid

        finally:
            conn.close()



    def _add_message(
        self,
        conversation_id,
        role,
        content
    ):
        """Compatibility wrapper."""

        return self._add_conversation_message(
            conversation_id,
            role,
            content
        )



    # -------------------------------------------------
    # UI Entry Point
    # -------------------------------------------------

    def ask(
        self,
        question: str,
        conversation_id=None
    ) -> dict:
        """
        Main entry point from Chat UI.
        """

        if conversation_id is None:

            conversation_id = self.create_new_conversation(
                "Athena Chat"
            )


        self._add_conversation_message(
            conversation_id,
            "user",
            question
        )


        result = self.answer(
            question
        )


        self._add_conversation_message(
            conversation_id,
            "assistant",
            result["answer"]
        )


        return result



    # -------------------------------------------------
    # RAG Answering
    # -------------------------------------------------

    def answer(
        self,
        question: str
    ) -> dict:
        """
        Perform retrieval augmented answering.
        """

        results = self.retrieval_service.search(
            question,
            limit=self.config.retrieval_count
        )


        if not results:

            return {
                "answer":
                    (
                        "I don't have any indexed documents "
                        "to answer this question. "
                        "Please import and index some documents first."
                    ),
                "sources": []
            }



        context = self._build_context(
            results
        )


        # No LLM fallback
        if not self.llm_client:

            return {
                "answer":
                    self._mock_answer(context),

                "sources":
                    self._format_sources(results)
            }



        prompt = f"""
Answer using only the supplied context.

Context:

{context}


Question:

{question}
"""


        try:

            response = self.llm_client.chat(
                self.config.ollama_model,
                [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                stream=False
            )


            answer = (
                response.get("response")
                or
                response.get(
                    "message",
                    {}
                ).get(
                    "content",
                    ""
                )
            )


        except Exception as e:

            logger.exception(e)

            answer = (
                f"AI generation failed: {e}"
            )


        return {
            "answer": answer,
            "sources": self._format_sources(results)
        }



    def _build_context(
        self,
        results
    ) -> str:
        """Create LLM context."""

        parts = []

        for index, result in enumerate(results):

            parts.append(
                f"""
[Source {index + 1}]

{result['text']}
"""
            )

        return "\n".join(parts)



    def _mock_answer(
        self,
        context: str
    ) -> str:
        """Fallback when no LLM is available."""

        return (
            "I found this information in your documents:\n\n"
            + context[:2000]
            +
            "\n\n(Source-based response)"
        )



    def _format_sources(
        self,
        results
    ) -> List[dict]:
        """
        Convert retrieval results into UI citation format.
        """

        sources = []


        for result in results:

            sources.append(
                {
                    "document_name":
                        result.get(
                            "document_name",
                            f"Document {result['document_id']}"
                        ),

                    "document_id":
                        result["document_id"],

                    "chunk_index":
                        result["chunk_index"],

                    "score":
                        result.get(
                            "score",
                            0
                        ),

                    "text_preview":
                        result["text"][:200],
                }
            )


        return sources