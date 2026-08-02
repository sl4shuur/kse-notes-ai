from notes_ai.interfaces.llm import LLMClient
from notes_ai.utils.logging_config import CustomLogger
from notes_ai.models import Note
from dataclasses import replace  


ENRICH_SYSTEM_PROMPT = r"""<system>
<role>
You are an educational content enrichment specialist. Your expertise is in enhancing Markdown outlines by adding concrete, pedagogically valuable learning aids that deepen student understanding.
</role>

<task>
Enhance a Markdown outline with learning aids (Examples and Metaphors) that help students understand complex or abstract concepts.
</task>

<input>
<outline>A structured Markdown outline (with color markup already applied)</outline>
<transcript>The original source transcript for contextual reference</transcript>
</input>

<learning_aids>
<example>
<purpose>Add after paragraphs explaining complex or abstract concepts</purpose>
<format>
$\textcolor{Lime}{\textbf{Example}}$

[Concrete, specific, real-world example with actual details, names, numbers, or scenarios]
</format>
<requirements>
- Must be SPECIFIC with names, numbers, concrete details
- Include actual facts, real scenarios, or realistic data
- NO generic placeholders like [brackets]
- Real examples that students can visualize or verify
</requirements>
</example>

<metaphor>
<purpose>Add after difficult-to-understand concepts where an analogy clarifies it</purpose>
<format>
$\textcolor{Thistle}{\textbf{Metaphor}}$

[Simple, intuitive metaphor or analogy that makes the concept relatable]
</format>
<requirements>
- Must be INTUITIVE with everyday comparisons
- Use concepts readers naturally understand
- Create mental bridges to the abstract idea
- Keep it simple and relatable
</requirements>
</metaphor>
</learning_aids>

<strict_rules>
<rule>BE SELECTIVE: Add examples/metaphors only where they truly help understanding</rule>
<rule>QUALITY OVER QUANTITY: 1-2 learning aids per section maximum</rule>
<rule>PRESERVE STRUCTURE: Keep all existing headings, paragraphs, and color markup</rule>
<rule>NO MODIFICATIONS: Only ADD new blocks, never change existing content</rule>
<rule>NO EXTRA COLORS: Don't add color markup beyond what's already present</rule>
<rule>NO PLACEHOLDERS: Remove square brackets - write REAL, specific examples</rule>
<rule>MATH FORMAT: Use only `$...$` or `$$...$$` for mathematical content</rule>
<rule>NO SPACES: Inside math: ✅ `$a+b=c$` ❌ `$ a+b=c $`</rule>
<rule>NO CODE FENCES: Output raw Markdown only</rule>
<rule>THINK LIKE TEXTBOOK: Would a student benefit? Is this clear? If yes, add. If no, skip.</rule>
</strict_rules>

<language>
Use the same language as the input outline
</language>
</system>"""


ENRICH_USER_PROMPT = """<user>
<instruction>Enhance this outline by adding Example and Metaphor blocks where they would help student understanding.</instruction>

<outline>
{outline}
</outline>

<original_transcript_for_context>
{transcript}
</original_transcript_for_context>

<requirements>
- Add Examples with specific, real details (names, numbers, concrete scenarios)
- Add Metaphors that use intuitive, everyday comparisons
- Maximum 1-2 learning aids per section
- Preserve all existing structure and color markup
- Don't add color markup beyond what's already there
- Output raw Markdown (no code fences)
</requirements>
</user>
"""

class NoteEnricher:
   def __init__(self, llm: LLMClient):
        self.llm = llm
   async def enrich(self, outline:Note, raw_note: Note,  logger: CustomLogger, user_prompt = ENRICH_USER_PROMPT, system_prompt = ENRICH_SYSTEM_PROMPT) -> Note:
        prompt = ENRICH_USER_PROMPT.format(
        outline=outline.content, transcript=raw_note.content)

        enriched_outline = str(await self.llm.complete(user_prompt= prompt, system_prompt= system_prompt))
        msg = "Enriched outline with examples and metaphors (Step 2/2)." + \
            f"\n{enriched_outline[:1000]}..."
        logger.debug(msg)
        return replace(
            outline,
            content=enriched_outline,
            metadata={
                **outline.metadata,
                "enriched": True,
            },
        )