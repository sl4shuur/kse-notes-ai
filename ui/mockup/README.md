# Notes AI — UI mockup

Static, self-contained HTML/CSS/JS mockup of the target Notes AI web app.
No build step, no backend — open any file directly in a browser.

## Pages (the user flow)

| File              | Step             | Purpose                                                              |
| ----------------- | ---------------- | -------------------------------------------------------------------- |
| `index.html`      | Dashboard        | Landing page, stats, flow overview, recent notes                     |
| `new-note.html`   | 1. Add source    | Pick a source type (YouTube, web, PDF, image, audio) and submit it   |
| `processing.html` | 2. Processing    | Animated pipeline: extract → outline → draft → highlight → visuals   |
| `note.html`       | 3. Review note   | Generated Markdown note with highlights, callouts, and related notes |
| `library.html`    | 4. Save & browse | Knowledge base grid with search and source-type filters              |

Start at `index.html` and follow the buttons/links through the flow.

Shared styles live in `assets/style.css`; light interactivity (tabs, the
simulated pipeline progress, filter-chip toggling) lives in `assets/app.js`.
