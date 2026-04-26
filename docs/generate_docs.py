#!/usr/bin/env python3
"""
Generate styled HTML and PDF versions of all planning documents.
Usage: python3 docs/generate_docs.py
"""

import os
import subprocess
import sys
import markdown
from pathlib import Path

DOCS_DIR = Path(__file__).parent
HTML_DIR = DOCS_DIR / "html"
PDF_DIR  = DOCS_DIR / "pdf"

HTML_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

DOCS = [
    ("ARCHITECTURE.md",    "Architecture"),
    ("REQUIREMENTS.md",    "Requirements"),
    ("PROJECT_PLAN.md",    "Project Plan"),
    ("ROADMAP.md",         "Roadmap"),
    ("SEASON_2026_PLAN.md","2026 Season Deadline Plan"),
]

# ── Shared CSS ────────────────────────────────────────────────────────────────
CSS = """
/* ── Screen (dark theme) ─────────────────────────────── */
@media screen {
  :root {
    --bg:       #07090f;
    --bg-card:  #0d1117;
    --bg-code:  #111827;
    --border:   #1e2d42;
    --accent:   #38bdf8;
    --green:    #34d399;
    --yellow:   #fbbf24;
    --red:      #ef4444;
    --text:     #e2e8f0;
    --muted:    #64748b;
    --dim:      #94a3b8;
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 15px;
    line-height: 1.7;
    max-width: 860px;
    margin: 0 auto;
    padding: 48px 36px;
  }
  .doc-header {
    border-bottom: 1px solid var(--border);
    padding-bottom: 24px;
    margin-bottom: 40px;
  }
  .doc-header .project-label {
    font-size: 0.72em;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent);
    font-weight: 600;
    margin-bottom: 6px;
  }
  .doc-header h1 {
    font-size: 2em;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.02em;
    margin: 0 0 8px;
  }
  .doc-header .meta {
    color: var(--muted);
    font-size: 0.82em;
  }
  h1 { font-size: 1.9em; color: var(--text); font-weight: 700; margin: 2em 0 0.5em; letter-spacing: -0.02em; }
  h2 { font-size: 1.3em; color: var(--accent); font-weight: 700; margin: 2em 0 0.6em; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
  h3 { font-size: 1.05em; color: var(--dim); font-weight: 700; margin: 1.6em 0 0.5em; }
  h4 { font-size: 0.9em; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin: 1.4em 0 0.4em; }
  p  { margin: 0 0 1em; color: var(--text); }
  a  { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  strong { color: var(--text); font-weight: 700; }
  em     { color: var(--dim); font-style: italic; }

  ul, ol { margin: 0 0 1em 1.4em; padding: 0; }
  li     { margin: 0.3em 0; color: var(--text); }

  /* Code + pre */
  code {
    background: var(--bg-code);
    color: #a5f3fc;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 0.85em;
    border: 1px solid var(--border);
  }
  pre {
    background: var(--bg-code);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
    overflow-x: auto;
    margin: 0 0 1.5em;
  }
  pre code {
    background: none;
    border: none;
    padding: 0;
    color: #a5f3fc;
    font-size: 0.82em;
    line-height: 1.6;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 1.5em;
    font-size: 0.88em;
  }
  th {
    background: #111827;
    color: var(--accent);
    padding: 10px 14px;
    text-align: left;
    font-size: 0.8em;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    border-bottom: 1px solid var(--border);
  }
  td {
    padding: 9px 14px;
    border-bottom: 1px solid #111827;
    color: var(--text);
    vertical-align: top;
  }
  tr:last-child td { border-bottom: none; }
  tr:nth-child(even) td { background: #0a0e18; }
  tr:hover td { background: #1a2235; }

  /* Blockquote — used for callout notes */
  blockquote {
    border-left: 3px solid var(--accent);
    background: #0d1a2a;
    margin: 0 0 1.5em;
    padding: 12px 18px;
    border-radius: 0 8px 8px 0;
  }
  blockquote p { color: var(--dim); margin: 0; }

  hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 2.5em 0;
  }

  .toc {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 40px;
  }
  .toc h2 { border: none; margin-top: 0; font-size: 0.82em; text-transform: uppercase; letter-spacing: 0.1em; padding: 0; }
  .toc ul  { margin: 8px 0 0 1em; }
  .toc li  { font-size: 0.88em; margin: 0.3em 0; }
  .toc a   { color: var(--dim); }
  .toc a:hover { color: var(--accent); }

  .doc-footer {
    border-top: 1px solid var(--border);
    margin-top: 48px;
    padding-top: 20px;
    font-size: 0.75em;
    color: var(--muted);
    display: flex;
    justify-content: space-between;
  }
}

/* ── Print (clean white document) ───────────────────────── */
@media print {
  :root {
    --text:   #1a1a1a;
    --muted:  #666;
    --dim:    #444;
    --accent: #0369a1;
    --border: #d1d5db;
    --bg-code:#f3f4f6;
  }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body {
    background: #fff;
    color: var(--text);
    font-family: 'Georgia', serif;
    font-size: 11pt;
    line-height: 1.6;
    max-width: 100%;
    margin: 0;
    padding: 0;
  }
  .doc-header {
    background: #0c2340;
    color: #fff;
    padding: 36pt 48pt 28pt;
    margin-bottom: 0;
    border-bottom: none;
  }
  .doc-header .project-label {
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #7dd3fc;
    font-family: 'Helvetica Neue', sans-serif;
    font-weight: 600;
    margin-bottom: 6pt;
  }
  .doc-header h1 {
    font-size: 24pt;
    color: #fff;
    font-family: 'Helvetica Neue', sans-serif;
    font-weight: 700;
    margin: 0 0 8pt;
  }
  .doc-header .meta {
    font-size: 9pt;
    color: #93c5fd;
    font-family: 'Helvetica Neue', sans-serif;
  }
  .content-wrap { padding: 36pt 48pt; }
  h1 { font-size: 18pt; color: #0c2340; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; margin: 24pt 0 8pt; page-break-after: avoid; }
  h2 { font-size: 13pt; color: var(--accent); font-family: 'Helvetica Neue', sans-serif; font-weight: 700; margin: 20pt 0 6pt; border-bottom: 1pt solid var(--border); padding-bottom: 4pt; page-break-after: avoid; }
  h3 { font-size: 11pt; color: #374151; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; margin: 14pt 0 4pt; page-break-after: avoid; }
  h4 { font-size: 9pt; color: var(--muted); font-family: 'Helvetica Neue', sans-serif; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; margin: 12pt 0 4pt; page-break-after: avoid; }
  p  { margin: 0 0 8pt; }
  a  { color: var(--accent); }
  ul, ol { margin: 0 0 8pt 18pt; }
  li { margin: 2pt 0; }
  code {
    background: var(--bg-code);
    color: #1e40af;
    padding: 1pt 4pt;
    border-radius: 3pt;
    font-family: 'Courier New', monospace;
    font-size: 9pt;
    border: 0.5pt solid #e5e7eb;
  }
  pre {
    background: var(--bg-code);
    border: 0.5pt solid var(--border);
    border-radius: 4pt;
    padding: 10pt 14pt;
    margin: 0 0 10pt;
    page-break-inside: avoid;
    overflow: hidden;
  }
  pre code {
    background: none;
    border: none;
    padding: 0;
    color: #1e3a5f;
    font-size: 8.5pt;
    line-height: 1.5;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 12pt;
    font-size: 9.5pt;
    font-family: 'Helvetica Neue', sans-serif;
    page-break-inside: avoid;
  }
  th {
    background: #0c2340;
    color: #fff;
    padding: 6pt 10pt;
    text-align: left;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 700;
  }
  td {
    padding: 5pt 10pt;
    border-bottom: 0.5pt solid var(--border);
    vertical-align: top;
  }
  tr:nth-child(even) td { background: #f9fafb; }
  blockquote {
    border-left: 3pt solid var(--accent);
    background: #eff6ff;
    margin: 0 0 10pt;
    padding: 8pt 14pt;
    page-break-inside: avoid;
  }
  blockquote p { color: #1e3a5f; margin: 0; }
  hr { border: none; border-top: 0.5pt solid var(--border); margin: 18pt 0; }
  .toc {
    background: #f9fafb;
    border: 0.5pt solid var(--border);
    border-radius: 4pt;
    padding: 14pt 18pt;
    margin-bottom: 20pt;
    page-break-inside: avoid;
  }
  .toc h2 { color: var(--muted); font-size: 8pt; border: none; margin: 0 0 6pt; padding: 0; }
  .toc ul  { margin: 0 0 0 14pt; }
  .toc li  { font-size: 9pt; }
  .doc-footer {
    position: running(footer);
    font-size: 8pt;
    color: var(--muted);
    text-align: center;
    border-top: 0.5pt solid var(--border);
    padding-top: 6pt;
    font-family: 'Helvetica Neue', sans-serif;
  }
  @page {
    size: letter;
    margin: 0.75in 0.75in 1in 0.75in;
    @bottom-center {
      content: "ACE Tracker — " attr(data-title) " | Page " counter(page) " of " counter(pages);
      font-size: 8pt;
      color: #9ca3af;
      font-family: 'Helvetica Neue', sans-serif;
    }
  }
  /* Critical: prevent content cuts */
  section, .section { page-break-inside: avoid; }
  tr { page-break-inside: avoid; }
  img { page-break-inside: avoid; max-width: 100%; }
  .toc { page-break-after: always; }
}
"""

