"""Tests for evaluate_batch node."""

import pytest
from unittest.mock import AsyncMock

from src.schemas.langgraph_state import BatchEvaluation
from src.services.agent_service.nodes.evaluate_batch import _chunk_fingerprints


class TestChunkFingerprints:
    """Tests for the _chunk_fingerprints helper."""

    def test_empty(self):
        assert _chunk_fingerprints([]) == []

    def test_single(self):
        result = _chunk_fingerprints([{"arxiv_id": "1234.5678", "chunk_text": "hello"}])
        assert result == ["1234.5678:hello"]

    def test_sorted(self):
        chunks = [
            {"arxiv_id": "B", "chunk_text": "second"},
            {"arxiv_id": "A", "chunk_text": "first"},
        ]
        result = _chunk_fingerprints(chunks)
        assert result == ["A:first", "B:second"]

    def test_missing_fields(self):
        result = _chunk_fingerprints([{}])
        assert result == ["unknown:"]

    def test_truncation(self):
        long_text = "x" * 200
        result = _chunk_fingerprints([{"arxiv_id": "id", "chunk_text": long_text}])
        # Fingerprint uses first 100 chars
        assert result == [f"id:{'x' * 100}"]


class TestEvaluateBatchNode:
    """Tests for evaluate_batch_node function."""

    @pytest.fixture
    def base_state(self):
        return {
            "original_query": "What is attention in transformers?",
            "rewritten_query": None,
            "retrieved_chunks": [
                {
                    "chunk_id": "c1",
                    "arxiv_id": "1706.03762",
                    "title": "Attention Is All You Need",
                    "chunk_text": "The dominant sequence transduction models...",
                },
                {
                    "chunk_id": "c2",
                    "arxiv_id": "1706.03762",
                    "title": "Attention Is All You Need",
                    "chunk_text": "Multi-head attention allows the model...",
                },
            ],
            "iteration": 1,
            "max_iterations": 5,
            "metadata": {"reasoning_steps": []},
        }

    @pytest.mark.asyncio
    async def test_sufficient_promotes_all_chunks(self, mock_context, make_config, base_state):
        from src.services.agent_service.nodes.evaluate_batch import evaluate_batch_node

        mock_context.llm_client.generate_structured = AsyncMock(
            return_value=BatchEvaluation(
                sufficient=True,
                reasoning="Chunks cover the topic well",
            )
        )

        result = await evaluate_batch_node(base_state, make_config)

        assert result["evaluation_result"].sufficient is True
        assert len(result["relevant_chunks"]) == 2
        assert result["relevant_chunks"] == base_state["retrieved_chunks"]

    @pytest.mark.asyncio
    async def test_insufficient_with_rewrite(self, mock_context, make_config, base_state):
        from src.services.agent_service.nodes.evaluate_batch import evaluate_batch_node

        mock_context.llm_client.generate_structured = AsyncMock(
            return_value=BatchEvaluation(
                sufficient=False,
                reasoning="Chunks discuss transformers but not attention mechanism specifically",
                suggested_rewrite="self-attention mechanism in transformer architecture",
            )
        )

        result = await evaluate_batch_node(base_state, make_config)

        assert result["evaluation_result"].sufficient is False
        assert result["rewritten_query"] == "self-attention mechanism in transformer architecture"
        assert result["relevant_chunks"] == []

    @pytest.mark.asyncio
    async def test_insufficient_max_iterations_promotes_all(
        self, mock_context, make_config, base_state
    ):
        from src.services.agent_service.nodes.evaluate_batch import evaluate_batch_node

        base_state["iteration"] = 5  # at max

        mock_context.llm_client.generate_structured = AsyncMock(
            return_value=BatchEvaluation(
                sufficient=False,
                reasoning="Not quite sufficient",
                suggested_rewrite="better query",
            )
        )

        result = await evaluate_batch_node(base_state, make_config)

        assert result["evaluation_result"].sufficient is False
        # Should promote all chunks anyway (best-effort)
        assert len(result["relevant_chunks"]) == 2
        # Should NOT set rewritten_query since we're at max iterations
        assert "rewritten_query" not in result

    @pytest.mark.asyncio
    async def test_empty_chunks_returns_insufficient(self, mock_context, make_config, base_state):
        from src.services.agent_service.nodes.evaluate_batch import evaluate_batch_node

        base_state["retrieved_chunks"] = []

        result = await evaluate_batch_node(base_state, make_config)

        assert result["evaluation_result"].sufficient is False
        assert result["relevant_chunks"] == []
        # LLM should NOT have been called
        mock_context.llm_client.generate_structured.assert_not_called()

    @pytest.mark.asyncio
    async def test_insufficient_no_rewrite_promotes_all(
        self, mock_context, make_config, base_state
    ):
        from src.services.agent_service.nodes.evaluate_batch import evaluate_batch_node

        mock_context.llm_client.generate_structured = AsyncMock(
            return_value=BatchEvaluation(
                sufficient=False,
                reasoning="Chunks are thin but no better query comes to mind",
                suggested_rewrite=None,
            )
        )

        result = await evaluate_batch_node(base_state, make_config)

        assert result["evaluation_result"].sufficient is False
        # No rewrite suggested -> promote all (best-effort)
        assert len(result["relevant_chunks"]) == 2

    @pytest.mark.asyncio
    async def test_reasoning_steps_updated(self, mock_context, make_config, base_state):
        from src.services.agent_service.nodes.evaluate_batch import evaluate_batch_node

        mock_context.llm_client.generate_structured = AsyncMock(
            return_value=BatchEvaluation(
                sufficient=True,
                reasoning="Good coverage",
            )
        )

        result = await evaluate_batch_node(base_state, make_config)

        steps = result["metadata"]["reasoning_steps"]
        assert len(steps) == 1
        assert "sufficient" in steps[0]

    @pytest.mark.asyncio
    async def test_stagnation_skips_llm(self, mock_context, make_config, base_state):
        """When chunks match previous fingerprints, skip LLM and return sufficient=True."""
        from src.services.agent_service.nodes.evaluate_batch import evaluate_batch_node

        # Pre-populate fingerprints matching the base_state chunks
        base_state["metadata"]["previous_chunk_fingerprints"] = _chunk_fingerprints(
            base_state["retrieved_chunks"]
        )

        result = await evaluate_batch_node(base_state, make_config)

        assert result["evaluation_result"].sufficient is True
        assert "identical chunks" in result["evaluation_result"].reasoning.lower()
        assert result["relevant_chunks"] == base_state["retrieved_chunks"]
        mock_context.llm_client.generate_structured.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_stagnation_when_chunks_differ(self, mock_context, make_config, base_state):
        """Different fingerprints should proceed to LLM evaluation normally."""
        from src.services.agent_service.nodes.evaluate_batch import evaluate_batch_node

        base_state["metadata"]["previous_chunk_fingerprints"] = ["different:fingerprint"]

        mock_context.llm_client.generate_structured = AsyncMock(
            return_value=BatchEvaluation(sufficient=True, reasoning="Good")
        )

        result = await evaluate_batch_node(base_state, make_config)

        mock_context.llm_client.generate_structured.assert_called_once()
        assert result["evaluation_result"].sufficient is True

    @pytest.mark.asyncio
    async def test_first_iteration_no_stagnation(self, mock_context, make_config, base_state):
        """First iteration has no previous fingerprints -- should call LLM and store them."""
        from src.services.agent_service.nodes.evaluate_batch import evaluate_batch_node

        # No previous_chunk_fingerprints in metadata (first iteration)
        assert "previous_chunk_fingerprints" not in base_state["metadata"]

        mock_context.llm_client.generate_structured = AsyncMock(
            return_value=BatchEvaluation(
                sufficient=False,
                reasoning="Insufficient",
                suggested_rewrite="better query",
            )
        )

        result = await evaluate_batch_node(base_state, make_config)

        mock_context.llm_client.generate_structured.assert_called_once()
        # Fingerprints should be stored for next iteration
        assert "previous_chunk_fingerprints" in result["metadata"]
        assert len(result["metadata"]["previous_chunk_fingerprints"]) == 2
