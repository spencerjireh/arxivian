"""Tests for confirm_ingest_node."""

import pytest
from unittest.mock import AsyncMock, patch


class TestConfirmIngestNode:
    """Tests for confirm_ingest_node HITL interrupt point."""

    @pytest.fixture
    def base_state(self):
        return {
            "pause_reason": "propose_ingest_confirmation",
            "pause_data": {
                "papers": [
                    {"arxiv_id": "2301.00001", "title": "Paper A"},
                    {"arxiv_id": "2301.00002", "title": "Paper B"},
                ],
                "proposed_ids": ["2301.00001", "2301.00002"],
            },
            "tool_outputs": [],
        }

    @pytest.fixture
    def config(self):
        return {"configurable": {}}

    # ------------------------------------------------------------------
    # 1. Calls interrupt with pause_data
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.confirm_ingest.interrupt")
    async def test_calls_interrupt_with_pause_data(self, mock_interrupt, base_state, config):
        """interrupt() is called with the state's pause_data."""
        from src.services.agent_service.nodes.confirm_ingest import confirm_ingest_node

        mock_interrupt.return_value = {"declined": False, "papers_processed": 2}

        await confirm_ingest_node(base_state, config)

        mock_interrupt.assert_called_once_with(base_state["pause_data"])

    # ------------------------------------------------------------------
    # 2. Approved resume writes to tool_outputs
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.confirm_ingest.interrupt")
    async def test_approved_resume_writes_to_tool_outputs(
        self, mock_interrupt, base_state, config
    ):
        """When the user approves, tool_outputs has an entry with papers_processed."""
        from src.services.agent_service.nodes.confirm_ingest import confirm_ingest_node

        mock_interrupt.return_value = {"declined": False, "papers_processed": 3}

        result = await confirm_ingest_node(base_state, config)

        assert len(result["tool_outputs"]) == 1
        entry = result["tool_outputs"][0]
        assert entry["tool_name"] == "confirm_ingest"
        assert entry["data"]["declined"] is False
        assert entry["data"]["papers_processed"] == 3
        assert "approved" in entry["prompt_text"].lower()
        assert "3" in entry["prompt_text"]

    # ------------------------------------------------------------------
    # 3. Declined resume writes to tool_outputs
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.confirm_ingest.interrupt")
    async def test_declined_resume_writes_to_tool_outputs(
        self, mock_interrupt, base_state, config
    ):
        """When the user declines, prompt_text mentions the decline."""
        from src.services.agent_service.nodes.confirm_ingest import confirm_ingest_node

        mock_interrupt.return_value = {"declined": True}

        result = await confirm_ingest_node(base_state, config)

        assert len(result["tool_outputs"]) == 1
        entry = result["tool_outputs"][0]
        assert entry["tool_name"] == "confirm_ingest"
        assert entry["data"]["declined"] is True
        assert "declined" in entry["prompt_text"].lower()

    # ------------------------------------------------------------------
    # 4. Clears pause state
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.confirm_ingest.interrupt")
    async def test_clears_pause_state(self, mock_interrupt, base_state, config):
        """Both pause_reason and pause_data are None in the returned updates."""
        from src.services.agent_service.nodes.confirm_ingest import confirm_ingest_node

        mock_interrupt.return_value = {"declined": False, "papers_processed": 1}

        result = await confirm_ingest_node(base_state, config)

        assert result["pause_reason"] is None
        assert result["pause_data"] is None
