import json
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF library

from notes_ai.interfaces import TextExtractor
from notes_ai.loggers import CustomLogger
from notes_ai.models import ExtractedContent, PdfExtractionMetadata, Source


def _extract_text_from_page(page: fitz.Page) -> str:
    """
    Extract text from a single PDF page.
    """
    text = str(page.get_text())
    return text.strip()


def _extract_pages_as_list(pdf_path: str | Path, logger: CustomLogger) -> list[str]:
    """
    Extract text from all pages and return as list.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    logger.debug(f"Opening PDF: {pdf_path.name}")

    try:
        doc = fitz.open(pdf_path)
        pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = _extract_text_from_page(page)
            pages.append(text)
            logger.debug(f"Extracted page {page_num + 1}/{len(doc)}: {len(text)} chars")

        doc.close()
        logger.debug(f"Successfully extracted {len(pages)} pages from {pdf_path.name}")
        return pages

    except Exception as e:
        logger.error(f"Failed to extract text from PDF {pdf_path.name}: {e}")
        raise


def _extract_pages_as_dict(pdf_path: str | Path, logger: CustomLogger) -> dict[int, str]:
    """
    Extract text from all pages and return as dictionary.
    """
    pages_list = _extract_pages_as_list(pdf_path, logger)
    return {i + 1: text for i, text in enumerate(pages_list)}


def single_pdf2text(
    pdf_path: str | Path,
    logger: CustomLogger,
    output_format: Literal["text", "json"] = "text",
    separator: str = "\n\n--- Page Break ---\n\n",
) -> str:
    """
    Extract text from PDF and return as plain text or JSON string.

    Args:
        pdf_path: Path to the PDF file.
        logger: Custom logger instance.
        output_format: Output format - "text" (joined pages) or "json" (structured by page).
        separator: String to separate pages in text mode (default: page break marker).

    Returns:
        str: Extracted text as plain text or JSON string.
    """
    pages_dict = _extract_pages_as_dict(pdf_path, logger)

    if output_format == "json":
        result = json.dumps(pages_dict, ensure_ascii=False, indent=2)
        logger.info(f"Converted {len(pages_dict)} pages to JSON format")
        return result
    else:
        # Join all pages with separator
        result = separator.join(pages_dict.values())
        logger.info(f"Converted {len(pages_dict)} pages to plain text ({len(result)} chars)")
        return result


def save_pdf_text(
    pdf_path: str | Path,
    output_path: str | Path,
    logger: CustomLogger,
    output_format: Literal["text", "json"] = "text",
    separator: str = "\n\n--- Page Break ---\n\n",
) -> str | Path:
    """
    Extract text from PDF and save to file.

    Args:
        pdf_path: Path to the PDF file.
        output_path: Path where to save the extracted text.
        logger: Custom logger instance.
        output_format: Output format - "text" or "json".
        separator: String to separate pages in text mode.

    Returns:
        str | Path: Path to the saved output file.
    """
    text = single_pdf2text(pdf_path, logger, output_format, separator)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(text, encoding="utf-8")
    logger.success(f"Saved extracted text to: {output_path}")
    return output_path


class PDFExtractor(TextExtractor):
    """Extract text from PDF documents using PyMuPDF (fitz)."""

    def __init__(
        self,
        logger: CustomLogger,
    ):
        self.logger = logger

    def supports(self, source: Source) -> bool:
        return (
            source.input_type.lower() in ("pdf", "document")
            or source.location.lower().endswith(".pdf")
        )  # fmt: skip

    async def extract(self, source: Source) -> ExtractedContent:
        pdf_path = Path(source.location)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        pages = _extract_pages_as_list(pdf_path, self.logger)
        text = "\n\n--- Page Break ---\n\n".join(pages)

        return ExtractedContent(
            text=text,
            metadata=PdfExtractionMetadata(
                source_file=pdf_path.name,
                page_count=len(pages),
            ),
        )
