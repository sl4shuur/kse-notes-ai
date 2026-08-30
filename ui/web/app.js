const view = document.querySelector("#view");
const toast = document.querySelector("#toast");

const sourceLabels = {
  youtube: "YouTube",
  web: "Web article",
  pdf: "PDF",
  image: "Image",
  audio: "Audio",
};

const sourceIcons = {
  youtube: "▶",
  web: "🌐",
  pdf: "▤",
  image: "▧",
  audio: "◉",
};

let disposeView = () => {};
let toastTimer;

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message, type = "success") {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.className = `toast show ${type === "error" ? "error" : ""}`;
  toastTimer = setTimeout(() => {
    toast.className = "toast";
  }, 3200);
}

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: options.body instanceof FormData
      ? options.headers
      : { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || `Request failed with status ${response.status}`);
  }
  return data;
}

function navigate(path) {
  const next = `#/${path.replace(/^\//, "")}`;
  if (location.hash === next) renderRoute();
  else location.hash = next;
}

function setActiveNav(route) {
  const active = route === "new" || route === "processing"
    ? "new"
    : route === "notes" ? "library" : route;
  document.querySelectorAll("[data-nav]").forEach((link) => {
    link.classList.toggle("active", link.dataset.nav === active);
  });
}

function pageError(error, retryRoute) {
  view.innerHTML = `
    <div class="error-state">
      <h3>Something went wrong</h3>
      <p>${escapeHtml(error.message)}</p>
      <button class="btn" id="retry-request">Try again</button>
    </div>`;
  document.querySelector("#retry-request")?.addEventListener("click", () => navigate(retryRoute));
}

function flowSteps(activeStep) {
  const labels = ["Add source", "Processing", "Review", "Saved"];
  return `<ul class="steps">${labels.map((label, index) => {
    const step = index + 1;
    const state = step < activeStep ? "done" : step === activeStep ? "active" : "";
    const marker = step < activeStep ? "✓" : step;
    const connector = index < labels.length - 1 ? '<li class="connector"></li>' : "";
    return `<li class="${state}"><span class="dot">${marker}</span>${label}</li>${connector}`;
  }).join("")}</ul>`;
}

