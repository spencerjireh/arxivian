"""TypeSafe Jev client -- typed judgments for the Stage 2 scoring graph.

Jev is a System One model: it returns calibrated probabilities over typed answers
(Choice, Noul, Score) for questions asked over a ``state`` payload, and generates no text.
The scoring nodes own candidate finding and combination; this client owns the transport.

Design notes:

- The wrapper is the cached singleton and holds config only. Each ``ask`` opens a fresh
  ``AsyncTypeSafeClient`` (which owns an httpx2 connection pool), mirroring
  ``SemanticScholarClient._fetch``'s per-call ``httpx.AsyncClient``. Celery tasks run each
  invocation on a temporary event loop (``tasks/utils.run_async``), so a long-lived async
  client bound to one loop would break on the next task.
- ``RetryPolicy(timeout=None)``: the SDK's default 30 s *total* retry budget is smaller
  than a single 60 s request timeout, which would silently disable retries.
- Answers are normalized into plain dataclasses. The SDK answer models are frozen/strict,
  which makes test fakes awkward, and the combine rules only need the numbers.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from typesafe_sdk import (
    AsyncTypeSafeClient,
    Choice,
    Noul,
    RetryPolicy,
    Score,
)
from typesafe_sdk import TypeSafeAPIConnectionError as SDKConnectionError
from typesafe_sdk import TypeSafeAPIError as SDKAPIError
from typesafe_sdk import TypeSafeError as SDKError
from typesafe_sdk import TypeSafeRateLimitError as SDKRateLimitError

from src.exceptions import TypeSafeConnectionError, TypeSafeError, TypeSafeRateLimitError
from src.utils.logger import get_logger

log = get_logger(__name__)

Question = Choice | Noul | Score


@dataclass(frozen=True)
class ChoiceResult:
    """One Choice answer: the argmax option plus the full distribution."""

    choice: str
    probabilities: dict[str, float]
    confidence: float


@dataclass(frozen=True)
class ScoreResult:
    """One Score answer: expected level (fractional), per-level distribution, legend."""

    score: float
    probabilities: dict[int, float]
    confidence: float
    legend: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SystemOneResult:
    """Normalized ``system_one`` response. ``nouls`` values are P(yes)."""

    nouls: dict[str, float]
    choices: dict[str, ChoiceResult]
    scores: dict[str, ScoreResult]
    model: str
    input_tokens: int | None


class TypeSafeClient:
    """Thin wrapper over ``typesafe_sdk.AsyncTypeSafeClient``."""

    def __init__(self, api_key: str, model: str, timeout_seconds: float = 60.0):
        if not api_key:
            raise TypeSafeError("TYPESAFE_API_KEY is not set; Stage 2 scoring cannot run")
        self._api_key = api_key
        self.model = model
        self._timeout = float(timeout_seconds)
        self._retry = RetryPolicy(max_retries=2, timeout=None)

    async def ask(
        self,
        state: Any,
        questions: Mapping[str, Question],
        *,
        request_name: str,
    ) -> SystemOneResult:
        """Ask a set of independent questions over one state in a single round trip.

        Raises:
            TypeSafeRateLimitError: 429 after SDK retries (carries ``retry_after`` seconds).
            TypeSafeConnectionError: connect/timeout failure after SDK retries.
            TypeSafeError: any other API error (non-retryable by the scoring task).
        """
        state_chars = len(str(state))
        try:
            async with AsyncTypeSafeClient(
                api_key=self._api_key,
                model=self.model,
                timeout=self._timeout,
                retry=self._retry,
            ) as client:
                response = await client.system_one(state, questions)
        except SDKRateLimitError as e:
            retry_after = e.retry_after_ms / 1000.0 if e.retry_after_ms is not None else None
            log.warning(
                "typesafe_rate_limited",
                request_name=request_name,
                retry_after=retry_after,
                request_id=e.request_id,
            )
            raise TypeSafeRateLimitError(
                message=str(e), retry_after=retry_after, request_id=e.request_id
            ) from e
        except SDKConnectionError as e:
            log.warning("typesafe_connection_error", request_name=request_name, error=str(e))
            raise TypeSafeConnectionError(str(e)) from e
        except SDKAPIError as e:
            log.error(
                "typesafe_api_error",
                request_name=request_name,
                status=e.status,
                request_id=e.request_id,
                error=str(e),
            )
            raise TypeSafeError(str(e), status=e.status, request_id=e.request_id) from e
        except SDKError as e:
            # Client-side validation (empty questions, missing key, bad criteria).
            log.error("typesafe_client_error", request_name=request_name, error=str(e))
            raise TypeSafeError(str(e)) from e

        result = SystemOneResult(
            nouls={k: float(a.noul) for k, a in response.nouls.items()},
            choices={
                k: ChoiceResult(
                    choice=a.choice,
                    probabilities={opt: float(p) for opt, p in a.probabilities.items()},
                    confidence=float(a.confidence),
                )
                for k, a in response.choices.items()
            },
            scores={
                k: ScoreResult(
                    score=float(a.score),
                    probabilities={int(lvl): float(p) for lvl, p in a.probabilities.items()},
                    confidence=float(a.confidence),
                    legend=[str(a.legend[lvl]) for lvl in sorted(a.legend)] if a.legend else [],
                )
                for k, a in response.scores.items()
            },
            model=response.model,
            input_tokens=response.usage.input_tokens if response.usage else None,
        )
        log.info(
            "typesafe_request",
            request_name=request_name,
            model=result.model,
            input_tokens=result.input_tokens,
            question_count=len(questions),
            state_chars=state_chars,
        )
        return result
