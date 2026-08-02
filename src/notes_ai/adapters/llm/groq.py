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
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content.strip()
