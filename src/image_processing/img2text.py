import os
import base64
from pathlib import Path
from groq import Groq

from src.utils.logging_config import CustomLogger

# https://console.groq.com/docs/models
# meta-llama/llama-guard-4-12b
# meta-llama/llama-4-maverick-17b-128e-instruct
# meta-llama/llama-4-scout-17b-16e-instruct


OCR_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
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


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def _build_batch_prompt(image_paths: list[str | Path], logger: CustomLogger, separator: str) -> list[dict]:
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

    for image_path in image_paths:
        image_name = Path(image_path).name
        base64_image = encode_image(image_path)
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


def single_img2text(image_path: str | Path, logger: CustomLogger, model: str = OCR_MODEL) -> str:
    client = Groq()
    image_name = Path(image_path).name

    # Getting the base64 string
    base64_image = encode_image(image_path)

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            },
        ],
        model=model,
        temperature=0.0,
        max_tokens=8192,
        top_p=1.0,
    )
    ocr_text = str(chat_completion.choices[0].message.content)
    logger.debug(f"OCR result for image {image_name}: {ocr_text[:50]}")
    return ocr_text


def batch_img2text(
    image_paths: list[str | Path],
    logger: CustomLogger,
    model: str = OCR_MODEL,
    separator: str = "\n\n"
) -> str:
    """
    Extract text from multiple images and combine results.

    Args:
        image_paths: List of paths to image files.
        logger: Custom logger instance.
        model: Groq vision model to use for OCR.
        separator: String to join results (default: double newline).

    Returns:
        str: Combined OCR text from all images.
    """
    client = Groq()
    logger.debug(f"Starting batch OCR for {len(image_paths)} images")
    messages = _build_batch_prompt(image_paths, logger, separator)
    chat_completion = client.chat.completions.create(
        messages=messages,  # type: ignore
        model=model,
        temperature=0.0,
        max_tokens=8192,  # max amount is 8192
        top_p=1.0,
    )
    ocr_text = str(chat_completion.choices[0].message.content)
    logger.debug(f"Batch OCR result: {ocr_text[:100]}")
    return ocr_text