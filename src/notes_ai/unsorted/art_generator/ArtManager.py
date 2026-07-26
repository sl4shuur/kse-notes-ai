import os
import json
from typing import Optional, Literal
from dataclasses import dataclass
from groq import Groq


from notes_ai.unsorted.art_generator.plt_vis import generate_plt_vis_code, save_plt_vis_img
from notes_ai.unsorted.art_generator.mermaid_vis import generate_mermaid_code


@dataclass
class VisualizationDecision:
    """Decision about visualization for a section"""
    needs_visualization: bool
    viz_type: Optional[Literal['plt', 'mermaid']] = None
    prompt: Optional[str] = None


CLASSIFIER_PROMPT = r"""<system>
You are an expert at analyzing technical documentation and deciding when visualizations would enhance understanding.

Analyze the provided section and decide:
1. Does this section need a visualization? (yes/no)
2. If yes, what type? (plt for data/plots, mermaid for diagrams/architectures)
3. If yes, provide detailed instructions for creating the visualization

Visualization is beneficial for:
- Data relationships, distributions, trends → plt
- System architectures, workflows, neural networks → mermaid
- Algorithm flows, decision trees → mermaid
- Statistical concepts with sample data → plt

Visualization is NOT needed for:
- Pure text explanations without visual concepts
- Code examples that are self-explanatory
- Simple definitions
- Lists of features

Respond in JSON format:
{
    "needs_visualization": true/false,
    "viz_type": "plt" or "mermaid" or null,
    "prompt": "Detailed instructions for visualization" or null
}
</system>"""


USER_CLASSIFIER_PROMPT = r"""<user>
Analyze this section and decide if it needs visualization:

<section>
{section_content}
</section>

Return JSON with your decision.
</user>"""


class ArtManager:
    """Manager for generating and integrating visualizations into notes"""

    def __init__(
        self,
        output_dir: str = "./",
        model: str = "openai/gpt-oss-120b"
    ):
        """
        Initialize ArtManager

        Args:
            output_dir: Directory to save generated images
            model: Model to use for generation
        """
        self.output_dir = output_dir
        self.model = model
        self.client = Groq()

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def _classify_section(self, section_content: str) -> VisualizationDecision:
        """
        Classify if section needs visualization and what type

        Args:
            section_content: The section content to analyze

        Returns:
            VisualizationDecision with classification results
        """
        user_msg = USER_CLASSIFIER_PROMPT.format(
            section_content=section_content)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": CLASSIFIER_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )

        # Parse JSON response
        result = json.loads(str(response.choices[0].message.content))

        return VisualizationDecision(
            needs_visualization=result.get("needs_visualization", False),
            viz_type=result.get("viz_type"),
            prompt=result.get("prompt")
        )

    def _generate_plt_visualization(
        self,
        section_content: str,
        prompt: str,
        section_id: str
    ) -> str:
        """
        Generate matplotlib visualization and return markdown

        Args:
            section_content: Original section text
            prompt: Visualization instructions
            section_id: Unique identifier for this section

        Returns:
            Markdown string with image reference
        """
        # Generate code
        code = generate_plt_vis_code(section_content, prompt, self.model)

        # Save image
        img_filename = f"{section_id}_plt.png"
        img_path = os.path.join(self.output_dir, img_filename)

        try:
            save_plt_vis_img(code, img_path)

            # Return markdown
            return f"\n\n![Visualization]({img_path})\n"
        except Exception as e:
            print(f"Error generating/saving plt visualization: {e}")
            print(f"Generated code was:\n{code}")
            return ""

    def _generate_mermaid_visualization(
        self,
        section_content: str,
        prompt: str
    ) -> str:
        """
        Generate mermaid diagram and return markdown

        Args:
            section_content: Original section text
            prompt: Diagram instructions

        Returns:
            Markdown string with mermaid code block
        """
        # Generate mermaid code
        mermaid_code = generate_mermaid_code(
            section_content, prompt, self.model)

        # Return markdown with mermaid block
        return f"\n\n```mermaid\n{mermaid_code}\n```\n"

    def process_section(
        self,
        section_content: str,
        section_id: str
    ) -> str:
        """
        Process a section and add visualization if needed

        Args:
            section_content: The markdown section content (starting with ##)
            section_id: Unique identifier for this section (e.g., "chapter_3_section_1")

        Returns:
            Section content with visualization appended if applicable
        """
        # Step 1: Classify
        decision = self._classify_section(section_content)

        if not decision.needs_visualization:
            return section_content

        # Step 2: Generate visualization based on type
        if decision.viz_type == "plt":
            viz_markdown = self._generate_plt_visualization(
                section_content,
                decision.prompt,
                section_id
            )
        elif decision.viz_type == "mermaid":
            viz_markdown = self._generate_mermaid_visualization(
                section_content,
                decision.prompt
            )
        else:
            # Unknown type, skip
            return section_content

        # Step 3: Append visualization to section
        return section_content + viz_markdown

    def process_document(
        self,
        document_content: str,
        document_id: str = "doc"
    ) -> str:
        """
        Process entire document, adding visualizations to sections

        Args:
            document_content: Full markdown document
            document_id: Identifier for this document

        Returns:
            Document with visualizations added
        """
        # Split document into sections (by ##)
        sections = document_content.split('\n## ')

        # Process each section
        processed_sections = []
        for idx, section in enumerate(sections):
            if idx == 0:
                # First section might not start with ##
                processed_sections.append(section)
            else:
                # Add back the ## that was removed by split
                section = '## ' + section
                section_id = f"{document_id}_section_{idx}"
                processed_section = self.process_section(section, section_id)
                processed_sections.append(processed_section)

        return '\n'.join(processed_sections)
