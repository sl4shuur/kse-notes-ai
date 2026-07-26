from notes_ai.interfaces.extractor import TextExtractor
from notes_ai.models import Source, ExtractedContent

class YouTubeExtractor(TextExtractor):
    def supports(self, source: Source) -> bool:
        return source.type == "youtube"

    async def extract(self, source: Source) -> ExtractedContent:
        # Implement the logic to extract content from YouTube
        # This is a placeholder implementation
        content = f"Extracted content from YouTube video: {source.url}"
        return ExtractedContent(content=content)