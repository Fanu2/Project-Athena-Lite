"""
Base classes for document extractors.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class DocumentExtractionError(Exception):
    """Raised when document extraction fails."""
    pass


@dataclass(slots=True)
class PageText:
    """Text content from a single page."""
    page_number: int
    text: str
    full_text: str


@dataclass
class ExtractionResult:
    """Result of document extraction."""
    pages: List[PageText] = field(default_factory=list)
    full_text: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def text(self) -> str:
        """Convenience property returning full text."""
        return self.full_text


class DocumentExtractor(ABC):
    """
    Abstract base class for document extractors.

    Each extractor handles a specific file format and converts
    documents into structured text with page tracking.
    """

    supported_extensions: List[str] = []

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractionResult:
        """
        Extract text and metadata from a document.

        Args:
            file_path: Path to the document file

        Returns:
            ExtractionResult with pages, full text, and metadata

        Raises:
            DocumentExtractionError: If extraction fails
        """
        ...

    def validate(self, file_path: Path) -> bool:
        """
        Validate that the file can be extracted.

        Args:
            file_path: Path to the document file

        Returns:
            True if the file is valid for this extractor
        """
        return file_path.exists() and file_path.suffix.lower() in self.supported_extensions


class ExtractorRegistry:
    """
    Registry for document extractors.

    Maintains a mapping of file extensions to extractors.
    """

    def __init__(self):
        self._extractors: dict[str, DocumentExtractor] = {}

    def register(self, extractor: DocumentExtractor) -> None:
        """Register an extractor for its supported extensions."""
        for ext in extractor.supported_extensions:
            self._extractors[ext.lower()] = extractor

    def get_extractor(self, file_type: str) -> DocumentExtractor | None:
        """
        Get the appropriate extractor for a file type.

        Args:
            file_type: File extension (e.g., '.txt', '.pdf', '.docx')

        Returns:
            Extractor instance for the file type, or None if not found
        """
        ext = file_type.lower() if file_type.startswith('.') else f'.{file_type.lower()}'
        return self._extractors.get(ext)

    def get_supported_extensions(self) -> List[str]:
        """Get list of all supported file extensions."""
        return list(self._extractors.keys())

    def is_supported(self, file_path: Path) -> bool:
        """Check if a file type is supported."""
        return file_path.suffix.lower() in self._extractors


def create_default_registry() -> ExtractorRegistry:
    """Create a registry with default extractors."""
    from app.extractors.pdf_extractor import PDFExtractor
    from app.extractors.docx_extractor import DOCXExtractor
    from app.extractors.text_extractor import TextExtractor, MarkdownExtractor

    registry = ExtractorRegistry()
    registry.register(PDFExtractor())
    registry.register(DOCXExtractor())
    registry.register(TextExtractor())
    registry.register(MarkdownExtractor())

    return registry
