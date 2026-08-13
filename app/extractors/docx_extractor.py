"""
DOCX text extractor using python-docx.
Extracts text from Word documents.
"""

import logging
from pathlib import Path
from typing import List

from app.extractors.base import DocumentExtractor, ExtractionResult, PageText

logger = logging.getLogger(__name__)


class DOCXExtractor(DocumentExtractor):
    """
    DOCX document text extractor using python-docx.
    Extracts text from Word documents with paragraph tracking.
    """

    supported_extensions = ['.docx', '.doc']
    name = 'DOCX'

    def __init__(self):
        super().__init__()
        try:
            from docx import Document as DocxDocument
            self._docx = DocxDocument
        except ImportError:
            self._docx = None
            logger.warning("python-docx not installed. DOCX extraction unavailable.")

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extract text from a DOCX file."""
        if self._docx is None:
            raise RuntimeError("python-docx not installed. Cannot extract DOCX.")

        doc = self._docx(str(file_path))
        full_text = []
        pages_text: List[PageText] = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                full_text.append(text)
                pages_text.append(PageText(
                    page_number=len(pages_text) + 1,
                    text=text,
                ))

        full_text_str = '\n\n'.join(full_text)

        return ExtractionResult(
            text=full_text_str,
            pages=pages_text,
            metadata={
                'paragraph_count': len(full_text),
            },
        )