# ── HTML template ─────────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-title="{title}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — ACE Tracker</title>
<style>{css}</style>
</head>
<body>
<div class="doc-header">
  <div class="project-label">ACE Tracker · Planning Document</div>
  <h1>{title}</h1>
  <div class="meta">Hurricane ACE Tracker Web Dashboard &nbsp;·&nbsp; Generated April 2026</div>
</div>

{toc_html}

<div class="content-wrap">
{body_html}
</div>

<div class="doc-footer">
  <span>ACE Tracker — {title}</span>
  <span>April 2026</span>
</div>
</body>
</html>"""

# ── TOC builder ───────────────────────────────────────────────────────────────
def build_toc(md_text):
    lines = md_text.split('\n')
    items = []
    for line in lines:
        if line.startswith('## '):
            heading = line[3:].strip()
            anchor  = heading.lower().replace(' ', '-').replace('/', '').replace('(', '').replace(')', '').replace(',', '').replace(':', '').replace('+', '').replace('&', '').replace("'", "")
            items.append(f'<li><a href="#{anchor}">{heading}</a></li>')
        elif line.startswith('### '):
            heading = line[4:].strip()
            anchor  = heading.lower().replace(' ', '-').replace('/', '').replace('(', '').replace(')', '').replace(',', '').replace(':', '').replace('+', '').replace('&', '').replace("'", "")
            items.append(f'<li style="margin-left:1.2em; font-size:0.9em"><a href="#{anchor}">{heading}</a></li>')
    if not items:
        return ''
    toc_items = '\n'.join(items)
    return f"""<div class="toc content-wrap">
  <h2>Contents</h2>
  <ul>{toc_items}</ul>
