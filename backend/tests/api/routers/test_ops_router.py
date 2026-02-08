"""Tests for ops router."""

from unittest.mock import Mock


class TestCleanupEndpoint:
    """Tests for POST /api/v1/ops/cleanup endpoint."""

    def test_cleanup_no_orphaned_papers(self, client, mock_paper_repo):
        """Test cleanup when no orphaned papers exist."""
        mock_paper_repo.get_orphaned_papers.return_value = []

        response = client.post("/api/v1/ops/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["orphaned_papers_found"] == 0
        assert data["papers_deleted"] == 0
        assert data["deleted_papers"] == []

    def test_cleanup_with_orphaned_papers(self, client, mock_paper_repo):
        """Test cleanup deletes orphaned papers."""
        orphaned_paper = Mock()
        orphaned_paper.id = "paper-uuid-1"
        orphaned_paper.arxiv_id = "2301.00001"
        orphaned_paper.title = "Orphaned Paper"

        mock_paper_repo.get_orphaned_papers.return_value = [orphaned_paper]

        response = client.post("/api/v1/ops/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["orphaned_papers_found"] == 1
        assert data["papers_deleted"] == 1
        assert len(data["deleted_papers"]) == 1
        assert data["deleted_papers"][0]["arxiv_id"] == "2301.00001"

    def test_cleanup_multiple_orphaned_papers(self, client, mock_paper_repo):
        """Test cleanup with multiple orphaned papers."""
        orphaned_papers = []
        for i in range(3):
            paper = Mock()
            paper.id = f"paper-uuid-{i}"
            paper.arxiv_id = f"2301.0000{i}"
            paper.title = f"Orphaned Paper {i}"
            orphaned_papers.append(paper)

        mock_paper_repo.get_orphaned_papers.return_value = orphaned_papers

        response = client.post("/api/v1/ops/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["orphaned_papers_found"] == 3
        assert data["papers_deleted"] == 3
        assert len(data["deleted_papers"]) == 3

    def test_cleanup_calls_delete_for_each_paper(self, client, mock_paper_repo):
        """Test that delete is called for each orphaned paper."""
        orphaned_paper = Mock()
        orphaned_paper.id = "paper-uuid-1"
        orphaned_paper.arxiv_id = "2301.00001"
        orphaned_paper.title = "Orphaned Paper"

        mock_paper_repo.get_orphaned_papers.return_value = [orphaned_paper]

        response = client.post("/api/v1/ops/cleanup")

        assert response.status_code == 200
        mock_paper_repo.delete.assert_called_once_with("paper-uuid-1")

    def test_cleanup_truncates_long_titles(self, client, mock_paper_repo):
        """Test that long titles are truncated in response."""
        orphaned_paper = Mock()
        orphaned_paper.id = "paper-uuid-1"
        orphaned_paper.arxiv_id = "2301.00001"
        orphaned_paper.title = "A" * 200  # Very long title

        mock_paper_repo.get_orphaned_papers.return_value = [orphaned_paper]

        response = client.post("/api/v1/ops/cleanup")

        assert response.status_code == 200
        data = response.json()
        # Title should be truncated to 100 characters
        assert len(data["deleted_papers"][0]["title"]) == 100


class TestOpsAuthentication:
    """Tests for ops endpoint API key authentication."""

    def test_missing_api_key_returns_401(self, unauthenticated_client):
        """Test that missing API key returns 401."""
        response = unauthenticated_client.post("/api/v1/ops/cleanup")
        assert response.status_code == 401

    def test_invalid_api_key_returns_401(self, unauthenticated_client):
        """Test that an invalid API key returns 401."""
        response = unauthenticated_client.post(
            "/api/v1/ops/cleanup",
            headers={"X-Api-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_valid_api_key_returns_200(self, unauthenticated_client, mock_paper_repo):
        """Test that a valid API key authenticates successfully."""
        mock_paper_repo.get_orphaned_papers.return_value = []
        response = unauthenticated_client.post(
            "/api/v1/ops/cleanup",
            headers={"X-Api-Key": "test-api-key"},
        )
        assert response.status_code == 200
