"""FeedService: read the cached digest and enrich it into ranked cards (SPE-274).

The digest row is only the candidate set and a bake-time default order. Everything the
card shows comes from the live `papers` + `paper_scores` rows (so a re-score is reflected
without a rebuild) plus the caller's `user_paper_states`. Personalization is applied here
at read time: composite weights, compute-profile match, keyword tie-break. Five queries per
page, no N+1: weeks, digest, papers IN, scores IN, states IN.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import ValidationError

from src.models.paper import Paper
from src.models.paper_score import PaperScore
from src.models.user import User
from src.models.user_paper_state import UserPaperState
from src.repositories.digest_repository import DigestRepository
from src.repositories.paper_repository import PaperRepository
from src.repositories.scoring_repository import ScoringRepository
from src.repositories.user_paper_state_repository import UserPaperStateRepository
from src.schemas.feed import AvailableWeek, FeedItem, FeedPaper, FeedResponse, LibraryResponse
from src.schemas.paper_states import UserPaperStateResponse
from src.schemas.papers import PaperScoreDetailResponse
from src.schemas.users import FeedProfile
from src.services.feed_service.derive import (
    build_attributes_detail,
    build_dimension_details,
    build_scores,
    build_signals,
    build_verdict,
    low_confidence_dimensions,
    parse_dimensions,
    resolve_weights,
)
from src.services.feed_service.digest import DigestRankingEntry, week_start_for
from src.services.scoring_service.state import RUBRIC_VERSION
from src.utils.logger import get_logger

log = get_logger(__name__)


class FeedService:
    """Ranked weekly feed over the cached digest snapshot."""

    def __init__(
        self,
        *,
        digest_repo: DigestRepository,
        scoring_repo: ScoringRepository,
        paper_repo: PaperRepository,
        state_repo: UserPaperStateRepository,
        category_key: str,
        rubric_version: str = RUBRIC_VERSION,
    ):
        self.digest_repo = digest_repo
        self.scoring_repo = scoring_repo
        self.paper_repo = paper_repo
        self.state_repo = state_repo
        self.category_key = category_key
        self.rubric_version = rubric_version

    async def get_feed(
        self,
        user: User,
        *,
        week: date | None = None,
        categories: list[str] | None = None,
        min_score: int | None = None,
        include_dismissed: bool = False,
        offset: int = 0,
        limit: int = 20,
    ) -> FeedResponse:
        """One page of ranked cards for a digest week (default: the newest built week)."""
        weeks = await self.digest_repo.list_weeks(self.category_key)
        available = [AvailableWeek(week_start=w, paper_count=n) for w, n in weeks]
        if not weeks:
            return FeedResponse(
                week_start=None,
                available_weeks=[],
                categories_available=[],
                total=0,
                offset=offset,
                limit=limit,
                items=[],
            )

        target = week_start_for(week) if week is not None else weeks[0][0]
        digest = await self.digest_repo.get_by_week(target, self.category_key)
        if digest is None:
            return FeedResponse(
                week_start=target,
                available_weeks=available,
                categories_available=[],
                total=0,
                offset=offset,
                limit=limit,
                items=[],
            )

        items = await self._enrich(user, digest.ranking)

        category_set = set(categories or [])
        if category_set:
            items = [i for i in items if category_set & set(i.paper.categories)]
        if min_score is not None:
            items = [i for i in items if _composite(i) >= min_score]
        if not include_dismissed:
            items = [i for i in items if i.state is None or i.state.state != "dismissed"]

        profile = FeedProfile.from_user(user)
        if profile.compute_profile is not None or profile.keywords:
            items.sort(
                key=lambda i: (
                    -(1 if i.signals is not None and i.signals.compute_match else 0),
                    -(1 if i.keyword_match else 0),
                    -_composite(i),
                )
            )
        else:
            items.sort(key=lambda i: -_composite(i))

        log.info(
            "feed_page_built",
            week_start=target.isoformat(),
            total=len(items),
            offset=offset,
            limit=limit,
            user_id=str(user.id),
        )
        return FeedResponse(
            week_start=target,
            available_weeks=available,
            categories_available=list(digest.categories or []),
            total=len(items),
            offset=offset,
            limit=limit,
            items=items[offset : offset + limit],
        )

    async def get_score_detail(self, user: User, arxiv_id: str) -> PaperScoreDetailResponse | None:
        """The full breakdown for one paper, or None when it is not ingested or not scored."""
        paper = await self.paper_repo.get_by_arxiv_id(arxiv_id)
        if paper is None or not paper.pdf_processed:
            return None
        score = await self.scoring_repo.get_by_paper_id(
            paper.id, self.rubric_version, with_evidence=True
        )
        if score is None:
            return None

        profile = FeedProfile.from_user(user)
        dims = parse_dimensions(score.dimensions)
        state_row = await self.state_repo.get(user.id, paper.id)
        evidence_rows = list(score.evidence)
        return PaperScoreDetailResponse(
            paper=FeedPaper.model_validate(paper),
            rubric_version=score.rubric_version,
            scored_at=score.updated_at,
            scores=build_scores(score, resolve_weights(profile.weights)),
            verdict=build_verdict(dims, score.attributes),
            signals=build_signals(dims, score.attributes, profile.compute_profile),
            low_confidence=low_confidence_dimensions(dims),
            state=(
                UserPaperStateResponse.model_validate(state_row) if state_row is not None else None
            ),
            attributes=build_attributes_detail(score.attributes, evidence_rows),
            dimensions=build_dimension_details(dims, evidence_rows),
        )

    async def _enrich(self, user: User, ranking: list[dict]) -> list[FeedItem]:
        """Turn digest ranking entries into cards from the live rows."""
        entries: list[DigestRankingEntry] = []
        for raw in ranking or []:
            try:
                entries.append(DigestRankingEntry.model_validate(raw))
            except ValidationError as e:
                log.warning("feed_entry_unparseable", error=str(e))

        paper_ids = [uuid.UUID(e.paper_id) for e in entries]
        papers = {p.id: p for p in await self.paper_repo.get_by_ids(paper_ids)}
        scores = await self.scoring_repo.get_by_paper_ids(paper_ids, self.rubric_version)
        states = await self.state_repo.get_many(user.id, paper_ids)

        profile = FeedProfile.from_user(user)
        items: list[FeedItem] = []
        for entry in entries:
            pid = uuid.UUID(entry.paper_id)
            paper = papers.get(pid)
            score = scores.get(pid)
            if paper is None or score is None:
                log.warning("feed_entry_skipped", paper_id=entry.paper_id, arxiv_id=entry.arxiv_id)
                continue
            items.append(self._build_item(paper, score, states.get(pid), profile))
        return items

    async def get_library(self, user: User) -> LibraryResponse:
        """The caller's saved / implementing / shipped papers as cards (SPE-296). A paper
        without a current score still appears, with the score-derived fields empty."""
        rows = await self.state_repo.list_for_user(user.id)
        scores = await self.scoring_repo.get_by_paper_ids(
            [paper.id for _, paper in rows], self.rubric_version
        )
        profile = FeedProfile.from_user(user)
        groups: dict[str, list[FeedItem]] = {"saved": [], "implementing": [], "shipped": []}
        for state_row, paper in rows:
            groups[state_row.state].append(
                self._build_item(paper, scores.get(paper.id), state_row, profile)
            )
        log.info(
            "library_built",
            user_id=str(user.id),
            **{state: len(items) for state, items in groups.items()},
        )
        return LibraryResponse(**groups)

    @staticmethod
    def _build_item(
        paper: Paper,
        score: PaperScore | None,
        state_row: UserPaperState | None,
        profile: FeedProfile,
    ) -> FeedItem:
        """One card from the live rows; personalization (weights, compute match, keyword
        tie-break) is applied here at read time."""
        state = UserPaperStateResponse.model_validate(state_row) if state_row is not None else None
        haystack = f"{paper.title} {paper.abstract}".lower()
        keyword_match = any(k.lower() in haystack for k in profile.keywords)
        if score is None:
            return FeedItem(
                paper=FeedPaper.model_validate(paper), keyword_match=keyword_match, state=state
            )
        dims = parse_dimensions(score.dimensions)
        return FeedItem(
            paper=FeedPaper.model_validate(paper),
            scores=build_scores(score, resolve_weights(profile.weights)),
            verdict=build_verdict(dims, score.attributes),
            signals=build_signals(dims, score.attributes, profile.compute_profile),
            low_confidence=low_confidence_dimensions(dims),
            keyword_match=keyword_match,
            state=state,
            scored_at=score.updated_at,
        )


def _composite(item: FeedItem) -> float:
    """Sort/filter key; an unscored card sorts last."""
    return item.scores.composite if item.scores is not None else -1.0
