from groq import Groq
import matplotlib.pyplot as plt

SYS_PROMPT = r"""<system>
You are a data visualization expert specializing in creating clear, educational matplotlib visualizations for technical documentation.

Your task: Generate Python code that creates a visualization to illustrate a concept from the provided text and visual instructions.

Requirements:
- Use matplotlib and/or seaborn
- Code must be complete and executable
- Include clear title and labels
- Use appropriate colors and styling
- Keep it simple and focused on ONE concept
- Add comments explaining key parts
- Set figure size appropriately (usually 10x6 or 8x5)
- Use sns.set_style() for clean look

Output ONLY the Python code block, no explanations outside the code.
</system>"""


USER_PROMPT = r"""<user>
Create a visualization for the following concept:

Input Data:
<context>
{paragraph_text}
</context>

Visualization Instructions:
<design_brief>
{visual_instructions}
</design_brief>

Focus on illustrating the main idea visually. The code should be self-contained and ready to run.
</user>"""


def generate_plt_vis_code(clean_text: str, prompt: str, model: str = 'openai/gpt-oss-120b') -> str:
    """
    Generate matplotlib code for visualizing a concept

    Args:
        paragraph: The text content to visualize
        api_key: Anthropic API key

    Returns:
        Generated Python code as string
    """
    client = Groq()

    # Format user prompt
    user_msg = USER_PROMPT.format(
        paragraph_text=clean_text, visual_instructions=prompt)

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
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()

    return code


def save_plt_vis_img(code: str, img_path: str) -> None:
    """
    Execute matplotlib code and save the resulting figure as an image

    Args:
        code: The Python code to execute
        img_path: Path to save the generated image
    """
    # Create a local namespace for executing the code
    local_namespace = {}

    # Execute the provided code
    exec(code, globals())

    # Save the current figure
    plt.savefig(img_path, bbox_inches='tight')
    plt.close()
