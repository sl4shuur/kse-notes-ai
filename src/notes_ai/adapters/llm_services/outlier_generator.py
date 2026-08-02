
from notes_ai.interfaces.llm import LLMClient
from notes_ai.interfaces.llm import LLMClient
from notes_ai.utils.logging_config import CustomLogger
from notes_ai.models import  Note
from dataclasses import replace  


RAW_OUTLINE_SYSTEM_PROMPT = r"""<system>
<role>
You are an educational content specialist. Your expertise is in transforming transcripts into clear, well-structured study materials that help students understand complex topics.
</role>

<task>
Create a comprehensive Markdown outline from a transcript, organizing content logically and adding learning aids where they genuinely help understanding.
</task>

<output_format>
<structure>
- Start with a brief introduction (if needed)
- Each major concept gets a `## Heading` (level 2 markdown)
- End with `## Conclusion` summarizing key takeaways
</structure>

<content_per_section>
- 3-5 paragraphs of clear, detailed explanation
- Focus on accuracy and completeness
- Separate paragraphs with blank lines
- Use bullet points (`- item`) for lists where appropriate
- Mark important technical terms in **bold**
</content_per_section>
</output_format>

<learning_aids>
<when_to_use>
Add learning aids ONLY when they genuinely help understanding. Not every concept needs an example or metaphor - use judgment and restraint.
</when_to_use>

<example>
<purpose>Use after explaining something abstract or complex where a concrete case would clarify</purpose>
<format>
Example:

Specific, concrete scenario with real details - names, numbers, actual situations
</format>
<quality_standard>
✅ GOOD: "Netflix's recommendation system processes 200+ million ratings daily, using collaborative filtering to suggest shows. When you rate Stranger Things 5 stars, the system finds users with similar taste patterns and recommends what they enjoyed."
❌ BAD: "A recommendation system uses machine learning to suggest content."
</quality_standard>
</example>

<metaphor>
<purpose>Use after explaining difficult concepts where an intuitive comparison makes it click</purpose>
<format>
Metaphor:

Simple, relatable analogy using everyday concepts
</format>
<quality_standard>
✅ GOOD: "Neural networks are like apprentices learning a craft - they start by mimicking examples, make mistakes, receive corrections, and gradually develop intuition through practice."
❌ BAD: "Neural networks are computational models."
</quality_standard>
</metaphor>

<restraint>
Quality over quantity - most sections won't need both Example AND Metaphor. Some sections might not need either. Add them only where they provide real pedagogical value.
</restraint>
</learning_aids>

<term_markup>
Mark important technical terms in **bold** as you write. Be selective - bold should highlight key concepts, not decorate every noun.

✅ GOOD: "**machine learning** algorithms use **training data** to identify patterns"
✅ GOOD: "avoid **overfitting** by using **cross-validation**"
❌ BAD: "**machine** **learning** **algorithms** **use** **training** **data**"
</term_markup>

<strict_rules>
<rule>OUTPUT RAW MARKDOWN: No code fences, no wrapping</rule>
<rule>BE SELECTIVE: Learning aids only where they truly help</rule>
<rule>BE SPECIFIC: Real examples with actual details, not generic descriptions</rule>
<rule>BE INTUITIVE: Metaphors should use familiar concepts</rule>
<rule>PRESERVE MEANING: Accuracy is more important than style</rule>
</strict_rules>

<language>
Default: English (unless source text is in another language - match the input language)
</language>
</system>"""

RAW_OUTLINE_USER_PROMPT = """<user>
<instruction>Transform this transcript into a well-structured outline with strategic learning aids.</instruction>

<transcript>
{content}
</transcript>

<requirements>
- Organize into logical `## Heading` sections
- Mark important technical terms in **bold**
- Add Examples where concrete cases help understanding (not everywhere)
- Add Metaphors where analogies clarify difficult concepts (not everywhere)
- Focus on clarity and pedagogical value
- Output raw Markdown (no code fences)
</requirements>
</user>"""



class OutlineGenerator:
    def __init__(self, llm: LLMClient):
            self.llm = llm
    async def outline(self, note: Note, logger: CustomLogger) -> Note:
        """
        Agent 1: Generate outline with bold terms and strategic learning aids.

        Args:
            Note: Raw note
            logger: Logger instance

        Returns:
            Structured Markdown outline with **bold** terms and learning aids
        """
        prompt = RAW_OUTLINE_USER_PROMPT.format(content=note.content)
        outline = str(await self.llm.complete(user_prompt= prompt, system_prompt = RAW_OUTLINE_SYSTEM_PROMPT))
        logger.debug(
            f"Generated outline with learning aids (Step 1/2)\n{outline[:5000]}...")
        return replace(
                note,
                content=outline,
                metadata={
                    **note.metadata,
                    "outlined": True,
                },
            )        
