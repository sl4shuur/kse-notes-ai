import re
import json
from notes_ai.loggers.logging_config import CustomLogger
from notes_ai.models import Note
from dataclasses import replace
from notes_ai.interfaces.llm import LLMClient

THREESHOLD_ADJACENT = 200  # Characters
COLOR_CLUSTERS = {
    "primary_concepts": {
        "primary": "Goldenrod",
        "shades": [
            "Goldenrod",
            "Yellow",
            "SpringGreen",
        ],
        "meaning": "Core ideas, main topics, central definitions"
    },
    "critical_issues": {
        "primary": "Red",
        "shades": [
            "Red",
            "Maroon",
            "WildStrawberry",
            "Salmon",
        ],
        "meaning": "Problems, failures, things to avoid, critical points"
    },
    "considerations": {
        "primary": "Orange",
        "shades": [
            "Orange",
            "Apricot",
            "Peach",
            "Melon",
            "Tan",
        ],
        "meaning": "Important notes, trade-offs, things to keep in mind"
    },
    "specifics": {
        "primary": "Cyan",
        "shades": [
            "Cyan",
            "Aquamarine",
            "Turquoise",
            "BlueGreen",
            "SkyBlue",
            "Cerulean",
        ],
        "meaning": "Concrete details, measurements, numbers, actual examples"
    },
    "actions": {
        "primary": "Lavender",
        "shades": [
            "Lavender",
            "CarnationPink",
            "Orchid",
        ],
        "meaning": "Steps, operations, actions, flows, what to do"
    },
    "structures": {
        "primary": "Periwinkle",
        "shades": [
            "Periwinkle",
            "Purple",
            "Plum",
            "Violet",
        ],
        "meaning": "Organization, composition, relationships, how things fit together"
    },
    "emphasis": {
        "primary": "SeaGreen",
        "shades": [
            "SeaGreen",
            "Emerald",
            "JungleGreen",
            "PineGreen",
            "ForestGreen",
        ],
        "meaning": "Key points, important terms, notable items"
    },
    "neutral": {
        "primary": None,  # No color, keep bold only
        "shades": [None],
        "meaning": "Generic terms, keep bold without color"
    }
}


COLOR_CATEGORIZATION_PROMPT = """<system>
<role>
You are a semantic color categorization expert. Your task is to assign semantic colors to technical terms.
</role>

<input>
<terms_to_categorize>
{terms_list}
</terms_to_categorize>
<context_outline>
{outline_snippet}
</context_outline>
</input>

<categories>
- primary_concepts: Core ideas, main topics, central definitions
- critical_issues: Problems, failures, things to avoid, critical points
- considerations: Important notes, trade-offs, caveats, risks, limitations
- specifics: Concrete details, measurements, numbers, benchmarks, examples
- actions: Steps, operations, actions, workflows, procedures
- structures: Organization, composition, relationships, how things fit together
- emphasis: Key points, notable items, highlights
- neutral: Generic/common terms — keep bold without color
</categories>

<output_format>
Return ONLY a valid JSON mapping:
{{
  "term1": "primary_concepts",
  "term2": "actions",
  "term3": "specifics",
  ...
}}
</output_format>

<rules>
- Be consistent: similar terms get the same category
- Use "neutral" for generic/common words (system, data, process, thing, item)
- Consider technical context and common usage
- Return ONLY the JSON object, nothing else
</rules>
</system>"""



