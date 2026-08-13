"""
Text and Markdown extractors.
Ext extracts plain text and markdown files.
"""

import logging
from pathlib import Path
from typing import List

from app.extractors.base import DocumentExtractor, ExtractionResult, PageText

logger = logging.getLogger(__name__)


class TextExtractor(DocumentExtractor):
    """
    Extracts text from plain text files (.txt, .text).
    """

    supported_extensions = [".txt", ".text"]

    def extract(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from a plain text file.

        Args:
            file_path: Path to the text file

        Returns:
            ExtractionResult with full text
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")

            pages = [
                PageText(
                    page_number=1,
                    text=content,
                    full_text=content,
                )
            ]

            metadata = {
                "title": file_path.stem,
                "author": "",
                "page_count": 1,
            }

            logger.info(f"Extracted text: {file_path.name} ({len(content)} chars)")

            return ExtractionResult(
                pages=pages,
                full_text=content,
                metadata={
                    "title": file_path.stem,
                    "author": "",
                    "page_count": 1,
                    "line_count": content.count('\n') + 1,
                },
            )

        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ["latin-1", "cp1252", "utf-16"]:
                try:
                    content = file_path.read_text(encoding=encoding)
                    pages = [
                        PageText(
                            page_number=1,
                            text=content,
                            full_text=content,
                        )
                    ]
                    return ExtractionResult(
                        pages=pages,
                        full_text=content,
                        metadata=metadata,
                    )
                except UnicodeDecodeError:
                    continue
            raise DocumentExtractionError(f"Failed to decode text file: {file_path}")
        except Exception as e:
            logger.error(f"Error extracting text {file_path}: {e}")
            raise DocumentExtractionError(f"Failed to extract text: {e}") from e


class MarkdownExtractor(DocumentExtractor):
    """
    Extracts text from Markdown files (.md, .markdown).

    Markdown files are treated as plain text with a single page.
    """

    supported_extensions = [".md", ".markdown", ".mkd"]

    def extract(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from a Markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            ExtractionResult with full text
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")

            pages = [
                PageText(
                    page_number=1,
                    text=content,
                    full_text=content,
                )
            ]

            metadata = {
                "title": file_path.stem,
                "author": "",
                "page_count": 1,
            }

            logger.info(f"Extracted markdown: {file_path.name} ({len(content)} chars)")

            return ExtractionResult(
                pages=pages,
                full_text=content,
                metadata={
                    "title": file_path.stem,
                    "author": "",
                    "page_count": 1,
                    "line_count": content.count('\n') + 1,
                },
            )

        except UnicodeDecodeError:
            for encoding in ["latin-1", "cp1252", "utf-16"]:
                try:
                    content = file_path.read_text(encoding=encoding)
                    pages = [
                        PageText(
                            page_number=1,
                            text=content,
                            full_text=content,
                        )
                    ]
                    return ExtractionResult(
                        pages=pages,
                        full_text=content,
                        metadata=metadata,
                    )
                except UnicodeDecodeError:
                    continue
            raise DocumentExtractionError(f"Failed to decode markdown file: {file_path}")
        except Exception as e:
            logger.error(f"Error extracting markdown {file_path}: {e}")
            raise DocumentExtractionError(f"Failed to extract markdown: {e}") from e
