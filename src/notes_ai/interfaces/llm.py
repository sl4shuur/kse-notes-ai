"""Protocol implemented by language-model adapters."""

from typing import Protocol


class LLMClient(Protocol):
    model: str

    async def complete(
        self,
        *,
        user_prompt: str,
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 3000,
        images: list[str] | None = None,
        model: str | None = None,
    ) -> str: ...
