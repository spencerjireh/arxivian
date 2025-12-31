"""Shared pytest fixtures for service tests."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone


@pytest.fixture
def mock_search_repository():
    """Create a mock SearchRepository."""
    repo = AsyncMock()
    repo.vector_search = AsyncMock(return_value=[])
    repo.fulltext_search = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_embeddings_client():
    """Create a mock JinaEmbeddingsClient."""
    client = AsyncMock()
    client.embed_query = AsyncMock(return_value=[0.1] * 1024)
    client.embed_documents = AsyncMock(return_value=[[0.1] * 1024])
    return client


@pytest.fixture
def mock_arxiv_client():
    """Create a mock ArxivClient."""
    client = AsyncMock()
    client.search_papers = AsyncMock(return_value=[])
    client.get_papers_by_ids = AsyncMock(return_value=[])
    client.download_pdf = AsyncMock()
    return client


@pytest.fixture
def mock_pdf_parser():
    """Create a mock PDFParser."""
    parser = AsyncMock()
    parser.parse_pdf = AsyncMock()
    return parser


@pytest.fixture
def mock_chunking_service():
    """Create a mock ChunkingService."""
    service = Mock()
    service.chunk_document = Mock(return_value=[])
    return service


@pytest.fixture
def mock_paper_repository():
    """Create a mock PaperRepository."""
    repo = AsyncMock()
    repo.session = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_arxiv_id = AsyncMock(return_value=None)
    repo.get_by_arxiv_id_for_update = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock(return_value=True)
    repo.get_all = AsyncMock(return_value=([], 0))
    return repo


@pytest.fixture
def mock_chunk_repository():
    """Create a mock ChunkRepository."""
    repo = AsyncMock()
    repo.create_bulk = AsyncMock(return_value=[])
    repo.get_by_paper_id = AsyncMock(return_value=[])
    repo.delete_by_paper_id = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def sample_arxiv_paper():
    """Create a sample ArxivPaper-like object."""
    paper = Mock()
    paper.arxiv_id = "2301.00001"
    paper.title = "Test Paper Title"
    paper.authors = ["Author One", "Author Two"]
    paper.abstract = "This is a test abstract for unit testing purposes."
    paper.categories = ["cs.LG", "cs.AI"]
    paper.published_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    paper.pdf_url = "https://arxiv.org/pdf/2301.00001.pdf"
    return paper


@pytest.fixture
def sample_parsed_pdf():
    """Create a sample parsed PDF result."""
    result = Mock()
    result.raw_text = "This is the raw text content of the paper. " * 100
    result.sections = [
        {"name": "Introduction", "text": "Introduction text."},
        {"name": "Methods", "text": "Methods text."},
        {"name": "Conclusion", "text": "Conclusion text."},
    ]
    return result


@pytest.fixture
def sample_chunks():
    """Create sample chunk objects."""
    chunks = []
    for i in range(3):
        chunk = Mock()
        chunk.text = f"Chunk {i} text content."
        chunk.chunk_index = i
        chunk.section_name = "Introduction" if i == 0 else "Methods"
        chunk.page_number = i + 1
        chunk.word_count = 5
        chunks.append(chunk)
    return chunks


@pytest.fixture
def sample_search_result():
    """Create a sample SearchResult-like object."""
    from src.repositories.search_repository import SearchResult

    return SearchResult(
        chunk_id="chunk-uuid-1",
        paper_id="paper-uuid-1",
        arxiv_id="2301.00001",
        title="Test Paper",
        authors=["Author One"],
        chunk_text="Sample chunk text for testing.",
        section_name="Introduction",
        page_number=1,
        score=0.95,
        vector_score=0.95,
        text_score=None,
        published_date="2023-01-01",
        pdf_url="https://arxiv.org/pdf/2301.00001.pdf",
    )