function formatDate(value) {
  if (!value) return "Recently";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "Recently";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function noteId(note) {
  return note.id || note.title;
}

function noteCard(note) {
  const type = note.source?.input_type || "web";
  const tags = (note.tags || []).slice(0, 2);
  const snippet = String(note.content || "No preview available")
    .replace(/[#*_`$\\{}]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return `
    <a class="note-card" href="#/notes/${encodeURIComponent(noteId(note))}">
      <div class="source-icon">${sourceIcons[type] || "•"}</div>
      <div class="title">${escapeHtml(note.title || "Untitled note")}</div>
      <div class="snippet">${escapeHtml(snippet)}</div>
      ${tags.length ? `<div class="tag-row">${tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
      <div class="card-footer">
        <span class="source-type">${escapeHtml(sourceLabels[type] || type)}</span>
        <span>${formatDate(note.date_created)}</span>
      </div>
    </a>`;
}

function inlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/\$\\textcolor\{[^}]+\}\{\\text(?:bf)?\{([^{}]+)\}\}\$/g, "<mark>$1</mark>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function isHorizontalRule(line) {
  return /^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line);
}

function tableCells(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isTableStart(lines, index) {
  if (!lines[index]?.includes("|") || !lines[index + 1]?.includes("|")) return false;
  const dividers = tableCells(lines[index + 1]);
  return dividers.length > 0 && dividers.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function parseTable(lines, start) {
  const headers = tableCells(lines[start]);
  const rows = [];
  let index = start + 2;
  while (index < lines.length && lines[index].trim() && lines[index].includes("|")) {
    rows.push(tableCells(lines[index]));
    index += 1;
  }

  return {
    html: `<div class="table-wrap"><table><thead><tr>${headers.map((cell) => `<th>${inlineMarkdown(cell)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${headers.map((_, cellIndex) => `<td>${inlineMarkdown(row[cellIndex] || "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`,
    nextIndex: index,
  };
}

function parseOrderedList(lines, start) {
  let index = start;
  let html = "<ol>";

  while (index < lines.length) {
    const item = lines[index].match(/^\s{0,3}\d+[.)]\s+(.+)$/);
    if (!item) break;

    html += `<li><div>${inlineMarkdown(item[1].trimEnd())}</div>`;
    index += 1;
    const nestedItems = [];

    while (index < lines.length) {
      if (!lines[index].trim()) {
        let next = index + 1;
        while (next < lines.length && !lines[next].trim()) next += 1;
        if (/^\s{0,3}\d+[.)]\s+/.test(lines[next] || "")) {
          index = next;
          break;
        }
        if (/^\s{2,}[-+*]\s+/.test(lines[next] || "")) {
          index = next;
          continue;
        }
        index = next;
        break;
      }

      const nested = lines[index].match(/^\s{2,}[-+*]\s+(.+)$/);
      if (!nested) break;
      nestedItems.push(nested[1].trimEnd());
      index += 1;
    }

    if (nestedItems.length) {
      html += `<ul>${nestedItems.map((nested) => `<li>${inlineMarkdown(nested)}</li>`).join("")}</ul>`;
    }
    html += "</li>";
  }

  return { html: `${html}</ol>`, nextIndex: index };
}

function parseUnorderedList(lines, start) {
  let index = start;
  const items = [];
  while (index < lines.length) {
    const item = lines[index].match(/^\s{0,3}[-+*]\s+(.+)$/);
    if (!item) break;
    items.push(item[1].trimEnd());
    index += 1;
  }
  return {
    html: `<ul>${items.map((item) => `<li>${inlineMarkdown(item)}</li>`).join("")}</ul>`,
    nextIndex: index,
  };
}

function startsMarkdownBlock(lines, index) {
  const line = lines[index] || "";
  return !line.trim()
    || /^\s*```/.test(line)
    || /^\s{0,3}#{1,6}\s+/.test(line)
    || isHorizontalRule(line)
    || /^\s{0,3}\d+[.)]\s+/.test(line)
    || /^\s{0,3}[-+*]\s+/.test(line)
    || /^\s{0,3}>\s?/.test(line)
    || isTableStart(lines, index);
}

function renderMarkdown(markdown = "") {
  const lines = String(markdown).replace(/\r\n?/g, "\n").split("\n");
  const output = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = line.match(/^\s*```([\w-]*)\s*$/);
    if (fence) {
      const code = [];
      index += 1;
      while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) {
        code.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      const language = fence[1] ? ` class="language-${escapeHtml(fence[1])}"` : "";
      output.push(`<pre><code${language}>${escapeHtml(code.join("\n"))}</code></pre>`);
      continue;
    }

    if (isHorizontalRule(line)) {
      output.push("<hr>");
      index += 1;
      continue;
    }

    const heading = line.match(/^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      const level = heading[1].length;
      output.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
      index += 1;
      continue;
    }

    if (isTableStart(lines, index)) {
      const table = parseTable(lines, index);
      output.push(table.html);
      index = table.nextIndex;
      continue;
    }

    if (/^\s{0,3}\d+[.)]\s+/.test(line)) {
      const list = parseOrderedList(lines, index);
      output.push(list.html);
      index = list.nextIndex;
      continue;
    }

    if (/^\s{0,3}[-+*]\s+/.test(line)) {
      const list = parseUnorderedList(lines, index);
      output.push(list.html);
      index = list.nextIndex;
      continue;
    }

    if (/^\s{0,3}>\s?/.test(line)) {
      const quote = [];
      while (index < lines.length && /^\s{0,3}>\s?/.test(lines[index])) {
        quote.push(lines[index].replace(/^\s{0,3}>\s?/, ""));
        index += 1;
      }
      output.push(`<blockquote>${quote.map(inlineMarkdown).join("<br>")}</blockquote>`);
      continue;
    }

    const paragraph = [];
    while (index < lines.length && !startsMarkdownBlock(lines, index)) {
      const hardBreak = /\s{2,}$/.test(lines[index]);
      paragraph.push(`${inlineMarkdown(lines[index].trimEnd())}${hardBreak ? "<br>" : ""}`);
      index += 1;
    }
    output.push(`<p>${paragraph.join(" ")}</p>`);
  }

  return output.join("");
}

async function renderDashboard() {
  view.innerHTML = '<div class="loading-state">Loading your workspace…</div>';
  try {
    const [stats, notes] = await Promise.all([api("/stats"), api("/notes")]);
    const recent = [...notes]
      .sort((a, b) => new Date(b.date_created || 0) - new Date(a.date_created || 0))
      .slice(0, 3);
    view.innerHTML = `
      <div class="page-header">
        <p class="eyebrow">Dashboard</p>
        <h1>What are we turning into notes today?</h1>
        <p>Drop in a video, article, PDF, image, or audio file. Notes AI extracts the content and writes a structured study note for you.</p>
      </div>
      <div class="btn-row" style="margin-top:0">
        <a class="btn btn-primary" href="#/new">＋ New note</a>
        <a class="btn" href="#/library">Browse library</a>
      </div>
      <div class="grid grid-3" style="margin-top:28px">
        <div class="stat"><div class="value">${Number(stats.notes_total || 0)}</div><div class="label">Notes in your knowledge base</div></div>
        <div class="stat"><div class="value">${Number(stats.source_types_supported || 5)}</div><div class="label">Source types supported</div></div>
        <div class="stat"><div class="value">${Number(stats.sources_count || 0)}</div><div class="label">Sources processed</div></div>
      </div>
      <div class="section-title"><h3>How a note gets made</h3></div>
      <div class="flow">
        <a class="flow-step" href="#/new"><div class="num">STEP 1</div><h4>Add a source</h4><p>Paste a link or upload a document, image, or audio file.</p></a>
        <div class="flow-step"><div class="num">STEP 2</div><h4>Pipeline runs</h4><p>Content is extracted and turned into a structured note.</p></div>
        <div class="flow-step"><div class="num">STEP 3</div><h4>Review the note</h4><p>Read the generated Markdown and check the important ideas.</p></div>
        <a class="flow-step" href="#/library"><div class="num">STEP 4</div><h4>Save &amp; browse</h4><p>Keep it in your searchable personal knowledge base.</p></a>
      </div>
      <div class="section-title"><h3>Recent notes</h3><a href="#/library">View all →</a></div>
      ${recent.length
        ? `<div class="grid grid-3">${recent.map(noteCard).join("")}</div>`
        : '<div class="empty-state"><h3>No notes yet</h3><p>Your first generated note will appear here.</p><a class="btn btn-primary" href="#/new">Create a note</a></div>'}`;
  } catch (error) {
    pageError(error, "dashboard");
  }
}

function renderNewNote() {
  const types = Object.keys(sourceLabels);
  view.innerHTML = `
    <div class="page-header">
      <p class="eyebrow">New note</p>
      <h1>Add a source</h1>
      <p>Choose where the content comes from. Notes AI extracts it before writing the note.</p>
    </div>
    ${flowSteps(1)}
    <form id="source-form">
      <div class="card">
        <div class="tabs" role="tablist">
          ${types.map((type, index) => `<button class="tab ${index === 0 ? "active" : ""}" type="button" data-source-tab="${type}">${sourceIcons[type]} ${sourceLabels[type]}</button>`).join("")}
        </div>
        <div id="source-field"></div>
        <div class="field" style="margin-top:18px">
          <label for="note-focus">Note focus <span class="muted">(optional)</span></label>
          <input id="note-focus" type="text" placeholder="e.g. focus on the math behind attention" />
        </div>
        <p class="form-error" id="source-error" hidden></p>
      </div>
      <div class="btn-row">
        <button class="btn btn-primary" id="generate-button" type="submit">Generate note →</button>
        <a class="btn" href="#/dashboard">Cancel</a>
      </div>
    </form>`;

  let selectedType = "youtube";
  let selectedFile = null;
  const field = document.querySelector("#source-field");

  const renderField = () => {
    selectedFile = null;
    if (selectedType === "youtube" || selectedType === "web") {
      const label = selectedType === "youtube" ? "YouTube URL" : "Article URL";
      field.innerHTML = `
        <div class="field">
          <label for="source-location">${label}</label>
          <input id="source-location" type="url" required placeholder="${selectedType === "youtube" ? "https://www.youtube.com/watch?v=…" : "https://example.com/article"}" />
          <p class="hint">The content is downloaded and extracted automatically.</p>
        </div>`;
      return;
    }
    field.innerHTML = `
      <div class="field">
        <label>Upload ${sourceLabels[selectedType].toLowerCase()}</label>
        <label class="dropzone" id="dropzone">
          <input id="source-file" type="file" required accept="${selectedType === "pdf" ? ".pdf,application/pdf" : selectedType === "image" ? "image/*" : "audio/*"}" />
          <div class="icon">${sourceIcons[selectedType]}</div>
          <p><strong id="file-label">Choose a file</strong></p>
          <p class="hint">The file is uploaded securely before generation starts.</p>
        </label>
      </div>`;
    document.querySelector("#source-file").addEventListener("change", (event) => {
      selectedFile = event.target.files[0] || null;
      document.querySelector("#file-label").textContent = selectedFile?.name || "Choose a file";
      document.querySelector("#dropzone").classList.toggle("has-file", Boolean(selectedFile));
    });
  };

  renderField();
  document.querySelectorAll("[data-source-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      selectedType = tab.dataset.sourceTab;
      document.querySelectorAll("[data-source-tab]").forEach((item) => item.classList.toggle("active", item === tab));
      renderField();
    });
  });

  document.querySelector("#source-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = document.querySelector("#generate-button");
    const errorElement = document.querySelector("#source-error");
    errorElement.hidden = true;
    button.disabled = true;
    button.textContent = "Starting pipeline…";
    try {
      let locationValue;
      if (selectedType === "youtube" || selectedType === "web") {
        locationValue = document.querySelector("#source-location").value.trim();
        if (!locationValue) throw new Error("Enter a source URL.");
      } else {
        if (!selectedFile) throw new Error("Choose a file first.");
        const upload = new FormData();
        upload.append("file", selectedFile);
        const uploaded = await api("/uploads", { method: "POST", body: upload });
        locationValue = uploaded.file_id;
      }

      const result = await api("/sources", {
        method: "POST",
        body: JSON.stringify({
          input_type: selectedType,
          location: locationValue,
          note_focus: document.querySelector("#note-focus").value.trim() || null,
        }),
      });
      sessionStorage.setItem("notesAiCurrentJob", result.job_id);
      navigate(`processing/${encodeURIComponent(result.job_id)}`);
    } catch (error) {
      errorElement.textContent = error.message;
      errorElement.hidden = false;
      button.disabled = false;
      button.textContent = "Generate note →";
    }
  });
}

