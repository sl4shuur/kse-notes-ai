# Notes AI

Notes AI turns YouTube videos, web articles, PDFs, images, and audio files into structured Markdown study notes. The target product combines multi-source content extraction, an explicit note-generation pipeline, semantic highlighting, generated visuals, related-note discovery, and a web interface.

> [!NOTE]
> **Project status:** active refactoring. The repository already contains working extraction and note-generation modules, but the codebase is being reorganized into a stable Python package before new product features are added.

## Target capabilities

- Extract content from YouTube, web pages, PDFs, images, and audio files
- Generate structured Markdown notes through a multi-step pipeline
- Add semantic highlighting, examples, metaphors, diagrams, and plots
- Store notes in a local knowledge base
- Find related notes with embeddings and ChromaDB
- Create and browse notes through a React web interface
- Inspect LLM calls and pipeline steps in Arize Phoenix
- Run the complete stack with Docker Compose

## Technology stack

- **Backend:** Python 3.13, FastAPI
- **Package management:** `uv`
- **LLM provider:** Groq
- **Frontend:** React, TypeScript, Vite
- **Vector storage:** ChromaDB
- **Observability:** Arize Phoenix
- **Infrastructure:** Docker Compose
- **Testing:** pytest

---

## Local setup

### Requirements

- Python 3.13
- [`uv`](https://docs.astral.sh/uv/)
- Git
- FFmpeg
- Groq API key

### Installation

```bash
git clone <repo-url>
cd kse-notes-ai
uv sync --group dev
cp .env.example .env
```

Add the required values to `.env`, including the Groq API key.

Install Playwright browsers only when dynamic web-page extraction is needed:

```bash
uv run playwright install
```

On Windows, install the Microsoft Visual C++ Redistributable if a native dependency cannot be installed.

### Current execution

The repository is currently being migrated to the package layout described below. During the refactoring phase, verify the available CLI commands with:

```bash
uv run python main.py --help
```

After the package migration, the preferred entry point will be:

```bash
uv run notes-ai --help
```

### Tests

```bash
uv run pytest -q
```

---

## Development principles

1. **Preserve working behavior before adding features.** Refactoring should not remove supported input types or existing note-generation capabilities.
2. **Keep domain logic independent of frameworks.** Extraction, synthesis, and storage must not depend directly on FastAPI, React, or CLI code.
3. **Depend on interfaces at integration boundaries.** LLM providers, storage backends, and vector databases should be replaceable without rewriting the pipeline.
4. **Prefer explicit pipelines over agent frameworks.** Plain Python classes are sufficient until orchestration requirements justify a heavier tool.
5. **Make each phase demonstrable.** Every week ends with a working vertical slice, tests, and documented run instructions.
6. **Keep scope realistic.** Core functionality has priority over optional modes, chat, export, or advanced agent behavior.

---

## Roadmap

**Kickoff:** 27 July 2026  
**Demo:** 16 August 2026

| Phase | Focus | Midweek check-in | Deadline |
| --- | --- | --- | --- |
| 1 | Refactor and package foundation | 29 July | 2 August |
| 2 | Multi-step synthesis and web application | 5 August | 9 August |
| 3 | Knowledge base, containers, observability, and demo | 12 August | 16 August |

The implementation should progress from a simple working version to a clean extensible version. LangGraph or another agent framework is intentionally out of scope unless the plain-class pipeline becomes insufficient.

---

## Phase 1 — Refactor the existing codebase

### Goal

Turn the current code into a clean, installable Python package without changing the main user flow.

The focus of this phase is not to redesign the whole application. It is to:

- move code into a consistent package structure;
- separate application contracts from external implementations;
- remove duplicated configuration and orchestration;
- make the main workflow easier to test and extend.

### Target structure

```text
src/
└── notes_ai/
    ├── __init__.py
    ├── cli.py
    ├── models.py
    ├── pipeline.py
    ├── interfaces/
    │   ├── __init__.py
    │   ├── extractor.py
    │   ├── llm.py
    │   └── storage.py
    └── adapters/
        ├── __init__.py
        ├── extractors/
        │   ├── youtube.py
        │   ├── web.py
        │   ├── pdf.py
        │   ├── image.py
        │   └── audio.py
        ├── llm/
        │   └── groq.py
        └── storage/
            └── markdown.py
```

The structure should remain small. New folders should be added only when there is enough code to justify them.

### 1. Create the Python package

- [ ] Move application code under `src/notes_ai/`
- [ ] Configure `notes_ai` as the only importable package
- [ ] Replace imports such as `from src...` with `from notes_ai...`
- [ ] Add a `notes-ai` CLI entry point in `pyproject.toml`
- [ ] Keep the root `main.py` only as a temporary compatibility wrapper, then remove it
- [ ] Update `.gitignore` and remove committed caches, generated files, and local environment files

All internal imports should follow the same pattern:

```python
from notes_ai.pipeline import create_note
from notes_ai.adapters.llm.groq import GroqLLMClient
```

### 2. Add shared models

Create a small number of models in `notes_ai/models.py`.

Suggested models:

- [ ] `Source` — input type, location, title, and metadata
- [ ] `ExtractedContent` — normalized text and extraction metadata
- [ ] `Note` — title, Markdown content, source, and timestamps

Use dataclasses or Pydantic models, but do not mix provider-specific SDK objects into these models.

### 3. Define simple interfaces

The `interfaces/` folder should contain only small contracts that describe what the application needs.

#### Extractor interface

```python
from typing import Protocol


class TextExtractor(Protocol):
    def supports(self, source: Source) -> bool: ...
    async def extract(self, source: Source) -> ExtractedContent: ...
```

#### LLM interface

```python
class LLMClient(Protocol):
    async def generate(self, prompt: str) -> str: ...
```

#### Storage interface

```python
class NoteStore(Protocol):
    async def save(self, note: Note) -> None: ...
```

Keep these interfaces minimal. Add methods only when the current application actually needs them.

### 4. Move external logic into adapters

The `adapters/` folder should contain implementations that depend on external tools, APIs, file formats, or libraries.

Examples:

- `YouTubeExtractor`
- `WebArticleExtractor`
- `PDFExtractor`
- `ImageExtractor`
- `AudioExtractor`
- `GroqLLMClient`
- `MarkdownNoteStore`

Existing functions from modules such as `yt_processing`, `web_processing`, and `audio_processing` can initially be reused inside these adapters. They do not need to be rewritten immediately.

The important rule is that the rest of the application should call the interfaces, not provider-specific functions directly.

### 5. Simplify the main pipeline

Use one small orchestration function in `notes_ai/pipeline.py` instead of introducing several service classes.

```python
async def create_note(
    source: Source,
    extractors: list[TextExtractor],
    llm: LLMClient,
    store: NoteStore,
) -> Note:
    extractor = next(
        (item for item in extractors if item.supports(source)),
        None,
    )

    if extractor is None:
        raise UnsupportedSourceError(source.location)

    content = await extractor.extract(source)
    note = await generate_note(content, llm)
    await store.save(note)

    return note
```

This function should coordinate the workflow only:

1. select an extractor;
2. extract the source content;
3. generate the note;
4. save the result.

Detailed extraction, prompt construction, formatting, and persistence should stay inside their respective modules.

### 6. Preserve the current generation flow

Do not rewrite the full note-generation pipeline during this phase.

- [ ] Wrap the current generation flow behind one function such as `generate_note()`
- [ ] Keep existing outline, formatting, artwork, and cleanup steps working
- [ ] Move these steps gradually only when necessary
- [ ] Avoid mixing refactoring with major prompt or product changes

The goal is to create a stable boundary around the current behavior before improving it in later phases.

### 7. Centralize configuration and errors

- [ ] Move environment-variable loading into `config.py`
- [ ] Keep API keys, model names, output paths, and timeouts in one settings object
- [ ] Add a small set of application errors, for example:
  - `UnsupportedSourceError`
  - `ExtractionError`
  - `LLMError`
  - `StorageError`
- [ ] Remove duplicate configuration and logging setup after migration

### 8. Add focused tests

Minimum tests for this phase:

- [ ] the correct extractor is selected for a source;
- [ ] unsupported sources produce a clear error;
- [ ] `create_note()` works with fake extractor, LLM, and storage adapters;
- [ ] `MarkdownNoteStore` writes a note into a temporary directory;
- [ ] one regression test covers the current note-generation flow.

Use lightweight fake adapters in unit tests instead of network calls.

```text
tests/
├── unit/
│   ├── test_pipeline.py
│   ├── test_extractors.py
│   └── test_markdown_storage.py
└── integration/
    └── test_note_generation.py
```

Tests should not require a real Groq key, browser, FFmpeg, or external network access unless explicitly marked as integration tests.

### 9. Update documentation

- [ ] Update installation and launch commands in `README.md`
- [ ] Add the target project structure
- [ ] Document the basic request flow:

```text
CLI → create_note() → extractor → LLM → Markdown storage
```

- [ ] Add a short note explaining the role of `interfaces/` and `adapters/`

### Phase 1 acceptance criteria

The phase is complete when:

- [ ] all application code is importable through `notes_ai`
- [ ] the project installs successfully with `uv sync`
- [ ] `uv run notes-ai` starts the CLI
- [ ] the current note-generation flow still works
- [ ] extractors, Groq, and Markdown storage are placed under `adapters/`
- [ ] contracts are placed under `interfaces/`
- [ ] the main workflow is coordinated by one small pipeline function
- [ ] an offline end-to-end test passes with fake adapters
- [ ] secrets, caches, generated notes, and local environment files are not tracked
- [ ] README instructions match the actual repository

### Phase one progress

Phase one has been successfully completed. The legacy codebase was refactored into a structured Python package (`notes_ai`). Here is how each goal was accomplished:

1. **Create the Python package**: The legacy application was restructured into a clean package under `src/notes_ai/`. We configured the CLI entry point in `pyproject.toml` (enabling `uv run notes-ai`), removed the legacy `main.py` orchestrator, and set up `cli.py` to handle environment and path resolutions.
2. **Add shared models**: Built lightweight domain objects (`Source`, `ExtractedContent`, `Note`) using Python's `@dataclass` in `src/notes_ai/models.py`.
3. **Define simple interfaces and custom exceptions**: Established strict `Protocol` contracts for `TextExtractor`, `LLMClient`, and `NoteStore` in `src/notes_ai/interfaces/`. Furthermore, we created `interfaces/exceptions.py` to define custom error classes (`UnsupportedSourceError`, `ExtractionError`, `LLMError`, `StorageError`), which accept an `extra_info` parameter for better error tracking.
4. **Move external logic into adapters**: Third-party dependencies and integrations were isolated into `src/notes_ai/adapters/`. This encapsulates our extractors (YouTube, Web, PDF, Image, Audio), the `GroqLLMClient`, and the `MarkdownNoteStore`.
5. **Implement an advanced synthesis pipeline**: The `src/notes_ai/pipeline.py` orchestrator was built to handle end-to-end processing. It features format detection (`process_content`) and extensive metadata extraction (`extract_metadata`) using libraries like `trafilatura` (web), `YoutubeDL` (video), `fitz` (PDF), `mutagen` (audio), and PIL (images). The core `create_note` function delegates to the appropriate extractor, generates content via `NoteGenerator`, optionally applies modular enhancements (`OutlineGenerator`, `NoteEnricher`, `ColorCategorizer`), and scrubs the output with `clean_note`.
6. **Preserve the current generation flow**: The legacy prompt engineering logic (including semantic coloring rules, examples, and metaphors) was successfully preserved inside `adapters/llm_services/note_generator.py`.
7. **Centralize configuration**: `config.py` was created to standardize paths (`DATA_DIR`, `TEST_DATA_DIR`, `TEMP_AUDIO_DIR`, etc.) and handle `.env` validation. Logging was also centralized using a `CustomLogger` setup.
8. **Add focused tests**: *Not yet implemented.* (The `tests/` directory and offline integration tests specified in the requirements have not been added to the repository yet).
9. **Update documentation**: The README was updated to reflect the new architecture, and the CLI documentation was appended.

#### CLI User Guide & Documentation

This guide provides full documentation on using the `notes-ai` Command-Line Interface (CLI).

##### Quick Start & Global Help

```bash
uv run python -m notes_ai.cli --help
```
*or via the installed package entry point:*
```bash
uv run notes-ai --help
```

##### Global Help Output
```text
usage: cli.py [-h] [-o OUTPUT_DIR] [-n NAME] [-v] sources [sources ...]

Notes AI — Generate structured study notes from YouTube, web, PDF, image, or audio sources.

positional arguments:
  sources               One or more URLs or local file paths to process.

options:
  -h, --help            show this help message and exit
  -o, --output-dir OUTPUT_DIR
                        Directory to save the generated markdown note(s) (default: output).
  -n, --name NAME       Custom title/name for the note (only applicable when processing a single source).
  -v, --verbose         Enable debug logging.
```

##### Command Reference

###### Synopsis
```bash
uv run python -m notes_ai.cli <SOURCES...> [OPTIONS]
```

###### Positional Arguments
| Argument | Type | Nargs | Description |
| :--- | :--- | :---: | :--- |
| `sources` | `str` | `+` (1 or more) | One or more YouTube URLs, Web URLs, or local file paths (`.pdf`, `.png`, `.mp3`, etc.) |

###### Options & Flags
| Option / Flag | Short | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| `--output-dir` | `-o` | `str` | `output` | Directory where generated `.md` note files will be saved |
| `--name` | `-n` | `str` | `None` | Custom note filename (without extension). Only valid for single-source runs |
| `--verbose` | `-v` | flag | `False` | Enables `DEBUG` level log output in terminal |
| `--help` | `-h` | flag | — | Displays the global help screen and exits |

##### Supported Source Formats

| Format | Category | File Extension / Pattern | Extractor Adapter |
| :--- | :--- | :--- | :--- |
| **YouTube** | Video URL | `youtube.com/watch?v=...`, `youtu.be/...` | `YouTubeExtractor` |
| **Web Pages** | Article URL | `http://...`, `https://...` | `WebExtractor` |
| **PDF** | Document | `.pdf` | `PDFExtractor` |
| **Image (OCR)** | Image | `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp` | `ImageExtractor` |
| **Audio** | Audio | `.mp3`, `.wav`, `.m4a`, `.opus`, `.flac`, `.aac` | `AudioExtractor` |

##### Examples

###### 1. Single Source Processing

**YouTube Video:**
```bash
uv run python -m notes_ai.cli "https://www.youtube.com/watch?v=Z6z_feacXW8"
```
*Saves output to `./output/note_1.md`*

**PDF Document with Custom Name & Output Directory:**
```bash
uv run python -m notes_ai.cli "/path/to/report.pdf" -o my_notes -n "Elections_Analysis"
```
*Saves output to `./my_notes/Elections_Analysis.md`*

**Image File with Verbose Logging:**
```bash
uv run python -m notes_ai.cli "/path/to/diagram.png" -v
```

###### 2. Batch Processing (Multiple Sources)

You can pass multiple files or URLs at once in a single command:

```bash
uv run python -m notes_ai.cli "https://youtu.be/Z6z_feacXW8" "report.pdf" "lecture.mp3" -o batch_output
```

*Processes each source sequentially and creates:*
* `./batch_output/note_1.md`
* `./batch_output/report.md`
* `./batch_output/lecture.md`

##### Environment Setup

The CLI uses Groq LLMs to synthesize extracted content into study notes. Make sure your `GROQ_API_KEY` is defined in your `.env` file or environment variables:

```bash
# In your .env file
GROQ_API_KEY="your_actual_groq_api_key"

# Or exported directly in shell
export GROQ_API_KEY="your_actual_groq_api_key"
```

---

## Phase 2 — Multi-step synthesis and web application

### Goal

Replace the transitional legacy orchestration with explicit pipeline steps and expose note creation through a stable HTTP API and a usable React interface.

### Synthesis pipeline

Create a shared mutable or immutable `NoteContext` model containing the extracted text, outline, draft, enriched Markdown, artifacts, metadata, and step status.

Define a step interface:

```python
class SynthesisStep(Protocol):
    name: str
    async def run(self, context: NoteContext) -> NoteContext: ...
```

Implement:

- [ ] `PlannerStep` — create the note outline
- [ ] `WriterStep` — produce the main draft
- [ ] `EnrichmentStep` — add examples and metaphors where useful
- [ ] `ColorMarkupStep` — apply semantic highlighting
- [ ] `VisualizationStep` — generate diagrams or plots through existing art helpers
- [ ] `CleanupStep` — normalize and validate final Markdown
- [ ] `SequentialSynthesisPipeline` — run configured steps in order

The pipeline should support a reduced set of steps without creating separate implementations for every mode. A fast mode may skip enrichment and visualization.

### Backend API

Create a FastAPI application with versioned routes:

- [ ] `POST /api/v1/notes` — create a note from a URL or uploaded file
- [ ] `GET /api/v1/notes` — list notes
- [ ] `GET /api/v1/notes/{note_id}` — retrieve one note
- [ ] `GET /api/v1/health` — health check

Additional requirements:

- [ ] validate URLs, files, source types, and size limits
- [ ] return consistent error responses
- [ ] expose pipeline status through polling, server-sent events, or a deliberately simple synchronous response
- [ ] keep HTTP schemas separate from core domain models when they begin to differ
- [ ] generate OpenAPI documentation automatically through FastAPI

### React interface

- [ ] scaffold React with TypeScript and Vite
- [ ] create a note list page
- [ ] create a Markdown note viewer
- [ ] add a create-note form for URLs and file uploads
- [ ] show current pipeline step and failure messages
- [ ] add basic loading, empty, and error states
- [ ] support a practical responsive layout

### Observability

- [ ] add Arize Phoenix to the local stack
- [ ] trace LLM requests and synthesis steps
- [ ] attach source type, model, duration, and success status as trace metadata
- [ ] avoid logging API keys or full private documents by default
- [ ] document the local Phoenix URL and one trace-inspection workflow

### Phase 2 acceptance criteria

- [ ] at least three source types can create notes through the API
- [ ] React can create, list, and display notes
- [ ] each synthesis step is visible in logs or traces
- [ ] fast and full pipeline configurations are demonstrable
- [ ] three representative sample notes are available for the demo
- [ ] unit tests cover step ordering and failure propagation
- [ ] API integration tests cover create, list, and retrieve operations

---

## Phase 3 — Knowledge base, containers, and demo

### Goal

Add related-note discovery, package the system as a reproducible multi-container application, and prepare a stable end-to-end demonstration.

### Knowledge base

Define a separate vector-storage interface:

```python
class VectorStore(Protocol):
    async def add(self, chunks: list[NoteChunk]) -> None: ...
    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]: ...
```

Tasks:

- [ ] implement a ChromaDB adapter
- [ ] split finalized notes into traceable chunks
- [ ] store note and chunk identifiers with embeddings
- [ ] retrieve top-k related chunks
- [ ] add a “Related notes” section without duplicating the current note
- [ ] show related notes in the React interface
- [ ] support a configurable Obsidian vault directory as the Markdown store

### Docker Compose

Create containers for at least:

| Service | Responsibility |
| --- | --- |
| `api` | FastAPI backend and note pipeline |
| `web` | React production build |
| `phoenix` | tracing and LLM observability |

Optional: run ChromaDB as a separate service when this simplifies persistence or inspection.

Tasks:

- [ ] add a backend `Dockerfile`
- [ ] add a frontend `Dockerfile`
- [ ] add health checks where practical
- [ ] configure service networking and environment variables
- [ ] persist notes and vector data through named volumes or mounted directories
- [ ] add `.dockerignore` files
- [ ] document `docker compose up --build`

### Reliability and demo preparation

- [ ] handle bad URLs, unsupported files, empty extraction results, provider timeouts, and malformed Markdown
- [ ] verify setup on a clean machine or clean container environment
- [ ] prepare a deterministic backup sample in case an external service fails
- [ ] create a 5–7 minute demo flow:
  1. submit a source;
  2. observe pipeline progress;
  3. open the generated note;
  4. inspect related notes;
  5. show the corresponding Phoenix trace.
- [ ] document known limitations and intentionally deferred features

### Stretch goals

Only attempt these after all acceptance criteria are met:

- chat over notes with retrieval-augmented generation;
- export selected notes as a ZIP archive;
- additional LLM providers;
- background task queue for long-running jobs.

### Phase 3 acceptance criteria

- [ ] related-note retrieval works for stored notes
- [ ] `docker compose up --build` starts the documented stack
- [ ] data survives container restart
- [ ] one real note run is visible in Phoenix
- [ ] the full demo path works from a clean checkout
- [ ] README instructions have been verified rather than copied from an earlier state

---

## Target repository layout

```text
kse-notes-ai/
├── .github/
│   └── workflows/
│       └── tests.yml
├── docs/
│   └── architecture.md
├── prompts/
│   ├── planner.md
│   ├── writer.md
│   └── enrichment.md
├── src/
│   └── notes_ai/
│       ├── __init__.py
│       ├── cli/
│       │   └── app.py
│       ├── core/
│       │   ├── exceptions.py
│       │   ├── models.py
│       │   └── settings.py
│       ├── ingestion/
│       │   ├── extractors/
│       │   └── router.py
│       ├── llm/
│       │   ├── client.py
│       │   ├── fake.py
│       │   └── groq.py
│       ├── synthesis/
│       │   ├── context.py
│       │   ├── pipeline.py
│       │   └── steps/
│       ├── storage/
│       │   ├── markdown.py
│       │   └── vector.py
│       ├── application/
│       │   └── create_note.py
│       ├── api/
│       │   ├── app.py
│       │   └── routes/
│       └── observability/
│           └── tracing.py
├── tests/
│   ├── unit/
│   └── integration/
├── ui/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
├── config.py
├── README.md
└── uv.lock
```

Imports should use the installed package name:

```python
from notes_ai.application.create_note import CreateNoteService
from notes_ai.ingestion.router import SourceRouter
from notes_ai.llm.groq import GroqLLMClient
from notes_ai.storage.markdown import MarkdownFileStore
from notes_ai.synthesis.pipeline import SequentialSynthesisPipeline
```

Do not import modules through `src`, because `src` is a repository layout directory, not the application package.

---

## Definition of done

The project is ready for the final demo when:

1. at least three source types work end-to-end;
2. notes are saved as structured Markdown;
3. the synthesis pipeline has explicit, observable steps;
4. React can create, list, and display notes;
5. related notes are retrieved through ChromaDB;
6. Docker Compose starts the API, web application, and Phoenix;
7. one complete note-generation trace is visible in Phoenix;
8. offline tests pass without API credentials;
9. a clean-checkout setup has been verified;
10. known limitations and stretch goals are clearly separated from completed functionality.

## Contribution workflow

- Create one branch per task: `feature/...`, `fix/...`, `refactor/...`, or `docs/...`
- Keep commits small and focused
- Add or update tests with behavior changes
- Run tests before opening a pull request
- Do not commit `.env`, generated content, model files, logs, caches, or local databases
- Update README or architecture documentation when commands or module boundaries change

Suggested checks:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Ruff should be added to the development dependencies before these checks become mandatory in CI.

## License

This project is intended for learning, experimentation, and demonstrations. Add an explicit license file before public reuse or distribution. Keep all credentials in environment variables and never commit real API keys.


