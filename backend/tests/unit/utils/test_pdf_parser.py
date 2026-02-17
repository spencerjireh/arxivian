"""Tests for PDFParser null byte handling."""

from unittest.mock import MagicMock, patch

import pytest

from src.utils.pdf_parser import PDFParser


def _make_page(text: str) -> MagicMock:
    """Build a mock pypdf page that returns the given text."""
    page = MagicMock()
    page.extract_text.return_value = text
    return page


@pytest.fixture
def parser() -> PDFParser:
    return PDFParser()


class TestNullByteStripping:
    """pypdf sometimes returns \\x00 from malformed font tables.

    PostgreSQL TEXT columns reject null bytes, so the parser must strip
    them before any downstream consumer sees the text.
    """

    @pytest.mark.asyncio
    async def test_null_bytes_stripped_from_raw_text(self, parser: PDFParser):
        pages = [_make_page("Hello\x00 world\x00")]
        reader = MagicMock()
        reader.pages = pages

        with patch("pypdf.PdfReader", return_value=reader):
            result = await parser.parse_pdf("/fake/path.pdf")

        assert "\x00" not in result.raw_text
        assert "Hello world" in result.raw_text

    @pytest.mark.asyncio
    async def test_null_bytes_stripped_from_sections(self, parser: PDFParser):
        pages = [_make_page("Section\x00 content")]
        reader = MagicMock()
        reader.pages = pages

        with patch("pypdf.PdfReader", return_value=reader):
            result = await parser.parse_pdf("/fake/path.pdf")

        assert "\x00" not in result.sections[0]["content"]
        assert "Section content" in result.sections[0]["content"]

    @pytest.mark.asyncio
    async def test_clean_text_unchanged(self, parser: PDFParser):
        pages = [_make_page("No null bytes here")]
        reader = MagicMock()
        reader.pages = pages

        with patch("pypdf.PdfReader", return_value=reader):
            result = await parser.parse_pdf("/fake/path.pdf")

        assert "No null bytes here" in result.raw_text

    @pytest.mark.asyncio
    async def test_multiple_pages_all_stripped(self, parser: PDFParser):
        pages = [
            _make_page("Page\x00 one"),
            _make_page("Page\x00 two"),
        ]
        reader = MagicMock()
        reader.pages = pages

        with patch("pypdf.PdfReader", return_value=reader):
            result = await parser.parse_pdf("/fake/path.pdf")

        assert "\x00" not in result.raw_text
        assert "Page one" in result.raw_text
        assert "Page two" in result.raw_text
        assert len(result.sections) == 2
        for section in result.sections:
            assert "\x00" not in section["content"]
