"""Seed script for integration evals.

Usage: uv run python -m tests.evals.integration.seed

Idempotent -- only ingests papers that are not already in the database.
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings
from src.factories.service_factories import get_ingest_service
from src.models.user import User
from src.repositories.paper_repository import PaperRepository

from .scenarios import SEED_PAPERS


async def _seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.postgres_url, echo=False, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # Ensure test user exists
        result = await session.execute(
            select(User).where(User.clerk_id == "inteval_test_user")
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(clerk_id="inteval_test_user", email="inteval@test.local")
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created test user: {user.id}")
        else:
            print(f"Test user exists: {user.id}")

        # Check which papers are already ingested
        paper_repo = PaperRepository(session)
        missing: list[str] = []
        for arxiv_id in SEED_PAPERS:
            paper = await paper_repo.get_by_arxiv_id(arxiv_id)
            if paper is None:
                missing.append(arxiv_id)
                print(f"  Missing: {arxiv_id}")
            else:
                print(f"  Found:   {arxiv_id} ({paper.title})")

        if not missing:
            print("\nAll seed papers already ingested.")
            return

        # Ingest missing papers
        print(f"\nIngesting {len(missing)} papers: {missing}")
        ingest_service = get_ingest_service(session, ingested_by=str(user.id))
        result = await ingest_service.ingest_by_ids(missing)

        await session.commit()

        print(f"\nIngest complete: {result.status} -- "
              f"{result.papers_processed} papers, {result.chunks_created} chunks")
        if result.errors:
            print(f"WARNING: {len(result.errors)} errors during ingest:")
            for err in result.errors:
                print(f"  {err}")
            if result.papers_processed == 0:
                print("FATAL: No papers were ingested.")
                sys.exit(1)
            print("Continuing with partial seed (some tests may be skipped).")

    await engine.dispose()


def main() -> None:
    asyncio.run(_seed())


if __name__ == "__main__":
    main()
