"""Gemini AI service exceptions."""


class GeminiError(Exception):
    """Base error for all Gemini service failures."""


class GeminiServiceUnavailableError(GeminiError):
    """Raised when the Gemini API is temporarily unavailable after retries.

    Attributes:
        attempts: Number of attempts made before giving up.
    """

    def __init__(self, message: str, *, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(message)


class GeminiToolError(GeminiError):
    """Raised when a tool execution fails unexpectedly.

    Attributes:
        tool_name: The name of the tool that failed.
    """

    def __init__(self, tool_name: str, detail: str) -> None:
        self.tool_name = tool_name
        self.detail = detail
        super().__init__(f"Tool '{tool_name}' failed: {detail}")
