"""LLM service error definitions"""


class LLMError(Exception):
    """Base exception for LLM-related errors"""

    pass


class LLMRateLimitError(LLMError):
    """Raised when LLM API rate limit is exceeded"""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int | None = None
    ):
        super().__init__(message)
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """Raised when LLM API request times out"""

    pass


class LLMInvalidResponseError(LLMError):
    """Raised when LLM returns invalid or unparseable response"""

    pass


class LLMAuthenticationError(LLMError):
    """Raised when LLM API authentication fails"""

    pass


class LLMQuotaExceededError(LLMError):
    """Raised when LLM API quota is exceeded"""

    pass
