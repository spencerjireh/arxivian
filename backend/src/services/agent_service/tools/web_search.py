"""Web search tool for finding recent information."""

import httpx
from src.utils.logger import get_logger
from .base import BaseTool, ToolResult

log = get_logger(__name__)

# Default search API (can be configured for different providers)
DEFAULT_SEARCH_API = "https://api.duckduckgo.com/"


class WebSearchTool(BaseTool):
    """
    Tool for searching the web for recent information.

    Uses DuckDuckGo Instant Answer API by default. Can be extended
    to support other search providers.
    """

    name = "web_search"
    description = (
        "Search the web for recent information, news, or updates. "
        "Use this when the user asks about recent developments, new papers from 2024+, "
        "or information that may not be in the local database."
    )

    def __init__(
        self,
        api_url: str = DEFAULT_SEARCH_API,
        timeout: float = 10.0,
        max_results: int = 5,
    ):
        """
        Initialize web search tool.

        Args:
            api_url: Search API endpoint
            timeout: Request timeout in seconds
            max_results: Maximum number of results to return
        """
        self.api_url = api_url
        self.timeout = timeout
        self.max_results = max_results

    @property
    def parameters_schema(self) -> dict:
        """Return JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for finding web results",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": self.max_results,
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, max_results: int | None = None, **kwargs) -> ToolResult:
        """
        Execute web search.

        Args:
            query: Search query
            max_results: Maximum results to return (uses default if not provided)

        Returns:
            ToolResult with list of search result dictionaries
        """
        max_results = max_results or self.max_results

        log.debug("web_search executing", query=query[:100], max_results=max_results)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.api_url,
                    params={
                        "q": query,
                        "format": "json",
                        "no_redirect": "1",
                        "no_html": "1",
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []

            # Extract results from DuckDuckGo response
            # Abstract (main answer)
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", "Answer"),
                    "snippet": data["Abstract"],
                    "url": data.get("AbstractURL", ""),
                    "source": data.get("AbstractSource", "DuckDuckGo"),
                })

            # Related topics
            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:100],
                        "snippet": topic.get("Text", ""),
                        "url": topic.get("FirstURL", ""),
                        "source": "DuckDuckGo",
                    })

            # Limit results
            results = results[:max_results]

            log.debug("web_search completed", results_found=len(results))

            return ToolResult(
                success=True,
                data=results,
                tool_name=self.name,
            )

        except httpx.TimeoutException:
            log.warning("web_search timeout", query=query[:50])
            return ToolResult(
                success=False,
                error="Search request timed out",
                tool_name=self.name,
            )
        except httpx.HTTPStatusError as e:
            log.error("web_search http error", status=e.response.status_code)
            return ToolResult(
                success=False,
                error=f"Search request failed: HTTP {e.response.status_code}",
                tool_name=self.name,
            )
        except Exception as e:
            log.error("web_search failed", error=str(e))
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name,
            )
