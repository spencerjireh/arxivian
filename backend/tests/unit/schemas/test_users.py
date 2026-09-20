"""Tests for FeedProfile / UpdatePreferencesRequest."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.schemas.users import FeedProfile, UpdatePreferencesRequest


@pytest.mark.unit
class TestFeedProfile:
    def test_from_user_tolerates_missing_and_garbage(self):
        assert FeedProfile.from_user(SimpleNamespace(preferences=None)).categories == []
        assert FeedProfile.from_user(SimpleNamespace(preferences={})).onboarded is False
        bad = SimpleNamespace(preferences={"feed_profile": {"compute_profile": "mainframe"}})
        assert FeedProfile.from_user(bad) == FeedProfile()

    def test_onboarded_needs_categories_and_compute(self):
        assert FeedProfile(categories=["cs.LG"]).onboarded is False
        assert FeedProfile(compute_profile="laptop").onboarded is False
        assert FeedProfile(categories=["cs.LG"], compute_profile="laptop").onboarded is True

    def test_ignores_unknown_keys(self):
        profile = FeedProfile.model_validate({"categories": ["cs.LG"], "future": 1})
        assert profile.categories == ["cs.LG"]


@pytest.mark.unit
class TestUpdatePreferencesRequest:
    def test_normalizes(self):
        req = UpdatePreferencesRequest(
            categories=["cs.LG", " cs.AI ", "cs.LG"],
            compute_profile="laptop",
            keywords=["RAG", "rag", " sparse "],
        )
        assert req.categories == ["cs.AI", "cs.LG"]
        assert req.keywords == ["rag", "sparse"]

    def test_rejects_bad_category_and_extra(self):
        with pytest.raises(ValidationError):
            UpdatePreferencesRequest(categories=["cs LG"], compute_profile="laptop")
        with pytest.raises(ValidationError):
            UpdatePreferencesRequest(categories=["cs.LG"], compute_profile="laptop", weights={})
        with pytest.raises(ValidationError):
            UpdatePreferencesRequest(categories=["  "], compute_profile="laptop")
