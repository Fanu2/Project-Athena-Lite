"""
Chat Service - handles RAG question answering.
"""

import logging
from datetime import datetime
from typing import List

from app.database import Database
from app.config import AppConfig
from app.services.indexing_service import RetrievalService


logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for handling chat conversations and RAG question answering.
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



    def create_new_conversation(
        self,
        title="New Conversation"
    ):

        now = datetime.now().isoformat()

        conn = self.db.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO conversations
                (title, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (title, now, now)
            )

            conn.commit()

            return cursor.lastrowid

        finally:
            conn.close()



    def list_conversations(self):

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
                    "id": r["id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]

        finally:
            conn.close()



    def _add_message(
        self,
        conversation_id,
        role,
        content
    ):

        now = datetime.now().isoformat()

        conn = self.db.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO messages
                (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                    now
                )
            )

            conn.commit()

            return cursor.lastrowid

        finally:
            conn.close()



    # -------------------------------------------------
    # UI ENTRY POINT
    # -------------------------------------------------

    def ask(
        self,
        question: str,
        conversation_id=None
    ):

        """
        Called by Chat UI.
        """

        if conversation_id is None:

            conversation_id = (
                self.create_new_conversation(
                    "Athena Chat"
                )
            )


        self._add_message(
            conversation_id,
            "user",
            question
        )


        result = self.answer(question)


        self._add_message(
            conversation_id,
            "assistant",
            result["answer"]
        )


        return result



    # -------------------------------------------------
    # RAG ENGINE
    # -------------------------------------------------

    def answer(
        self,
        question: str
    ):

        results = self.retrieval_service.search(
            question,
            limit=self.config.retrieval_count
        )


        if not results:

            return {
                "answer":
                (
                    "I could not find relevant documents. "
                    "Please import documents first."
                ),
                "sources": []
            }



        context = self._build_context(results)



        if not self.llm_client:

            return {
                "answer":
                    self._mock_answer(
                        context
                    ),
                "sources":
                    self._format_sources(results)
            }



        prompt = f"""
Answer using only this context.

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
                        "role":"user",
                        "content":prompt
                    }
                ],
                stream=False
            )


            answer = (
                response.get("response")
                or (response.get("message") or {}).get("content")
                or ""
            )


        except Exception as e:

            logger.exception(e)

            answer = (
                f"AI generation failed: {e}"
            )



        return {
            "answer": answer,
            "sources":
                self._format_sources(results)
        }



    def _build_context(
        self,
        results
    ):

        parts=[]

        for i,r in enumerate(results):

            parts.append(
                f"""
[Source {i+1}]

{r['text']}
"""
            )

        return "\n".join(parts)



    def _mock_answer(
        self,
        context
    ):

        return (
            "I found this information in your documents:\n\n"
            +
            context[:2000]
            +
            "\n\n(Source-based response)"
        )



    def _format_sources(
        self,
        results
    ):

        sources=[]

        for r in results:

            sources.append(
                {
                    "document_id":
                        r["document_id"],

                    "chunk_index":
                        r["chunk_index"],

                    "score":
                        r.get(
                            "score",
                            0
                        ),

                    "text_preview":
                        r["text"][:200]
                }
            )


        return sources