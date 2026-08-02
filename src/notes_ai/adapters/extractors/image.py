from notes_ai.models import Source, ExtractedContent

from pathlib import Path


from notes_ai.utils.logging_config import CustomLogger


import base64
from pathlib import Path
from groq import Groq

from notes_ai.utils.logging_config import CustomLogger

# https://console.groq.com/docs/models
# meta-llama/llama-guard-4-12b
# meta-llama/llama-4-maverick-17b-128e-instruct
# meta-llama/llama-4-scout-17b-16e-instruct


OCR_MODEL = "qwen/qwen3.6-27b"
SYSTEM_PROMPT = (
    "You are an OCR assistant. Follow the user's rules exactly. "
    "Return only the text present in the image."
)

# TODO: rewrite using XML format
PROMPT = (
    "Extract only the literal text visible in the image.\n"
    "\n"
    "Strict rules:\n"
    "- Output plain text only.\n"
    "- Do not describe, summarize, or explain anything.\n"
    "- Do not add headings, labels, comments, or metadata.\n"
    "- Preserve line breaks and reading order.\n"
    "\n"
    "Math Syntax Rules:\n"
    "- Use standard KaTeX/LaTeX syntax only.\n"
    "- DO NOT invent custom commands like \\ecc, \\rad, \\diam, \\vol.\n"
    "- For multi-letter function names or text inside math, ALWAYS use \\operatorname{...} or \\text{...}.\n"
    "  - BAD: \\ecc(u)\n"
    "  - GOOD: \\operatorname{ecc}(u) or \\text{ecc}(u)\n"
    "- For inline math use $...$.\n"
    "- For centered/display equations use:\n"
    "  $$\n"
    "  ...\n"
    "  $$\n"
    "- If nothing is readable, return an empty string."
)

        

class ImageExtractor:



    def __init__(self,llm, logger: CustomLogger):
        self.logger= logger
        self.llm = llm
    async def _run_ocr_completion(
        self,
        image_payloads: list[str],
        logger: CustomLogger,
        separator: str = "\n\n",
    ) -> str:
        """Shared call into LLMClient for both single and batch OCR."""
        result = await self.llm.complete(
            user_prompt=PROMPT,
            system_prompt=SYSTEM_PROMPT,
            images=image_payloads,   # base64 strings; LLMClient builds the image_url blocks
        )
        return str(result)         
        
    def _build_batch_prompt(self, sources : list[Source], logger: CustomLogger, separator: str) -> list[dict]:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]


        # Build a combined prompt with explicit joining rules.
        combined_prompt = (
            PROMPT
            + "\n\nWhen multiple images are provided, process them in order and concatenate the extracted text. "
            "Insert exactly the following separator between images (no extra spaces or lines):\n"
            + separator
        )
        # Build a single user message: PROMPT + all images
        user_content: list[dict] = [{"type": "text", "text": combined_prompt}]

        for source in sources:
            image_name = Path(source.location).name
            base64_image = self.encode_image(source)
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                    },
                }
            )
            logger.debug(f"Added image {image_name} to batch prompt")

        messages.append(
            {
                "role": "user",
                "content": user_content,  # type: ignore
            }
        )
        logger.debug(f"Batch prompt for multiple images constructed:\n{str(messages)}")
        return messages
    


    def supports(self, source: Source) -> bool:
        source_type = source.input_type.lower()
        return source_type  == "image"
    


    def encode_image(self, source :Source):
        with open(source.location, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')




    async def single_img2text(self, source: Source, logger: CustomLogger) -> ExtractedContent:
        image_path = source.location
        image_name = Path(image_path).name
        base64_image = self.encode_image(source=source)

        ocr_text = await self.llm.complete(
            user_prompt=PROMPT,
            system_prompt=SYSTEM_PROMPT,
            images=[base64_image],
            model=OCR_MODEL,
            temperature=0.0,
            max_tokens=2048,
        )

        logger.debug(f"OCR result for image {image_name}: {ocr_text[:50]}")
        return ExtractedContent(ocr_text, metadata={})


    async def batch_img2text(
        self,
        sources: list[Source],
        logger: CustomLogger,
        separator: str = "\n\n",
    ) -> ExtractedContent:
        """
        Extract text from multiple images and combine results.

        Args:
            sources: List of Source objects pointing to image files.
            logger: Custom logger instance.
            separator: String to join results (default: double newline).

        Returns:
            ExtractedContent: Combined OCR text from all images.
        """
        logger.debug(f"Starting batch OCR for {len(sources)} images")

        base64_images = [self.encode_image(source=s) for s in sources]

        ocr_text = await self.llm.complete(
            user_prompt=PROMPT,
            system_prompt=SYSTEM_PROMPT,
            images=base64_images,
            model=OCR_MODEL,
            temperature=0.0,
            max_tokens=2048,
        )

        logger.debug(f"Batch OCR result: {ocr_text[:100]}")
        return ExtractedContent(ocr_text, metadata={})
      
    async def extract(self, source: Source | list[Source], **kwargs):
         if isinstance(source, list):
              return await self.batch_img2text(sources=source,logger = self.logger)
         else: 
              return await self.single_img2text(source=source,logger = self.logger)     
             