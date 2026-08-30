# REST API — required for the UI mockup

Every screen in `ui/mockup/` is backed by one of four resources: **sources**
(submitting new content), **jobs** (the pipeline run that turns a source into
a note), **notes** (the generated Markdown, once saved), and **tags**. This
document lists the CRUD surface needed to drive each screen. Paths assume a
`/api` prefix served by the FastAPI app referenced in the README's target
stack; request/response bodies follow the existing domain models in
`notes_ai.models` (`Source`, `SourceType`, `Note`, `NoteMetadata`) with the
additions noted inline (`id`, `tags`, `status` — not yet on the domain model,
needed at the DTO/storage layer only, not the core pipeline).

## Screen → resource map

| Screen | Action | Resource(s) |
| --- | --- | --- |
| `index.html` | dashboard counts, recent notes | `GET /stats`, `GET /notes` |
| `new-note.html` | submit a source, upload a file | `POST /uploads`, `POST /sources` |
| `processing.html` | poll pipeline progress, view log, cancel | `GET /jobs/{id}`, `GET /jobs/{id}/log`, `DELETE /jobs/{id}` |
| `note.html` | read note, edit, related notes, save, discard | `GET /notes/{id}`, `PATCH /notes/{id}`, `GET /notes/{id}/related`, `DELETE /notes/{id}` |
| `library.html` | list/search/filter, tag chips | `GET /notes`, `GET /tags` |

---

## 1. Sources — `/api/sources`

Created once per "New note" submission (`new-note.html` → "Generate note").
Creating a source starts a `Job`; sources themselves are immutable once
extracted, so only **Create** and **Read** apply.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/sources` | Register a new source (YouTube/web URL, or an uploaded file reference) and enqueue a pipeline job. |
| `GET` | `/sources` | List previously submitted sources (history/debugging). |
| `GET` | `/sources/{id}` | Read one source's detected type and extracted metadata. |

`POST /sources` request:

```json
{
  "input_type": "youtube",
  "location": "https://www.youtube.com/watch?v=aircAruvnKk",
  "note_focus": "focus on the math behind attention"
}
```

For `pdf` / `image` / `audio`, `location` is the `file_id` returned by
`POST /uploads` instead of a URL.

Response — `202 Accepted`, points the client at the job to poll:

```json
{ "job_id": "job_8f2a", "source": { "input_type": "youtube", "location": "...", "title": "..." } }
```

## 2. Uploads — `/api/uploads`

Backs the drag-and-drop zones on the PDF/Image/Audio tabs. Files are
write-once; no update, and delete is only needed for cleanup of abandoned
uploads.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/uploads` | Multipart upload of a PDF, image, or audio file. Returns a `file_id` to pass into `POST /sources`. |
| `DELETE` | `/uploads/{file_id}` | Discard an uploaded file that was never turned into a source. |

## 3. Jobs — `/api/jobs`

