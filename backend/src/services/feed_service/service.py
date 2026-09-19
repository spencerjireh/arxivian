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

from src.models.user import User
from src.repositories.digest_repository import DigestRepository
from src.repositories.paper_repository import PaperRepository
from src.repositories.scoring_repository import ScoringRepository
from src.repositories.user_paper_state_repository import UserPaperStateRepository
from src.schemas.digest import DigestRankingEntry, week_start_for
from src.schemas.feed import (
    AvailableWeek,
    FeedItem,
    FeedPaper,
    FeedResponse,
    UserPaperStateResponse,
    build_scores,
    build_signals,
    build_verdict,
    low_confidence_dimensions,
    parse_dimensions,
    resolve_weights,
)
from src.schemas.scoring_state import RUBRIC_VERSION
from src.schemas.users import FeedProfile
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
            items = [i for i in items if i.scores.composite >= min_score]
        if not include_dismissed:
            items = [i for i in items if i.state is None or i.state.state != "dismissed"]

        profile = FeedProfile.from_user(user)
        if profile.compute_profile is not None or profile.keywords:
            items.sort(
                key=lambda i: (
                    -(1 if i.signals.compute_match else 0),
                    -(1 if i.keyword_match else 0),
                    -i.scores.composite,
                )
            )
        else:
            items.sort(key=lambda i: -i.scores.composite)

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
        weights = resolve_weights(profile.weights)
        keywords = [k.lower() for k in profile.keywords]

        items: list[FeedItem] = []
        for entry in entries:
            pid = uuid.UUID(entry.paper_id)
            paper = papers.get(pid)
            score = scores.get(pid)
            if paper is None or score is None:
                log.warning("feed_entry_skipped", paper_id=entry.paper_id, arxiv_id=entry.arxiv_id)
                continue

            dims = parse_dimensions(score.dimensions)
            haystack = f"{paper.title} {paper.abstract}".lower()
            state_row = states.get(pid)
            items.append(
                FeedItem(
                    paper=FeedPaper.model_validate(paper),
                    scores=build_scores(score, weights),
                    verdict=build_verdict(dims, score.attributes),
                    signals=build_signals(dims, score.attributes, profile.compute_profile),
                    low_confidence=low_confidence_dimensions(dims),
                    keyword_match=any(k in haystack for k in keywords),
                    state=(
                        UserPaperStateResponse.model_validate(state_row)
                        if state_row is not None
                        else None
                    ),
                    scored_at=score.updated_at,
                )
            )
        return items