function stageMarkup() {
  const stages = [
    ["Extract content", "Read the source text, transcript, or visual content."],
    ["Generate study note", "Organize the source into clear Markdown sections."],
    ["Add highlights", "Emphasize key concepts, examples, and takeaways."],
    ["Save note", "Store the note and its metadata in the library."],
  ];
  return stages.map(([title, description], index) => `
    <div class="stage is-pending" data-stage="${index}">
      <div class="stage-icon">${index + 1}</div>
      <div class="stage-body"><div class="stage-title">${title}</div><div class="stage-desc">${description}</div><div class="stage-status">Waiting…</div></div>
    </div>`).join("");
}

function updatePipeline(job, logs) {
  const status = job.status || "pending";
  const progress = status === "pending" ? 8 : status === "running" ? 58 : 100;
  document.querySelector("#job-status").textContent = status;
  document.querySelector("#progress-percent").textContent = `${progress}%`;
  document.querySelector("#progress-fill").style.width = `${progress}%`;

  const stages = [...document.querySelectorAll("[data-stage]")];
  const activeIndex = status === "pending" ? 0 : status === "running" ? 1 : stages.length;
  stages.forEach((stage, index) => {
    stage.className = "stage";
    const icon = stage.querySelector(".stage-icon");
    const label = stage.querySelector(".stage-status");
    if (status === "failed" && index === Math.min(activeIndex, stages.length - 1)) {
      stage.classList.add("is-failed");
      icon.textContent = "!";
      label.textContent = "Failed";
    } else if (status === "cancelled" && index === Math.min(activeIndex, stages.length - 1)) {
      stage.classList.add("is-failed");
      icon.textContent = "×";
      label.textContent = "Cancelled";
    } else if (status === "done" || index < activeIndex) {
      stage.classList.add("is-done");
      icon.textContent = "✓";
      label.textContent = "Done";
    } else if (index === activeIndex) {
      stage.classList.add("is-active");
      icon.innerHTML = '<span class="spinner"></span>';
      label.textContent = "In progress…";
    } else {
      stage.classList.add("is-pending");
      icon.textContent = index + 1;
      label.textContent = "Waiting…";
    }
  });

  const consoleElement = document.querySelector("#pipeline-log");
  consoleElement.innerHTML = (logs || []).map((line) => `<div>${escapeHtml(line)}</div>`).join("");
  const result = document.querySelector("#job-result");
  if (status === "done" && job.note_id) {
    result.innerHTML = `<a class="btn btn-primary" href="#/notes/${encodeURIComponent(job.note_id)}">View generated note →</a>`;
  } else if (status === "done") {
    result.innerHTML = '<p class="form-error">The job finished without creating a note. Check the API logs.</p>';
  } else if (status === "failed") {
    result.innerHTML = '<p class="form-error">Generation failed. Check the pipeline log and try another source.</p>';
  } else if (status === "cancelled") {
    result.innerHTML = '<p class="muted">This job was cancelled.</p>';
  }
}

