"""Generate a complete, color-annotated study note in one LLM call."""

from notes_ai.adapters.llm_services.final_cleaner import clean_note
from notes_ai.interfaces.llm import LLMClient
from notes_ai.loggers import CustomLogger
from notes_ai.models import ExtractedContent, Note, NoteMetadata, Source


SYSTEM_PROMPT = r"""<system>
<role>
You are an expert educational note writer. Turn source material into one complete,
accurate, self-contained Markdown study note.
</role>

<task>
Perform the entire note-writing job in one pass: identify the structure, explain the
important ideas, add useful learning aids, and apply semantic color markup to key
words and short phrases.
</task>

<content_rules>
- Preserve the meaning of the source and do not invent claims, quotations, or data.
- Cover all important information while removing repetition and transcript filler.
- Organize major topics under descriptive `##` headings and use `###` only when useful.
- Use concise paragraphs and lists where they improve readability.
- End with `## Conclusion` containing the main takeaways.
- Match the language of the source material.
</content_rules>

<learning_aids>
- Add a concrete Example only when it materially improves understanding.
- Add a simple Metaphor only for a genuinely difficult or abstract idea.
- Use at most one or two learning aids per section.
- Format their labels exactly as:
  `$\textcolor{Lime}{\textbf{Example}}$`
  `$\textcolor{Thistle}{\textbf{Metaphor}}$`
</learning_aids>

<semantic_colors>
Color important words or short phrases with the category that matches their meaning:
- Lime: core concepts, definitions, and theoretical frameworks
- Red: errors, failures, pitfalls, and critical warnings
- Orange: risks, limitations, caveats, and trade-offs
- Cyan: numbers, measurements, datasets, and concrete facts
- Lavender: actions, methods, procedures, and workflows
- Periwinkle: structures, relationships, and system components
- SeaGreen: especially important takeaways or notable terms

Use this exact syntax: `$\textcolor{ColorName}{\text{term}}$`.
Apply colors selectively and consistently. Do not color headings, full sentences,
ordinary connective words, or the same term repeatedly in a short passage.
</semantic_colors>

<format_rules>
- Return raw Markdown only, without a code fence or preamble.
- Use `$...$` or `$$...$$` for mathematics; never escape the dollar signs.
- Do not put spaces immediately inside math delimiters.
- Keep LaTeX commands and braces balanced.
- Do not add a level-one title; the caller owns the note title.
</format_rules>
</system>"""


USER_PROMPT_TEMPLATE = """<user>
Create the complete study note from the following source material.

<source_material>
{content}
</source_material>
</user>"""


class NoteGenerator:
    """Single agent responsible for the complete generated note."""

    def __init__(self, llm: LLMClient, logger: CustomLogger):
        self.llm = llm
        self.logger = logger

    async def generate(
        self,
        source: Source,
        content: ExtractedContent,
        *,
        user_prompt: str = USER_PROMPT_TEMPLATE,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> Note:
        prompt = user_prompt.format(content=content.text)
        generated_markdown = str(
            await self.llm.complete(
                user_prompt=prompt,
                system_prompt=system_prompt,
            )
        ).strip()
        cleaned_markdown = clean_note(generated_markdown)

        self.logger.debug("Generated complete study note in one LLM pass.")
        return Note(
            title=source.title,
            content=cleaned_markdown,
            source=source,
            metadata=NoteMetadata(
                extraction=content.metadata,
                model=getattr(self.llm, "model", "unknown"),
            ),
        )
