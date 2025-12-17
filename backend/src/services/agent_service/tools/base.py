"""Base tool definition for agent workflow."""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Result from tool execution."""

    success: bool = Field(..., description="Whether the tool execution succeeded")
    data: Any = Field(default=None, description="Result data from the tool")
    error: str | None = Field(default=None, description="Error message if execution failed")
    tool_name: str = Field(..., description="Name of the tool that was executed")


class BaseTool(ABC):
    """Abstract base class for agent tools."""

    name: str
    description: str

    @property
    @abstractmethod
    def parameters_schema(self) -> dict:
        """
        Return JSON schema for tool parameters.

        This is used by the LLM to understand what arguments the tool accepts.
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with success status and data or error
        """
        pass

    def to_llm_schema(self) -> dict:
        """
        Convert tool to LLM-compatible schema for tool calling.

        Returns:
            Dict with name, description, and parameters for LLM
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }
