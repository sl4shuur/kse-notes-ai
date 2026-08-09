import re


def normalize_smart_quotes(text: str) -> str:
    """Replace smart quotes with plain quotes."""
    return (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("„", '"')
        .replace("«", '"')
        .replace("»", '"')
    )


def unwrap_backticked_math(text: str) -> str:
    """Remove backticks around inline math like `...$...$...` -> ...$...$..."""
    pattern = re.compile(r"`\s*(\$[^`]+?\$)\s*`")
    return pattern.sub(lambda m: m.group(1).strip(), text)


def trim_spaces_in_math(text: str) -> str:
    """Remove leading/trailing spaces inside $...$ blocks."""

    # Inline math: $ ... $ -> $...$
    def _trim(match: re.Match[str]) -> str:
        inner = match.group(1)
        return f"${inner.strip()}$"

    text = re.sub(r"\$(.+?)\$", _trim, text)
    return text


def escape_underscores_in_textcolor(text: str) -> str:
    r"""Escape underscores inside \textcolor{...}{...} blocks within math.

    Example: $\textcolor{Lime}{\text{additional_authorized_imports}}$
    becomes: $\textcolor{Lime}{\text{additional\_authorized\_imports}}$
    """

    def _escape(match: re.Match[str]) -> str:
        block = match.group(0)
        return re.sub(r"(?<!\\)_", r"\\_", block)

    return re.sub(r"\\textcolor\{[^}]+\}\{[^}]*\}", _escape, text)


def clean_heading_colors(text: str) -> str:
    """Strip color markup from headings only.

    Example:
    ## $\textcolor{Lime}{\text{Introduction to LlamaIndex}}$ -> ## Introduction to LlamaIndex
    """

    pattern = re.compile(
        r"^(#{1,6})\s+\$\\textcolor\{[^}]+\}\{\s*\\text\{([^}]*)\}\s*\}\$\s*$", re.MULTILINE
    )

    def _strip(match: re.Match[str]) -> str:
        hashes = match.group(1)
        content = match.group(2)
        return f"{hashes} {content.strip()}"

    return pattern.sub(_strip, text)


def add_spaces_around_em_dashes(text: str) -> str:
    """
    Add spaces around "—" em dashes if missing.
    """
    return re.sub(r"(?<!\s)—(?!\s)", " — ", text)


def remove_spammy_underscores(text: str) -> str:
    """
    Remove underscores that are likely spammy, e.g., in URLs or random sequences.
    """
    # Remove random sequences of underscores longer than 3
    text = re.sub(r"_{3,}", "---", text)
    return text


def clean_note(markdown: str) -> str:
    """Apply all cleanup rules to a generated markdown note."""

    steps = [
        normalize_smart_quotes,
        unwrap_backticked_math,
        trim_spaces_in_math,
        add_spaces_around_em_dashes,
        escape_underscores_in_textcolor,
        clean_heading_colors,
        remove_spammy_underscores,
    ]

    for step in steps:
        markdown = step(markdown)
    return markdown
