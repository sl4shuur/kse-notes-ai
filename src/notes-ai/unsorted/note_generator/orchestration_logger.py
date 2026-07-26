import markdown
import tempfile
import webbrowser
from markdown.extensions.extra import ExtraExtension
from markdown.extensions.codehilite import CodeHiliteExtension

FULL_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Markdown Preview</title>
    <!-- MathJax for LaTeX rendering -->
    <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        packages: {{'[+]': ['color']}}
      }},
      loader: {{
        load: ['[tex]/color']
      }}
    }};
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px;
            background: #1e1e1e;
            color: #e0e0e0;
        }}
        code {{
            background: #2d2d30;
            color: #d4d4d4;
            padding: 0.2em 0.4em;
            border-radius: 6px;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 85%%;
        }}
        pre {{
            background: #2d2d30;
            color: #d4d4d4;
            padding: 16px;
            border-radius: 6px;
            overflow: auto;
            border: 1px solid #3e3e42;
        }}
        pre code {{
            background: transparent;
            padding: 0;
        }}
        blockquote {{
            border-left: 4px solid #007acc;
            color: #b0b0b0;
            margin: 0;
            padding: 0 1em;
        }}
        h1, h2, h3 {{
            border-bottom: 1px solid #3e3e42;
            padding-bottom: 0.3em;
            color: #ffffff;
        }}
        h1 {{
            color: #4ec9b0;
        }}
        h2 {{
            color: #569cd6;
        }}
        h3 {{
            color: #9cdcfe;
        }}
        a {{
            color: #3794ff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        mjx-container {{
            font-size: 1.1em !important;
        }}
        ul, ol {{
            color: #e0e0e0;
        }}
        strong {{
            color: #ffffff;
        }}
        em {{
            color: #dcdcaa;
        }}
    </style>
</head>
<body>
<div class="markdown-body">
{html_content}
</div>
</body>
</html>"""


def render_markdown_note(markdown_content: str) -> None:
    """
    Render markdown content to HTML and open in browser.

    Args:
        markdown_content: Markdown text to render
    """
    md = markdown.Markdown(
        extensions=[
            ExtraExtension(),
            CodeHiliteExtension(linenums=False, guess_lang=True),
            'toc',
            'fenced_code',
            'tables',
            'nl2br',
        ]
    )

    html_content = md.convert(markdown_content)
    full_html = FULL_HTML_TEMPLATE.format(html_content=html_content)

    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
        f.write(full_html)
        webbrowser.open(f.name)


def render_prompt_with_result(prompt: str, result: str) -> None:
    """
    Render a prompt and its result in markdown format.

    Args:
        prompt: Input prompt text
        result: Model result/response
    """
    combined_markdown = f"# Prompt\n\n{prompt}\n\n# Result\n\n{result}"
    render_markdown_note(combined_markdown)
