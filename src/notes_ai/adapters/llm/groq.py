from groq import AsyncGroq

class GroqLLMClient:
    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-oss-20b",
    ):
        self.client = AsyncGroq(api_key=api_key)
        self.model = model

    async def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": user,
                },
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content.strip()
