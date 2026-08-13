"""
Text and Markdown extractors.

Light Version responsibilities:
- Extract plain text files
- Extract Markdown files
- Return document text
- Provide basic metadata
- Track Markdown headings for UI/tests
"""

import logging
import re
from pathlib import Path

from app.extractors.base import (
    DocumentExtractor,
    ExtractionResult,
    PageText,
    DocumentExtractionError,
)


logger = logging.getLogger(__name__)


class TextExtractor(DocumentExtractor):
    """
    Extracts plain text files.

    Supported:
    - .txt
    - .text
    """

    supported_extensions = [
        ".txt",
        ".text",
    ]


    def extract(
        self,
        file_path: Path
    ) -> ExtractionResult:
        """
        Extract text content from a file.
        """

        if not file_path.exists():
            raise FileNotFoundError(
                f"Text file not found: {file_path}"
            )


        try:
            content = self._read_text(
                file_path
            )


            logger.info(
                "Extracted text: %s (%s chars)",
                file_path.name,
                len(content)
            )


            return ExtractionResult(
                pages=[
                    PageText(
                        page_number=1,
                        text=content,
                        full_text=content,
                    )
                ],

                full_text=content,

                metadata={
                    "title": file_path.stem,
                    "author": "",
                    "page_count": 1,
                    "line_count": content.count("\n") + 1,
                },
            )


        except Exception as e:

            logger.exception(e)

            raise DocumentExtractionError(
                f"Failed to extract text: {e}"
            ) from e



    def _read_text(
        self,
        file_path: Path
    ) -> str:
        """
        Read text using fallback encodings.
        """

        for encoding in [
            "utf-8",
            "latin-1",
            "cp1252",
            "utf-16",
        ]:

            try:
                return file_path.read_text(
                    encoding=encoding
                )

            except UnicodeDecodeError:
                continue


        raise DocumentExtractionError(
            f"Unable to decode file: {file_path}"
        )



class MarkdownExtractor(DocumentExtractor):
    """
    Extracts Markdown documents.

    Supported:
    - .md
    - .markdown
    - .mkd

    Markdown is treated as normal text,
    but headings are collected as sections.
    """

    supported_extensions = [
        ".md",
        ".markdown",
        ".mkd",
    ]


    def extract(
        self,
        file_path: Path
    ) -> ExtractionResult:
        """
        Extract Markdown content.
        """

        if not file_path.exists():
            raise FileNotFoundError(
                f"Markdown file not found: {file_path}"
            )


        try:

            content = self._read_markdown(
                file_path
            )


            # Find Markdown headings
            # Example:
            # # Title
            # ## Section
            sections = re.findall(
                r"^#+\s+(.+)$",
                content,
                re.MULTILINE,
            )


            logger.info(
                "Extracted markdown: %s (%s chars)",
                file_path.name,
                len(content)
            )


            return ExtractionResult(

                pages=[
                    PageText(
                        page_number=1,
                        text=content,
                        full_text=content,
                    )
                ],

                full_text=content,

                metadata={

                    "title": file_path.stem,

                    "author": "",

                    "page_count": 1,

                    "line_count":
                        content.count("\n") + 1,

                    # Required by tests
                    # and useful for future UI
                    "section_count": sections,
                },
            )


        except Exception as e:

            logger.exception(e)

            raise DocumentExtractionError(
                f"Failed to extract markdown: {e}"
            ) from e



    def _read_markdown(
        self,
        file_path: Path
    ) -> str:
        """
        Read Markdown with encoding fallback.
        """

        for encoding in [
            "utf-8",
            "latin-1",
            "cp1252",
            "utf-16",
        ]:

            try:
                return file_path.read_text(
                    encoding=encoding
                )

            except UnicodeDecodeError:
                continue


        raise DocumentExtractionError(
            f"Unable to decode markdown: {file_path}"
        )