Backs `processing.html`: the stage list, progress bar, and console log.
Jobs are system-owned state machines — clients read and can cancel, but
never edit stage results directly.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/jobs` | List jobs (e.g. an "in progress" indicator on the dashboard). |
| `GET` | `/jobs/{id}` | Current status: stage list, per-stage state (`pending/active/done/failed`), overall `progress_percent`, and `note_id` once finished. |
| `GET` | `/jobs/{id}/log` | Pipeline console log lines (`processing.html`'s log panel); supports `?since=` for incremental polling, or is upgraded to SSE/WebSocket later. |
| `DELETE` | `/jobs/{id}` | Cancel a running job. |

`GET /jobs/{id}` response:

```json
{
  "id": "job_8f2a",
  "status": "running",
  "progress_percent": 33,
  "stages": [
    { "name": "extract_content", "status": "done" },
    { "name": "structure_outline", "status": "active" },
    { "name": "generate_draft", "status": "pending" },
    { "name": "add_highlights", "status": "pending" },
    { "name": "generate_visuals", "status": "pending" },
    { "name": "finalize", "status": "pending" }
  ],
  "note_id": null
}
```

There is intentionally no `PATCH /jobs/{id}` — the pipeline (not the client)
owns stage transitions; the only client-initiated write is cancellation.

## 4. Notes — `/api/notes`

Backs `note.html` and `library.html`. Full CRUD: a job's output is a draft
note (`POST` happens server-side on job completion, not from the client), the
user reads it, edits it, saves it (`status: draft → saved`), or discards it.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/notes` | List/search notes. Query params: `q` (full-text search box), `source_type`, `tag`, `status`, `page`, `page_size`. Backs the library grid and filter chips. |
| `GET` | `/notes/{id}` | Read one note's full content for `note.html`. |
| `POST` | `/notes` | Create a note directly (manual/import path); the primary flow creates notes via `POST /sources` → job completion instead. |
| `PATCH` | `/notes/{id}` | Partial update — edit title/content/tags, or flip `status` from `draft` to `saved` ("Save to library" button). |
| `PUT` | `/notes/{id}` | Full replace of a note's editable fields (used by a future full note editor). |
| `DELETE` | `/notes/{id}` | Delete a note ("Discard" button on `note.html`, or a delete action in the library). |
| `GET` | `/notes/{id}/related` | Related notes sidebar — nearest neighbors by embedding similarity. |

`Note` shape (extends `notes_ai.models.Note` with API-only fields):

```json
{
  "id": "note_3c91",
  "title": "Transformers, Explained Simply",
  "content": "## Overview\n...",
  "status": "draft",
  "tags": ["machine-learning", "nlp", "attention"],
  "source": {
    "input_type": "youtube",
    "location": "https://www.youtube.com/watch?v=aircAruvnKk",
    "title": "Transformers, Explained Simply",
    "metadata": { "source_type": "youtube", "duration_seconds": 1084 }
  },
  "date_created": "2026-08-15T09:41:00Z",
  "metadata": { "model": "groq/llama-3.3-70b", "generated": true, "colored": true, "cleaned": true }
}
```

`PATCH /notes/{id}` request (save to library):

```json
{ "status": "saved", "tags": ["machine-learning", "nlp", "attention"] }
```

## 5. Tags — `/api/tags`

Backs the filter chips in `library.html` and the tag list in `note.html`'s
sidebar. Tags are simple, independently manageable entities.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/tags` | List all tags with note counts, for the filter-chip row. |
| `POST` | `/tags` | Create a tag (used when a user types a new tag while editing a note). |
| `PATCH` | `/tags/{id}` | Rename a tag. |
| `DELETE` | `/tags/{id}` | Delete a tag (removes it from all notes). |

## 6. Stats — `/api/stats`

Read-only aggregate for the dashboard tiles (`index.html`). No create/update/
delete — it's a derived view over `notes` and `sources`.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/stats` | `{ "notes_total": 128, "source_types_supported": 5, "related_links_found": 36 }` |

---

## Summary — CRUD coverage by resource

| Resource | Create | Read | Update | Delete |
| --- | --- | --- | --- | --- |
| Sources | `POST /sources` | `GET /sources`, `GET /sources/{id}` | — (immutable) | — |
| Uploads | `POST /uploads` | — | — | `DELETE /uploads/{file_id}` |
| Jobs | (system-created on `POST /sources`) | `GET /jobs`, `GET /jobs/{id}`, `GET /jobs/{id}/log` | — (system-owned) | `DELETE /jobs/{id}` (cancel) |
| Notes | `POST /notes` (system-created on job completion) | `GET /notes`, `GET /notes/{id}`, `GET /notes/{id}/related` | `PATCH /notes/{id}`, `PUT /notes/{id}` | `DELETE /notes/{id}` |
| Tags | `POST /tags` | `GET /tags` | `PATCH /tags/{id}` | `DELETE /tags/{id}` |
| Stats | — | `GET /stats` | — | — |
