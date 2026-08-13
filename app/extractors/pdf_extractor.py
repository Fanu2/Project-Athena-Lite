"""
PDF text extractor using PyMuPDF (fitz).
Extracts text with page number tracking.
"""

import logging
from pathlib import Path
from typing import List, Tuple

from app.extractors.base import DocumentExtractor, ExtractionResult, PageText

logger = logging.getLogger(__name__)


class PDFExtractor(DocumentExtractor):
    """
    PDF document text extractor using PyMuPDF (fitz).
    Extracts text from PDF files with metadata and page tracking.
    """

    supported_extensions = ['.pdf']
    name = 'PDF'

    def __init__(self):
        super().__init__()
        try:
            import fitz
            self._fitz = fitz
        except ImportError:
            self._fitz = None
            logger.warning("PyMuPDF (fitz) not installed. PDF extraction unavailable.")

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extract text from a PDF file."""
        if self._fitz is None:
            raise RuntimeError("PyMuPDF (fitz) not installed. Cannot extract PDF.")

        doc = self._fitz.open(str(file_path))
        pages_text: List[PageText] = []
        full_text = []

        try:
            metadata = doc.metadata
            title = metadata.get('title', '') if metadata else ''
            author = metadata.get('author', '') if metadata else ''
            subject = metadata.get('subject', '') if metadata else ''

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                pages_text.append(PageText(
                    page_number=page_num + 1,
                    text=text,
                ))
                full_text.append(text)

                if 'title' not in locals() or not title:
                    blocks = page.get_text("blocks")
                    for block in blocks:
                        if len(block) >= 4:
                            first_line = block[4].strip()
                            if first_line and len(first_line) < 100:
                                title = first_line
                                break

            full_text_str = '\n\n'.join(full_text)
        finally:
            doc.close()

        return ExtractionResult(
            text=full_text_str,
            pages=pages_text,
            metadata={
                'title': title,
            },
        )
