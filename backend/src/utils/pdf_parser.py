"""PDF parser service using Docling."""

from typing import Dict, List
from dataclasses import dataclass
import asyncio


@dataclass
class ParsedDocument:
    """Parsed PDF document with structure."""

    raw_text: str
    sections: List[Dict]
    references: List[str]
    metadata: Dict


class PDFParser:
    """Parser for extracting text and structure from PDFs."""

    def __init__(self):
        """Initialize PDF parser."""
        pass

    async def parse_pdf(self, pdf_path: str) -> ParsedDocument:
        """
        Parse PDF and extract structured content.

        Args:
            pdf_path: Path to PDF file

        Returns:
            ParsedDocument with text, sections, and metadata
        """
        # Run blocking operation in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._parse_pdf_sync, pdf_path)

    def _parse_pdf_sync(self, pdf_path: str) -> ParsedDocument:
        """
        Synchronous PDF parsing (runs in thread pool).

        This is a simplified implementation. In production, you would use
        Docling library for advanced parsing of academic papers.
        """
        try:
            # For now, use simple pypdf fallback
            from pypdf import PdfReader

            reader = PdfReader(pdf_path)
            raw_text = ""
            sections = []

            # Extract text from all pages
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()
                raw_text += page_text + "\n\n"

                # Simple section detection (in production, use Docling)
                sections.append(
                    {
                        "title": f"Page {page_num}",
                        "content": page_text,
                        "page_start": page_num,
                        "page_end": page_num,
                    }
                )

            # Extract metadata
            metadata = {"parser": "pypdf", "pages": len(reader.pages), "file_path": pdf_path}

            # Simple reference extraction (look for common patterns)
            references = self._extract_references(raw_text)

            return ParsedDocument(
                raw_text=raw_text.strip(),
                sections=sections,
                references=references,
                metadata=metadata,
            )

        except Exception as e:
            # Fallback: return basic structure
            return ParsedDocument(
                raw_text=f"Error parsing PDF: {str(e)}",
                sections=[],
                references=[],
                metadata={"error": str(e), "parser": "fallback"},
            )

    def _extract_references(self, text: str) -> List[str]:
        """
        Extract references from text.

        This is a simplified implementation. In production, use
        proper citation parsing.
        """
        references = []

        # Look for common reference patterns
        lines = text.split("\n")
        in_references = False

        for line in lines:
            line = line.strip()

            # Detect references section
            if line.lower() in ["references", "bibliography", "works cited"]:
                in_references = True
                continue

            # Extract reference lines
            if in_references and line:
                # Simple heuristic: lines that start with [number] or author names
                if line[0].isdigit() or line[0] == "[":
                    references.append(line)

        return references[:50]  # Limit to first 50 references
