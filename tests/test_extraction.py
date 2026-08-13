"""
Tests for extraction.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pathlib import Path
from app.extractors.base import DocumentExtractor, ExtractionResult, PageText, DocumentExtractionError
from app.extractors.pdf_extractor import PDFExtractor
from app.extractors.docx_extractor import DOCXExtractor
from app.extractors.text_extractor import TextExtractor, MarkdownExtractor
from app.extractors import ExtractorRegistry


class TestDocumentExtractorBase:
    """Tests for the base DocumentExtractor class."""

    def test_abstract_class_cannot_be_instantiated(self):
        """Test that abstract base class cannot be instantiated."""
        with pytest.raises(TypeError):
            DocumentExtractor()


class TestExtractionResult:
    """Tests for ExtractionResult."""

    def test_creation(self):
        """Test creating an ExtractionResult."""
        result = ExtractionResult(
            full_text="Page 1 content\n\nPage 2 content",
            pages=[
                PageText(page_number=1, text="Page 1 content", full_text="Page 1 content"),
                PageText(page_number=2, text="Page 2 content", full_text="Page 2 content"),
            ],
            metadata={"title": "Test Document"},
        )

        assert result.text == "Page 1 content\n\nPage 2 content"
        assert len(result.pages) == 2
        assert result.pages[0].page_number == 1
        assert result.pages[0].text == "Page 1 content"
        assert result.metadata["title"] == "Test Document"

    def test_empty_result(self):
        """Test creating an empty ExtractionResult."""
        result = ExtractionResult(full_text="", pages=[], metadata={})

        assert result.text == ""
        assert len(result.pages) == 0


class TestPageText:
    """Tests for PageText."""

    def test_creation(self):
        """Test creating a PageText."""
        page = PageText(page_number=1, text="Test content", full_text="Test content")

        assert page.page_number == 1
        assert page.text == "Test content"


class TestTextExtractor:
    """Tests for text file extraction."""

    def test_extract_txt_file(self, tmp_path):
        """Test extracting text from a .txt file."""
        extractor = TextExtractor()

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello world\nThis is a test document.")

        result = extractor.extract(txt_file)

        assert result.text == "Hello world\nThis is a test document."
        assert len(result.pages) == 1
        assert result.pages[0].page_number == 1
        assert result.pages[0].text == "Hello world\nThis is a test document."
        assert result.metadata["line_count"] == 2

    def test_extract_empty_txt_file(self, tmp_path):
        """Test extracting from an empty text file."""
        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("")

        result = TextExtractor().extract(txt_file)

        assert result.text == ""
        assert len(result.pages) == 1
        assert result.pages[0].text == ""

    def test_extract_utf8_file(self, tmp_path):
        """Test extracting UTF-8 encoded text."""
        txt_file = tmp_path / "utf8.txt"
        txt_file.write_text("Café résumé naïve", encoding="utf-8")

        result = TextExtractor().extract(txt_file)

        assert "Café" in result.text

    def test_extract_large_file(self, tmp_path):
        """
        Test that large text files are handled correctly.

        Ensures extractor does not truncate content.
        """

        txt_file = tmp_path / "large.txt"

        # Create content larger than 10,000 characters
        large_text = (
            "This is a test line with sample content. "
            * 1000
        )

        txt_file.write_text(
            large_text,
            encoding="utf-8"
        )

        result = TextExtractor().extract(
            txt_file
        )

        # Full content must be preserved
        assert len(result.full_text) > 10000

        # Single line because we did not add newline characters
        assert result.metadata["line_count"] == 1


class TestMarkdownExtractor:
    """Tests for Markdown file extraction."""

    def test_extract_md_file(self, tmp_path):
        """Test extracting from a .md file."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Title\n\n## Section\n\nContent here\n\n## Another\n\nMore content")

        result = MarkdownExtractor().extract(md_file)

        assert "Title" in result.text
        assert "Section" in result.text
        assert len(result.metadata["section_count"]) > 0

    def test_extract_markdown_heading(self, tmp_path):
        """Test extracting markdown headings."""
        md_file = tmp_path / "headings.md"
        md_file.write_text("# Level 1\n## Level 2\n### Level 3\n\nContent")

        result = MarkdownExtractor().extract(md_file)

        assert len(result.metadata["section_count"]) == 3
        assert "Level 1" in result.metadata["section_count"]
        assert "Level 2" in result.metadata["section_count"]
        assert "Level 3" in result.metadata["section_count"]

    def test_extract_markdown_empty(self, tmp_path):
        """Test extracting empty markdown file."""
        md_file = tmp_path / "empty.md"
        md_file.write_text("")

        result = MarkdownExtractor().extract(md_file)

        assert result.text == ""

    def test_extract_markdown_links(self, tmp_path):
        """Test extracting markdown with links."""
        md_file = tmp_path / "links.md"
        md_file.write_text("[Link](http://example.com)\n\n[Another](http://test.com)")

        result = MarkdownExtractor().extract(md_file)

        assert "[Link]" in result.text
        assert "[Another]" in result.text


class TestSupportedFileTypes:
    """Tests for supported file type detection."""

    def test_pdf_extractor_supported_types(self):
        """Test PDF extractor supported extensions."""
        extractor = PDFExtractor()
        assert ".pdf" in extractor.supported_extensions

    def test_docx_extractor_supported_types(self):
        """Test DOCX extractor supported extensions."""
        extractor = DOCXExtractor()
        assert ".docx" in extractor.supported_extensions
        assert ".doc" in extractor.supported_extensions

    def test_text_extractor_supported_types(self):
        """Test Text extractor supported extensions."""
        extractor = TextExtractor()
        assert ".txt" in extractor.supported_extensions
        assert ".text" in extractor.supported_extensions

    def test_markdown_extractor_supported_types(self):
        """Test Markdown extractor supported extensions."""
        extractor = MarkdownExtractor()
        assert ".md" in extractor.supported_extensions
        assert ".markdown" in extractor.supported_extensions
        assert ".mkd" in extractor.supported_extensions


class TestExtractorRegistry:
    """Tests for the ExtractorRegistry."""

    def test_get_supported_extensions(self):
        """Test retrieving supported extensions from registry."""
        registry = ExtractorRegistry()
        from app.extractors import create_default_registry
        default = create_default_registry()
        assert ".pdf" in default.get_supported_extensions()

    def test_get_extractor_for_pdf(self):
        """Test getting PDF extractor from registry."""
        from app.extractors import create_default_registry
        registry = create_default_registry()
        extractor = registry.get_extractor(".pdf")
        assert extractor is not None

    def test_get_extractor_for_txt(self):
        """Test getting TXT extractor from registry."""
        from app.extractors import create_default_registry
        registry = create_default_registry()
        extractor = registry.get_extractor(".txt")
        assert extractor is not None

    def test_get_extractor_for_md(self):
        """Test getting MD extractor from registry."""
        from app.extractors import create_default_registry
        registry = create_default_registry()
        extractor = registry.get_extractor(".md")
        assert extractor is not None

    def test_unsupported_extension_returns_none(self):
        """Test that unsupported extensions return None."""
        from app.extractors import create_default_registry
        registry = create_default_registry()
        extractor = registry.get_extractor("xyz")
        assert extractor is None
