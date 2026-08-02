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
        max_tokens: int = 3000,
        images: list[str] | None = None,
        model: str | None = None,
    ) -> str:
        if images:
            user_content = [{"type": "text", "text": user_prompt}] + [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                }
                for img in images
            ]
        else:
            user_content = user_prompt

        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content.strip()
        