function renderProcessing(jobId) {
  view.innerHTML = `
    <div class="page-header">
      <p class="eyebrow">New note</p>
      <h1>Generating your note</h1>
      <p>Job <strong>${escapeHtml(jobId)}</strong> is <span id="job-status">starting</span>.</p>
    </div>
    ${flowSteps(2)}
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:baseline"><strong>Pipeline progress</strong><span id="progress-percent" class="muted">0%</span></div>
      <div class="progress-track"><div class="progress-fill" id="progress-fill"></div></div>
      <div class="stage-list" style="margin-top:20px">${stageMarkup()}</div>
    </div>
    <div class="card">
      <strong>Pipeline log</strong>
      <div class="console" id="pipeline-log" style="margin-top:10px"></div>
    </div>
    <div class="btn-row">
      <div id="job-result"></div>
      <button class="btn btn-danger" id="cancel-job" type="button">Cancel job</button>
      <a class="btn" href="#/new">Start another</a>
    </div>`;

  let stopped = false;
  let timer;
  const poll = async () => {
    try {
      const [job, logs] = await Promise.all([
        api(`/jobs/${encodeURIComponent(jobId)}`),
        api(`/jobs/${encodeURIComponent(jobId)}/log`),
      ]);
      updatePipeline(job, logs);
      if (["done", "failed", "cancelled"].includes(job.status)) {
        clearInterval(timer);
        document.querySelector("#cancel-job").hidden = true;
      }
    } catch (error) {
      clearInterval(timer);
      if (!stopped) pageError(error, `processing/${encodeURIComponent(jobId)}`);
    }
  };

  document.querySelector("#cancel-job").addEventListener("click", async () => {
    try {
      await api(`/jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" });
      showToast("Job cancelled");
      await poll();
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  timer = setInterval(poll, 2000);
  poll();
  disposeView = () => {
    stopped = true;
    clearInterval(timer);
  };
}

async function renderNote(id) {
  view.innerHTML = '<div class="loading-state">Loading note…</div>';
  try {
    const note = await api(`/notes/${encodeURIComponent(id)}`);
    const type = note.source?.input_type || "web";
    const tags = note.tags || [];
    view.innerHTML = `
      <div class="page-header">
        <p class="eyebrow">Review note</p>
        <h1>${escapeHtml(note.title || "Untitled note")}</h1>
        <div class="tag-row" style="margin-top:10px">
          <span class="tag">${sourceIcons[type] || "•"} ${escapeHtml(sourceLabels[type] || type)}</span>
          <span class="tag">Generated ${formatDate(note.date_created)}</span>
          <span class="tag tag-accent">${escapeHtml(note.status || "draft")}</span>
        </div>
      </div>
      ${flowSteps(note.status === "saved" ? 4 : 3)}
      <div class="note-layout">
        <article class="note-doc"><div class="card">${renderMarkdown(note.content)}</div></article>
        <aside>
          <div class="sidebar-block"><h3>Tags</h3><div class="tag-row">${tags.length ? tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("") : '<span class="muted">No tags yet</span>'}</div></div>
          <div class="sidebar-block"><h3>Source</h3><p class="source-location">${escapeHtml(note.source?.location || "Unknown source")}</p></div>
          <div class="sidebar-block"><h3>Model</h3><p class="source-location">${escapeHtml(note.metadata?.model || "Unknown")}</p></div>
        </aside>
      </div>
      <div class="btn-row">
        <button class="btn btn-primary" id="save-note" type="button">${note.status === "saved" ? "Saved ✓" : "Save to library →"}</button>
        <button class="btn btn-danger" id="discard-note" type="button">Discard</button>
        <a class="btn" href="#/library">Back to library</a>
      </div>`;

    const saveButton = document.querySelector("#save-note");
    saveButton.disabled = note.status === "saved";
    saveButton.addEventListener("click", async () => {
      saveButton.disabled = true;
      saveButton.textContent = "Saving…";
      try {
        await api(`/notes/${encodeURIComponent(id)}?status=saved`, { method: "PATCH" });
        showToast("Note saved to your library");
        navigate("library");
      } catch (error) {
        saveButton.disabled = false;
        saveButton.textContent = "Save to library →";
        showToast(error.message, "error");
      }
    });

    document.querySelector("#discard-note").addEventListener("click", async () => {
      if (!window.confirm("Discard this note permanently?")) return;
      try {
        await api(`/notes/${encodeURIComponent(id)}`, { method: "DELETE" });
        showToast("Note discarded");
        navigate("library");
      } catch (error) {
        showToast(error.message, "error");
      }
    });
  } catch (error) {
    pageError(error, `notes/${encodeURIComponent(id)}`);
  }
}

async function renderLibrary() {
  view.innerHTML = '<div class="loading-state">Loading your library…</div>';
  try {
    const [notes, tags] = await Promise.all([api("/notes"), api("/tags")]);
    const types = ["all", ...Object.keys(sourceLabels)];
    view.innerHTML = `
      <div class="page-header-row">
        <div class="page-header">
          <p class="eyebrow">Knowledge base</p>
          <h1>Library</h1>
          <p>Every generated note lives here, searchable by content, source, and tag.</p>
        </div>
        <div class="page-actions"><a class="btn btn-primary" href="#/new">＋ New note</a></div>
      </div>
      <div class="toolbar">
        <div class="search-input"><input id="library-search" type="text" placeholder="Search notes by topic, keyword, or tag…" /></div>
      </div>
      <div class="filter-row" id="source-filters">
        ${types.map((type) => {
          const count = type === "all" ? notes.length : notes.filter((note) => note.source?.input_type === type).length;
          return `<button class="filter-chip ${type === "all" ? "active" : ""}" type="button" data-filter="${type}">${type === "all" ? "All" : `${sourceIcons[type]} ${sourceLabels[type]}`} (${count})</button>`;
        }).join("")}
      </div>
      ${Object.keys(tags).length ? `<div class="tag-row" style="margin-bottom:20px">${Object.entries(tags).map(([tag, count]) => `<button class="tag" type="button" data-tag-filter="${escapeHtml(tag)}">${escapeHtml(tag)} · ${Number(count)}</button>`).join("")}</div>` : ""}
      <div id="library-results"></div>`;

    let activeType = "all";
    let activeTag = "";
    const results = document.querySelector("#library-results");
    const search = document.querySelector("#library-search");
    const draw = () => {
      const query = search.value.trim().toLowerCase();
      const filtered = notes.filter((note) => {
        const matchesType = activeType === "all" || note.source?.input_type === activeType;
        const matchesTag = !activeTag || (note.tags || []).includes(activeTag);
        const haystack = `${note.title || ""} ${note.content || ""} ${(note.tags || []).join(" ")}`.toLowerCase();
        return matchesType && matchesTag && (!query || haystack.includes(query));
      });
      results.innerHTML = filtered.length
        ? `<div class="grid grid-3">${filtered.map(noteCard).join("")}</div>`
        : '<div class="empty-state"><h3>No matching notes</h3><p>Try another search or source filter.</p></div>';
    };

    search.addEventListener("input", draw);
    document.querySelectorAll("[data-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        activeType = button.dataset.filter;
        document.querySelectorAll("[data-filter]").forEach((item) => item.classList.toggle("active", item === button));
        draw();
      });
    });
    document.querySelectorAll("[data-tag-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        activeTag = activeTag === button.dataset.tagFilter ? "" : button.dataset.tagFilter;
        document.querySelectorAll("[data-tag-filter]").forEach((item) => item.classList.toggle("tag-accent", activeTag === item.dataset.tagFilter));
        draw();
      });
    });
    draw();
  } catch (error) {
    pageError(error, "library");
  }
}

async function renderRoute() {
  disposeView();
  disposeView = () => {};
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const route = parts[0] || "dashboard";
  setActiveNav(route);
  view.focus({ preventScroll: true });

  if (route === "dashboard") return renderDashboard();
  if (route === "new") return renderNewNote();
  if (route === "processing" && parts[1]) return renderProcessing(decodeURIComponent(parts[1]));
  if (route === "notes" && parts[1]) return renderNote(decodeURIComponent(parts.slice(1).join("/")));
  if (route === "library") return renderLibrary();
  navigate("dashboard");
}

window.addEventListener("hashchange", renderRoute);
renderRoute();
