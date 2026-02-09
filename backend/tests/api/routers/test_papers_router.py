"""Tests for papers management router."""


class TestPapersAuthentication:
    """Tests for papers endpoint authentication."""

    def test_list_papers_unauthenticated_allowed(self, unauthenticated_client, mock_paper_repo):
        """Test that unauthenticated list requests are allowed."""
        mock_paper_repo.get_all.return_value = ([], 0)

        response = unauthenticated_client.get("/api/v1/papers")

        assert response.status_code == 200

    def test_get_paper_unauthenticated_requires_auth(self, unauthenticated_client):
        """Test that unauthenticated detail requests return 401."""
        response = unauthenticated_client.get("/api/v1/papers/2301.00001")

        assert response.status_code == 401


class TestListPapersEndpoint:
    """Tests for GET /api/v1/papers endpoint."""

    def test_list_papers_empty(self, client, mock_paper_repo):
        """Test listing papers returns empty list."""
        mock_paper_repo.get_all.return_value = ([], 0)

        response = client.get("/api/v1/papers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["papers"] == []
        assert data["offset"] == 0
        assert data["limit"] == 20

    def test_list_papers_with_results(self, client, mock_paper_repo, sample_paper):
        """Test listing papers returns results."""
        mock_paper_repo.get_all.return_value = ([sample_paper], 1)

        response = client.get("/api/v1/papers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["papers"]) == 1
        assert data["papers"][0]["arxiv_id"] == "2301.00001"
        assert data["papers"][0]["title"] == "Test Paper Title"

    def test_list_papers_pagination(self, client, mock_paper_repo):
        """Test pagination parameters are passed correctly."""
        mock_paper_repo.get_all.return_value = ([], 100)

        response = client.get("/api/v1/papers?offset=20&limit=50")

        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 20
        assert data["limit"] == 50

        # Verify repository was called with correct params
        mock_paper_repo.get_all.assert_called_once()
        call_kwargs = mock_paper_repo.get_all.call_args.kwargs
        assert call_kwargs["offset"] == 20
        assert call_kwargs["limit"] == 50

    def test_list_papers_with_category_filter(self, client, mock_paper_repo):
        """Test filtering by category."""
        mock_paper_repo.get_all.return_value = ([], 0)

        response = client.get("/api/v1/papers?category=cs.LG")

        assert response.status_code == 200
        call_kwargs = mock_paper_repo.get_all.call_args.kwargs
        assert call_kwargs["category_filter"] == "cs.LG"

    def test_list_papers_with_author_filter(self, client, mock_paper_repo):
        """Test filtering by author."""
        mock_paper_repo.get_all.return_value = ([], 0)

        response = client.get("/api/v1/papers?author=John")

        assert response.status_code == 200
        call_kwargs = mock_paper_repo.get_all.call_args.kwargs
        assert call_kwargs["author_filter"] == "John"

    def test_list_papers_with_processed_only_filter(self, client, mock_paper_repo):
        """Test filtering by processed status."""
        mock_paper_repo.get_all.return_value = ([], 0)

        response = client.get("/api/v1/papers?processed_only=true")

        assert response.status_code == 200
        call_kwargs = mock_paper_repo.get_all.call_args.kwargs
        assert call_kwargs["processed_only"] is True

    def test_list_papers_with_sorting(self, client, mock_paper_repo):
        """Test sorting parameters."""
        mock_paper_repo.get_all.return_value = ([], 0)

        response = client.get("/api/v1/papers?sort_by=published_date&sort_order=asc")

        assert response.status_code == 200
        call_kwargs = mock_paper_repo.get_all.call_args.kwargs
        assert call_kwargs["sort_by"] == "published_date"
        assert call_kwargs["sort_order"] == "asc"

    def test_list_papers_invalid_limit(self, client):
        """Test validation error for invalid limit."""
        response = client.get("/api/v1/papers?limit=200")

        assert response.status_code == 422

    def test_list_papers_invalid_offset(self, client):
        """Test validation error for negative offset."""
        response = client.get("/api/v1/papers?offset=-1")

        assert response.status_code == 422


class TestGetPaperEndpoint:
    """Tests for GET /api/v1/papers/{arxiv_id} endpoint."""

    def test_get_paper_found(self, client, mock_paper_repo, sample_paper):
        """Test getting a paper that exists."""
        mock_paper_repo.get_by_arxiv_id.return_value = sample_paper

        response = client.get("/api/v1/papers/2301.00001")

        assert response.status_code == 200
        data = response.json()
        assert data["arxiv_id"] == "2301.00001"
        assert data["title"] == "Test Paper Title"
        assert data["authors"] == ["Author One", "Author Two"]

    def test_get_paper_not_found(self, client, mock_paper_repo):
        """Test getting a paper that doesn't exist."""
        mock_paper_repo.get_by_arxiv_id.return_value = None

        response = client.get("/api/v1/papers/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()

    def test_get_paper_includes_raw_text(self, client, mock_paper_repo, sample_paper):
        """Test that raw_text is included in single paper response."""
        mock_paper_repo.get_by_arxiv_id.return_value = sample_paper

        response = client.get("/api/v1/papers/2301.00001")

        assert response.status_code == 200
        data = response.json()
        assert data["raw_text"] == "Raw text content of the paper."
