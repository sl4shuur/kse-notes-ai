from dataclasses import dataclass


@dataclass
class Source:
  input_type: str
  location : str
  title: str
  metadata: dict


@dataclass
class ExtractedContent:
    text: str
    metadata: dict



@dataclass
class Note:
    title: str
    content: str
    date_created: str
    metadata: dict
