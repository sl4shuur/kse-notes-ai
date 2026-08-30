// Notes AI — mockup interactivity (no build step, static demo only)

// Source-type tabs on the "New note" page
document.querySelectorAll(".tabs").forEach((tabGroup) => {
  const tabs = tabGroup.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");

      const target = tab.getAttribute("data-tab");
      const panels = document.querySelectorAll(".tab-panel");
      panels.forEach((p) => {
        p.classList.toggle("active", p.getAttribute("data-panel") === target);
      });
    });
  });
});

// Filter chips on the "Library" page (purely visual — filters nothing)
document.querySelectorAll(".filter-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    chip.parentElement
      .querySelectorAll(".filter-chip")
      .forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
  });
});

// Simulated pipeline progress on the "Processing" page
const stageList = document.querySelector("[data-pipeline]");
if (stageList) {
  const stages = Array.from(stageList.querySelectorAll(".stage"));
  const fill = document.querySelector(".progress-fill");
  const pct = document.querySelector("[data-progress-pct]");
  const viewNoteBtn = document.querySelector("[data-view-note-btn]");
  let current = stages.findIndex((s) => s.classList.contains("is-active"));
  if (current === -1) current = 0;

  const setProgress = (value) => {
    if (fill) fill.style.width = value + "%";
    if (pct) pct.textContent = value + "%";
  };

  const step = () => {
    if (current >= stages.length) return;
    stages[current].classList.remove("is-active");
    stages[current].classList.add("is-done");
    const statusEl = stages[current].querySelector(".stage-status");
    if (statusEl) statusEl.textContent = "Done";

    current += 1;
    setProgress(Math.round((current / stages.length) * 100));

    if (current < stages.length) {
      stages[current].classList.add("is-active");
      const nextStatus = stages[current].querySelector(".stage-status");
      if (nextStatus) nextStatus.textContent = "In progress…";
      setTimeout(step, 1400);
    } else if (viewNoteBtn) {
      viewNoteBtn.removeAttribute("disabled");
      viewNoteBtn.textContent = "View generated note →";
    }
  };

  setProgress(Math.round((current / stages.length) * 100));
  setTimeout(step, 1400);
}
