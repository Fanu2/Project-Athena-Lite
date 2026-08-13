"""
Document Service - handles document import, validation, and metadata management.
Uses plain SQLite (no SQLAlchemy).
"""

import hashlib
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.database import Database
from app.models.document import Document as DomainDocument


logger = logging.getLogger(__name__)


class DocumentService:
    """Service for managing documents: import, list, get, remove."""

    def __init__(self, documents_dir: Path, db: Database):
        self.documents_dir = documents_dir
        self.db = db
        self.documents_dir.mkdir(parents=True, exist_ok=True)

    def import_document(self, file_path: Path) -> DomainDocument:
        """Import a document: copy to documents dir and record in database."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.suffix.lower()

        import shutil
        dest_path = self.documents_dir / file_path.name
        counter = 1
        while dest_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            dest_path = self.documents_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        shutil.copy2(file_path, dest_path)

        file_size = dest_path.stat().st_size

        supported = {'.pdf', '.docx', '.doc', '.txt', '.md', '.markdown', '.mkd'}
        if ext not in supported:
            raise ValueError(f"Unsupported file type: {ext}")

        now = datetime.now().isoformat()

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents (filename, original_filename, file_path, file_size, file_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (dest_path.name, file_path.name, str(dest_path), file_size, ext[1:], now, now))
            conn.commit()
            doc_id = cursor.lastrowid
        finally:
            conn.close()

        from app.models.document import Document as DomainDocument
        return DomainDocument(
            id=doc_id,
            filename=dest_path.name,
            original_filename=file_path.name,
            file_path=str(dest_path),
            file_size=file_size,
            file_type=ext[1:],
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    def list_documents(self) -> List[DomainDocument]:
        """List all documents."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_document(row) for row in rows]
        finally:
            conn.close()

    def get_document(self, doc_id: int) -> Optional[DomainDocument]:
        """Get a document by ID."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_document(row)
            return None
        finally:
            conn.close()

    def remove_document(self, doc_id: int) -> bool:
        """Remove a document from database and filesystem."""
        doc = self.get_document(doc_id)
        if not doc:
            return False

        try:
            import os
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
        except:
            pass

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def _row_to_document(self, row: dict) -> DomainDocument:
        """Convert database row to domain Document."""
        from app.models.document import Document as DomainDocument
        return DomainDocument(
            id=row['id'],
            filename=row['filename'],
            original_filename=row['original_filename'],
            file_path=row['file_path'],
            file_size=row['file_size'],
            file_type=row['file_type'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
        )
