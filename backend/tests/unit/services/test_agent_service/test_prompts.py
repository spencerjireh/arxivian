"""Tests for prompt templates and PromptBuilder."""

import json

import pytest

from src.services.agent_service.prompts import (
    ANSWER_SYSTEM_PROMPT,
    CLASSIFY_AND_ROUTE_SYSTEM_PROMPT,
    PromptBuilder,
)


class TestPromptBuilderToolOutputs:
    """Tests for PromptBuilder.with_tool_outputs."""

    def _make_output(self, tool_name: str, data: dict, prompt_text: str | None = None) -> dict:
        out: dict = {"tool_name": tool_name, "data": data}
        if prompt_text is not None:
            out["prompt_text"] = prompt_text
        return out

    def test_grouped_under_header(self):
        builder = PromptBuilder("system")
        builder.with_tool_outputs([
            self._make_output("arxiv_search", {}, prompt_text="Found 3 papers on transformers"),
        ])
        _, user = builder.build()
        assert user.startswith("Tool results:\n")
        assert "Found 3 papers on transformers" in user

    def test_retrieve_chunks_excluded(self):
        builder = PromptBuilder("system")
        builder.with_tool_outputs([
            self._make_output("retrieve_chunks", {"chunks": []}),
        ])
        _, user = builder.build()
        assert user == ""

    def test_multiple_under_single_header(self):
        builder = PromptBuilder("system")
        builder.with_tool_outputs([
            self._make_output("arxiv_search", {}, prompt_text="Paper A"),
            self._make_output("explore_citations", {}, prompt_text="Citation B"),
        ])
        _, user = builder.build()
        # Should be one "Tool results:" header, not two
        assert user.count("Tool results:") == 1
        assert "Paper A" in user
        assert "Citation B" in user

    def test_empty_adds_nothing(self):
        builder = PromptBuilder("system")
        builder.with_tool_outputs([])
        _, user = builder.build()
        assert user == ""

    def test_json_fallback(self):
        builder = PromptBuilder("system")
        data = {"key": "value", "count": 42}
        builder.with_tool_outputs([
            self._make_output("arxiv_search", data),
        ])
        _, user = builder.build()
        assert "Tool results:" in user
        assert json.dumps(data, default=str) in user


class TestClassifyAndRoutePromptContent:
    """Tests for CLASSIFY_AND_ROUTE_SYSTEM_PROMPT content."""

    def test_direct_intent_mentions_tool_results(self):
        """The SUFFICIENT CONTEXT rule must recognize tool results, not just retrieved passages."""
        assert "tool results" in CLASSIFY_AND_ROUTE_SYSTEM_PROMPT.lower()


class TestAnswerSystemPrompt:
    """Tests for ANSWER_SYSTEM_PROMPT content."""

    def test_mentions_tool_results(self):
        assert "tool results" in ANSWER_SYSTEM_PROMPT.lower()

    def test_no_chunks_in_sourcing_tiers(self):
        # "chunks" is an implementation detail; sourcing tiers should use "passages"/"context"
        # (the PRESENTATION RULES section intentionally names tools like retrieve_chunks)
        sourcing_section = ANSWER_SYSTEM_PROMPT.split("SOURCING TIERS")[1].split("HALLUCINATION")[0]
        assert "chunks" not in sourcing_section.lower()
