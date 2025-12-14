"""Text chunking service for splitting documents into retrievable chunks."""

from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class TextChunk:
    """A chunk of text with metadata."""

    text: str
    chunk_index: int
    section_name: Optional[str] = None
    page_number: Optional[int] = None
    word_count: int = 0


class ChunkingService:
    """Service for chunking documents into overlapping text segments."""

    def __init__(
        self, target_words: int = 600, overlap_words: int = 100, min_chunk_words: int = 100
    ):
        """
        Initialize chunking service.

        Args:
            target_words: Target words per chunk
            overlap_words: Words to overlap between chunks
            min_chunk_words: Minimum words for a valid chunk
        """
        self.target_words = target_words
        self.overlap_words = overlap_words
        self.min_chunk_words = min_chunk_words

    def chunk_document(self, text: str, sections: Optional[List[Dict]] = None) -> List[TextChunk]:
        """
        Chunk document with section-awareness.

        Args:
            text: Full document text
            sections: Optional list of sections with {title, content, page_start, page_end}

        Returns:
            List of TextChunk objects
        """
        if sections:
            return self._chunk_with_sections(sections)
        else:
            return self._chunk_plain_text(text)

    def _chunk_plain_text(self, text: str) -> List[TextChunk]:
        """Chunk plain text without section boundaries."""
        words = text.split()
        chunks = []
        chunk_index = 0

        i = 0
        while i < len(words):
            # Get chunk of target size
            chunk_words = words[i : i + self.target_words]

            # Skip if too small (unless it's the last chunk)
            if len(chunk_words) < self.min_chunk_words and i + self.target_words < len(words):
                i += self.target_words - self.overlap_words
                continue

            chunk_text = " ".join(chunk_words)
            chunks.append(
                TextChunk(text=chunk_text, chunk_index=chunk_index, word_count=len(chunk_words))
            )

            chunk_index += 1

            # Move forward with overlap
            i += self.target_words - self.overlap_words

        return chunks

    def _chunk_with_sections(self, sections: List[Dict]) -> List[TextChunk]:
        """Chunk text respecting section boundaries."""
        chunks = []
        chunk_index = 0

        for section in sections:
            section_name = section.get("title", "Unknown")
            section_content = section.get("content", "")
            page_start = section.get("page_start")

            # Chunk this section
            words = section_content.split()

            i = 0
            while i < len(words):
                chunk_words = words[i : i + self.target_words]

                # Skip tiny chunks unless last in section
                if len(chunk_words) < self.min_chunk_words and i + self.target_words < len(words):
                    i += self.target_words - self.overlap_words
                    continue

                chunk_text = " ".join(chunk_words)
                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        chunk_index=chunk_index,
                        section_name=section_name,
                        page_number=page_start,
                        word_count=len(chunk_words),
                    )
                )

                chunk_index += 1
                i += self.target_words - self.overlap_words

        return chunks

    def estimate_chunks(self, text: str) -> int:
        """Estimate number of chunks for a text."""
        word_count = len(text.split())
        step_size = self.target_words - self.overlap_words
        return max(1, (word_count - self.overlap_words) // step_size)
