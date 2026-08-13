"""
Extractors package - lazy imports to avoid circular dependencies.
"""

from .base import DocumentExtractor, DocumentExtractionError, ExtractionResult, PageText, ExtractorRegistry, create_default_registry


def __getattr__(name):
    """Lazy import extractors on demand."""
    if name == "TextExtractor":
        from .text_extractor import TextExtractor
        return TextExtractor
    if name == "MarkdownExtractor":
        from .text_extractor import MarkdownExtractor
        return MarkdownExtractor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """Return list of available attributes for tab completion."""
    return [
        "DocumentExtractor",
        "DocumentExtractionError",
        "ExtractionResult",
        "PageText",
        "ExtractorRegistry",
        "TextExtractor",
        "MarkdownExtractor",
        "create_default_registry",
    ]
