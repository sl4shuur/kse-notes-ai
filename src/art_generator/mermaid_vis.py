from groq import Groq

SYS_PROMPT = r"""<system>
You are a diagram expert specializing in creating clear, educational Mermaid diagrams for technical documentation.

Your task: Generate Mermaid diagram code that illustrates a concept from the provided text and visual instructions.

Requirements:
- Use Mermaid syntax (graph/flowchart)
- Code must be valid Mermaid syntax
- Include clear node labels with proper subscripts/superscripts using HTML tags
- Use appropriate node shapes (circles for neurons, rectangles for layers, etc.)
- Use descriptive edge labels where needed
- Apply professional styling (colors, strokes)
- Keep it simple and focused on ONE concept
- Add comments using %% for key sections

Available node shapes:
- Rectangle: [text]
- Rounded rectangle: (text)
- Circle: ((text))
- Asymmetric: >text]
- Rhombus: {text}

Styling examples:
- style NodeID fill:#e1f5fe,stroke:#01579b
- style SubgraphName fill:#fff3e0,stroke:#e65100

Output ONLY the Mermaid code block, no explanations outside the code.
</system>"""


USER_PROMPT = r"""<user>
Create a diagram for the following concept:

Input Data:
<context>
{paragraph_text}
</context>

Diagram Instructions:
<design_brief>
{visual_instructions}
</design_brief>

Focus on illustrating the architecture/structure/flow visually. The code should be valid Mermaid syntax.
</user>"""


def generate_mermaid_code(
    clean_text: str,
    prompt: str,
    model: str = 'openai/gpt-oss-120b'
) -> str:
    """
    Generate Mermaid diagram code for visualizing a concept

    Args:
        clean_text: The cleaned text content to visualize
        prompt: Visual instructions for the diagram
        model: Model to use for generation

    Returns:
        Generated Mermaid code as string
    """
    client = Groq()

    # Format user prompt
    user_msg = USER_PROMPT.format(
        paragraph_text=clean_text,
        visual_instructions=prompt
    )

    # Call the model
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=8192,
    )

    # Extract code from response
    code = str(response.choices[0].message.content)

    # Remove markdown code fences if present
    if "```mermaid" in code:
        code = code.split("```mermaid")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()

    return code
