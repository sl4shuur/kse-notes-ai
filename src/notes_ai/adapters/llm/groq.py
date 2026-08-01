from notes_ai.interfaces.llm import LLMClient
from groq import Groq
from pathlib import Path

from notes_ai.utils.config import TEST_OUTPUT_DIR
from notes_ai.utils.logging_config import CustomLogger
from notes_ai.models import ExtractedContent, Note
from datetime import datetime
from dataclasses import replace  

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









# class GroqLLMClient:
   
#    def __init__(self, api_key: str, model = "openai/gpt-oss-120b"):
#        self.api_key = api_key
#        self.groq_client = Groq(api_key=api_key)
#        self.model =model



#    def generate(self,source_content: ExtractedContent, logger: CustomLogger, user_prompt = USER_PROMPT_TEMPLATE) -> Note:
#        prompt = user_prompt.format(content=source_content)

#     # Generate study notes
#        response = self.groq_client.chat.completions.create(
#        model=self.model,
#        messages=[
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {"role": "user", "content": prompt},
#         ],
#        temperature=0.3,
#        max_tokens=8192,
#     )

#        notes = str(response.choices[0].message.content)
#        logger.debug("Generated study notes.")
#        return Note(
#         title=getattr(source_content, "title", "Study Notes"),
#         content=notes,
#         date_created=datetime.now(),
#         metadata={
#             "model": self.model,
#             "temperature": 0.3,
#         },
#     )



#    def enrich_with_examples_and_metaphors(self,
#     outline: str, note: Note,  logger: CustomLogger, user_prompt = ENRICH_USER_PROMPT) -> Note:
#     """
#     Agent 2: Add Example and Metaphor blocks to the outline.

#     Args:
#         outline: The raw outline from step 1
#         source_content: Original transcript for context
#         logger: Logger instance

#     Returns:
#         Enriched outline with Example and Metaphor blocks
#     """
#     prompt = user_prompt.format(
#         outline=outline, transcript=note.content)

#     response = self.groq_client.chat.completions.create(
#         model=self.model,
#         messages=[
#             {"role": "system", "content": ENRICH_SYSTEM_PROMPT},
#             {"role": "user", "content": prompt},
#         ],
#         temperature=0.3,  # Might even be higher for more creative examples
#         max_tokens=8192,
#     )

#     enriched_outline = str(response.choices[0].message.content)
#     msg = "Enriched outline with examples and metaphors (Step 2/2)." + \
#         f"\n{enriched_outline[:1000]}..."
#     logger.debug(msg)
#     return replace(
#         note,
#         content=enriched_outline,
#         metadata={
#             **note.metadata,
#             "enriched": True,
#         },
#     )

#    def generate_raw_outline(self, note: Note, logger: CustomLogger) -> Note:
#     """
#     Agent 1: Generate outline with bold terms and strategic learning aids.

#     Args:
#         Note: Raw note
#         logger: Logger instance

#     Returns:
#         Structured Markdown outline with **bold** terms and learning aids
#     """
#     prompt = RAW_OUTLINE_USER_PROMPT.format(content=note.content)

#     response = self.groq_client.chat.completions.create(
#         model=self.model,
#         messages=[
#             {"role": "system", "content": RAW_OUTLINE_SYSTEM_PROMPT},
#             {"role": "user", "content": prompt},
#         ],
#         temperature=0.3,  
#         max_tokens=8192,
#     )

#     outline = str(response.choices[0].message.content)
#     logger.debug(
#         f"Generated outline with learning aids (Step 1/2)\n{outline[:5000]}...")
#     return replace(
#             note,
#             content=outline,
#             metadata={
#                 **note.metadata,
#                 "outlined": True,
#             },
#         )

      
   
       



