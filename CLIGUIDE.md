# Notes AI — CLI User Guide & Documentation

This guide provides full documentation on using the `notes-ai` Command-Line Interface (CLI).

---

## Quick Start & Global Help

```bash
uv run python -m notes_ai.cli --help
```
*or via the installed package entry point:*
```bash
uv run notes-ai --help
```

### Global Help Output
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

---

## Command Reference

### Synopsis
```bash
uv run python -m notes_ai.cli <SOURCES...> [OPTIONS]
```

### Positional Arguments
| Argument | Type | Nargs | Description |
| :--- | :--- | :---: | :--- |
| `sources` | `str` | `+` (1 or more) | One or more YouTube URLs, Web URLs, or local file paths (`.pdf`, `.png`, `.mp3`, etc.) |

### Options & Flags
| Option / Flag | Short | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| `--output-dir` | `-o` | `str` | `output` | Directory where generated `.md` note files will be saved |
| `--name` | `-n` | `str` | `None` | Custom note filename (without extension). Only valid for single-source runs |
| `--verbose` | `-v` | flag | `False` | Enables `DEBUG` level log output in terminal |
| `--help` | `-h` | flag | — | Displays the global help screen and exits |

---

## Supported Source Formats

| Format | Category | File Extension / Pattern | Extractor Adapter |
| :--- | :--- | :--- | :--- |
| **YouTube** | Video URL | `youtube.com/watch?v=...`, `youtu.be/...` | `YouTubeExtractor` |
| **Web Pages** | Article URL | `http://...`, `https://...` | `WebExtractor` |
| **PDF** | Document | `.pdf` | `PDFExtractor` |
| **Image (OCR)** | Image | `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp` | `ImageExtractor` |
| **Audio** | Audio | `.mp3`, `.wav`, `.m4a`, `.opus`, `.flac`, `.aac` | `AudioExtractor` |

---

## Examples

### 1. Single Source Processing

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

### 2. Batch Processing (Multiple Sources)

You can pass multiple files or URLs at once in a single command:

```bash
uv run python -m notes_ai.cli "https://youtu.be/Z6z_feacXW8" "report.pdf" "lecture.mp3" -o batch_output
```

*Processes each source sequentially and creates:*
* `./batch_output/note_1.md`
* `./batch_output/report.md`
* `./batch_output/lecture.md`

---

## Environment Setup

The CLI uses Groq LLMs to synthesize extracted content into study notes. Make sure your `GROQ_API_KEY` is defined in your `.env` file or environment variables:

```bash
# In your .env file
GROQ_API_KEY="your_actual_groq_api_key"

# Or exported directly in shell
export GROQ_API_KEY="your_actual_groq_api_key"
```