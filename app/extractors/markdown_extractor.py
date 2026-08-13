"""
Markdown Extractor

Responsibilities:
- Read markdown files
- Return plain text
- Extract heading sections for metadata
"""

import re
from pathlib import Path

from app.extractors.base import ExtractionResult


class MarkdownExtractor:
    """
    Extract text and heading information from Markdown files.
    """

    def extract(self, path: Path) -> ExtractionResult:
        """
        Extract markdown content.
        """

        text = path.read_text(
            encoding="utf-8"
        )


        # Collect markdown headings
        sections = re.findall(
            r"^#+\s+(.+)$",
            text,
            re.MULTILINE
        )


        return ExtractionResult(
            text=text,
            metadata={
                # Tests/UI expect this collection
                "section_count": sections,
            }
        )