class ColorCategorizer:
    def __init__(self, llm: LLMClient):
           self.llm = llm
      
    def _format_learning_aids(self, outline: str) -> str:
        """
        Normalize Example/Metaphor headers to LaTeX and keep content clean.
        """
        # Example: header + inline content (with or without colon)
        outline = re.sub(
            r'^[ \t]*(?:\*\*\s*)?Example\s*(?:\**)?\s*:?\s+(?P<content>.+)$',
            lambda m: '$\\textcolor{Lime}{\\textbf{Example}}$\n\n' +
            m.group('content'),
            outline,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        # Example: header only (no inline content)
        outline = re.sub(
            r'^[ \t]*(?:\*\*\s*)?Example\s*(?:\**)?\s*:?[ \t]*$',
            lambda _: '$\\textcolor{Lime}{\\textbf{Example}}$\n\n',
            outline,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        # Metaphor: header + inline content (with or without colon)
        outline = re.sub(
            r'^[ \t]*(?:\*\*\s*)?Metaphor\s*(?:\**)?\s*:?\s+(?P<content>.+)$',
            lambda m: '$\\textcolor{Thistle}{\\textbf{Metaphor}}$\n\n' +
            m.group('content'),
            outline,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        # Metaphor: header only (no inline content)
        outline = re.sub(
            r'^[ \t]*(?:\*\*\s*)?Metaphor\s*(?:\**)?\s*:?[ \t]*$',
            lambda _: '$\\textcolor{Thistle}{\\textbf{Metaphor}}$\n\n',
            outline,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        return outline


    def _get_bold_terms(self, text: str) -> list[tuple[str, int]]:
        """
        Extract all bold terms from markdown with their positions.
        """
        pattern = r'\*\*([^*]+)\*\*'
        terms = []
        for match in re.finditer(pattern, text):
            term = match.group(1)
            terms.append((term, match.start()))
        return terms


    def _find_adjacent_terms(self, terms: list[tuple[str, int]], threshold: int = 20) -> list[list[int]]:
        """
        Group term indices that are close together (adjacent/near).
        """
        if not terms:
            return []

        groups = []
        current_group = [0]

        for i in range(1, len(terms)):
            distance = terms[i][1] - terms[i - 1][1]
            if distance <= threshold:
                current_group.append(i)
            else:
                groups.append(current_group)
                current_group = [i]

        groups.append(current_group)
        return groups


    def _get_color_assignment(cluster: str, shade_index: int) -> str | None:
        """
        Get color for a term in a specific cluster and shade position.
        """
        if cluster not in COLOR_CLUSTERS:
            cluster = "neutral"

        shades = COLOR_CLUSTERS[cluster]["shades"]
        shade = shades[shade_index % len(shades)]
        return shade


    async def _categorize_terms(self,terms: list[str], outline: str, logger: CustomLogger, prompt = COLOR_CATEGORIZATION_PROMPT) -> dict[str, str]:
        """
        Use LLM to categorize terms into color clusters.
        """
        terms_list = "\n".join([f"- {term}" for term in terms])
        prompt = prompt.format(
            terms_list=terms_list, outline_snippet=outline)



        result_text = str(await self.llm.complete(user_prompt=prompt, system_prompt = ""))
        logger.debug(f"Categorization result:\n{result_text}")

        try:
            categorization = json.loads(str(result_text))
            return categorization
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse categorization JSON: {result_text}")
            return {term: "neutral" for term in terms}


    def _extract_bold_matches(self, text: str) -> list[re.Match]:
        """Return all **bold** matches with positions."""
        return list(re.finditer(r'\*\*([^*]+)\*\*', text))


    def _filter_prohibitive(self, matches: list[re.Match]) -> list[re.Match]:
        """Drop Example/Metaphor headers from matches."""
        prohibitive = {"example", "metaphor", "example:", "metaphor:"}
        return [
            m for m in matches
            if m.group(1).strip().lower() not in prohibitive
        ]


    def _build_adjacent_groups(self,matches: list[re.Match], threshold: int) -> list[list[int]]:
        """Group indices of matches that are close to each other."""
        term_indices = [(m.group(1), m.start()) for m in matches]
        return self._find_adjacent_terms(term_indices, threshold=threshold)


    def _build_position_color_map(self,
        matches: list[re.Match],
        adjacent_groups: list[list[int]],
        categorization: dict[str, str],
    ) -> dict[int, tuple[str, str]]:
        """
        For every bold occurrence, decide its color and return a map:
        position -> (term, colored_term)
        """
        term_indices = [(m.group(1), m.start()) for m in matches]
        position_to_color: dict[int, tuple[str, str]] = {}

        for group_positions in adjacent_groups:
            for shade_idx, term_pos in enumerate(group_positions):
                term = term_indices[term_pos][0]
                position = term_indices[term_pos][1]

                cluster = categorization.get(term, "neutral")
                color = self._get_color_assignment(cluster, shade_idx)

                colored = (
                    f"$\\textcolor{{{color}}}{{\\text{{{term}}}}}$"
                    if color else f"**{term}**"
                )
                position_to_color[position] = (term, colored)

        return position_to_color


    def _replace_terms_once(self, text: str, position_to_color: dict[int, tuple[str, str]]) -> str:
        """Replace bold terms occurrence-by-occurrence, starting from the end."""
        result = text
        sorted_positions = sorted(
            position_to_color.items(), key=lambda x: x[0], reverse=True)

        for position, (term, colored) in sorted_positions:
            pattern = rf'\*\*{re.escape(term)}\*\*'
            match = re.search(pattern, result[position:])
            if match:
                start = position + match.start()
                end = position + match.end()
                result = result[:start] + colored + result[end:]
        return result


    async def apply_color_markup(self, note: Note, logger: CustomLogger) -> Note:
        """
        Apply color markup to bold terms with intelligent grouping.
        Each occurrence of a term gets its own color based on position.
        """
        outline = note.content
        matches = self._extract_bold_matches(outline)
        if not matches:
            logger.debug("No bold terms found")
            return 

        filtered = self._filter_prohibitive(matches)
        if not filtered:
            logger.debug("No terms to colorize after filtering")
            return replace(
                        note,
                        content=self._format_learning_aids(outline),
                        metadata={
                            **note.metadata,
                            "formatted": True,
                        },
                    )

        unique_terms = list(dict.fromkeys([m.group(1) for m in filtered]))
        logger.debug(f"Found {len(unique_terms)} unique bold terms")

        categorization = self._categorize_terms(unique_terms, outline, logger)

        adjacent_groups = self._build_adjacent_groups(
            filtered, threshold=THREESHOLD_ADJACENT)
        logger.debug(f"Found {len(adjacent_groups)} adjacent term groups")

        position_to_color = self._build_position_color_map(
            filtered, adjacent_groups, categorization)

        replaced = self._replace_terms_once(outline, position_to_color)

        formatted_outline = self._format_learning_aids(replaced)
        logger.debug(
            f"Applied color markup to {len(position_to_color)} term occurrences")
        return replace(
                note,
                content=formatted_outline,
                metadata={
                    **note.metadata,
                    "formatted": True,
                },
            )