</div>"""

# ── Markdown → HTML with ID anchors on headings ───────────────────────────────
def md_to_html(md_text):
    # Use markdown library with tables and fenced code extensions
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc'])
    html = md.convert(md_text)
    return html

# ── Main ─────────────────────────────────────────────────────────────────────
def generate(md_filename, title):
    md_path   = DOCS_DIR / md_filename
    html_path = HTML_DIR / md_filename.replace('.md', '.html')
    pdf_path  = PDF_DIR  / md_filename.replace('.md', '.pdf')

    print(f"\n{'─'*50}")
    print(f"  Processing: {md_filename}")

    # Read markdown
    md_text = md_path.read_text(encoding='utf-8')

    # Build TOC and body
    toc_html  = build_toc(md_text)
    body_html = md_to_html(md_text)

    # Build full HTML
    html = HTML_TEMPLATE.format(
        title=title,
        css=CSS,
        toc_html=toc_html,
        body_html=body_html,
    )
    html_path.write_text(html, encoding='utf-8')
    print(f"  HTML → {html_path.relative_to(DOCS_DIR.parent)}")

    # Generate PDF via Chrome headless
    if not os.path.exists(CHROME):
        print(f"  PDF SKIPPED — Chrome not found at expected path")
        return

    cmd = [
        CHROME,
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--run-all-compositor-stages-before-draw',
        '--virtual-time-budget=5000',
        f'--print-to-pdf={pdf_path}',
        '--print-to-pdf-no-header',
        f'file://{html_path.resolve()}',
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0 and pdf_path.exists():
        size_kb = pdf_path.stat().st_size // 1024
        print(f"  PDF  → {pdf_path.relative_to(DOCS_DIR.parent)}  ({size_kb} KB)")
    else:
        print(f"  PDF FAILED: {result.stderr[:200]}")


if __name__ == '__main__':
    print("ACE Tracker — Document Generator")
    print(f"Output dirs: docs/html/  |  docs/pdf/")
    for filename, title in DOCS:
        generate(filename, title)
    print(f"\n{'─'*50}")
    print("  Done.")
