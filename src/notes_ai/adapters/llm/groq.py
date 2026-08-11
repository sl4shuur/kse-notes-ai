from groq import AsyncGroq
from openinference.instrumentation.groq import GroqInstrumentor
from notes_ai.interfaces import LLMClient
from phoenix.otel import register

class GroqLLMClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        phoenix_api_key: str,
        model: str = "openai/gpt-oss-20b",
    ):
        self.client = AsyncGroq(api_key=api_key)
        self.model = model
        self.phoenix_api_key = phoenix_api_key
        self._tracer_provider = register(
            project_name="Notes-AI",
            endpoint="https://app.phoenix.arize.com/s/mkapranov/v1/traces",
            headers={"authorization": f"Bearer {phoenix_api_key}"},
            batch=True,
            set_global_tracer_provider=False,
            )        
        GroqInstrumentor().instrument(tracer_provider=self._tracer_provider)
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
