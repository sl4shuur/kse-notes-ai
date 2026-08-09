"""Validated domain models shared across Notes AI."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DomainModel(BaseModel):
    """Strict base model for application-owned data."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceType(StrEnum):
    YOUTUBE = "youtube"
    WEB = "web"
    PDF = "pdf"
    IMAGE = "image"
    AUDIO = "audio"


class SourceMetadataBase(DomainModel):
    title: NonEmptyString
    error: str | None = None


class YouTubeMetadata(SourceMetadataBase):
    source_type: Literal[SourceType.YOUTUBE] = SourceType.YOUTUBE
    author: str | None = None
    channel: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    upload_date: str | None = None
    description: str | None = None
    view_count: int | None = Field(default=None, ge=0)
    url: NonEmptyString


class WebMetadata(SourceMetadataBase):
    source_type: Literal[SourceType.WEB] = SourceType.WEB
    author: str | None = None
    published_date: str | None = None
    description: str | None = None
    hostname: str | None = None
    url: NonEmptyString
    site_name: str | None = None


class PdfMetadata(SourceMetadataBase):
    source_type: Literal[SourceType.PDF] = SourceType.PDF
    author: str | None = None
    subject: str | None = None
    keywords: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    modification_date: str | None = None
    page_count: int | None = Field(default=None, ge=0)


class ImageMetadata(SourceMetadataBase):
    source_type: Literal[SourceType.IMAGE] = SourceType.IMAGE
    image_format: str | None = None
    color_mode: str | None = None
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)


class AudioTag(DomainModel):
    name: NonEmptyString
    value: str


class AudioMetadata(SourceMetadataBase):
    source_type: Literal[SourceType.AUDIO] = SourceType.AUDIO
    duration_seconds: float | None = Field(default=None, ge=0)
    bitrate: int | None = Field(default=None, ge=0)
    sample_rate: int | None = Field(default=None, ge=0)
    tags: tuple[AudioTag, ...] = ()


SourceMetadata = Annotated[
    YouTubeMetadata | WebMetadata | PdfMetadata | ImageMetadata | AudioMetadata,
    Field(discriminator="source_type"),
]


class Source(DomainModel):
    input_type: SourceType
    location: NonEmptyString
    title: NonEmptyString
    metadata: SourceMetadata

    @model_validator(mode="after")
    def metadata_matches_source_type(self) -> Self:
        if self.metadata.source_type != self.input_type:
            raise ValueError("metadata source_type must match input_type")
        return self


class YouTubeExtractionMetadata(DomainModel):
    source_type: Literal[SourceType.YOUTUBE] = SourceType.YOUTUBE
    method: Literal["subtitles", "whisper"]
    language_code: str | None = None


class WebExtractionMetadata(DomainModel):
    source_type: Literal[SourceType.WEB] = SourceType.WEB
    title: str | None = None
    author: str | None = None
    published_date: str | None = None
    url: str | None = None


class PdfExtractionMetadata(DomainModel):
    source_type: Literal[SourceType.PDF] = SourceType.PDF
    source_file: NonEmptyString
    page_count: int = Field(ge=0)


class ImageExtractionMetadata(DomainModel):
    source_type: Literal[SourceType.IMAGE] = SourceType.IMAGE
    image_count: int = Field(default=1, gt=0)


class AudioExtractionMetadata(DomainModel):
    source_type: Literal[SourceType.AUDIO] = SourceType.AUDIO
    source_file: NonEmptyString
    chunk_count: int = Field(ge=0)


ExtractionMetadata = Annotated[
    YouTubeExtractionMetadata
    | WebExtractionMetadata
    | PdfExtractionMetadata
    | ImageExtractionMetadata
    | AudioExtractionMetadata,
    Field(discriminator="source_type"),
]


class ExtractedContent(DomainModel):
    text: NonEmptyString
    metadata: ExtractionMetadata


class NoteMetadata(DomainModel):
    extraction: ExtractionMetadata
    model: NonEmptyString
    generated: bool = True
    colored: bool = True
    cleaned: bool = True


class Note(DomainModel):
    title: NonEmptyString
    content: NonEmptyString
    source: Source
    date_created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: NoteMetadata
