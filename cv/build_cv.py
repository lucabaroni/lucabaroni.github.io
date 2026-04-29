#!/usr/bin/env python3
"""
build_cv.py — Generate CV HTML (and optionally PDF) from cv_source.md

Usage:
  python3 build_cv.py                      # → Luca_Baroni_CV_generated.html
  python3 build_cv.py -o my_cv.html        # custom output path
  python3 build_cv.py --pdf                # also generate PDF (requires Chrome)
  python3 build_cv.py -o out.html --pdf              # both
  python3 build_cv.py --pdf-output ~/Desktop/cv.pdf  # custom PDF path (implies --pdf)
"""

import base64
import re
import sys
import argparse
import subprocess
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Run: pip3 install pyyaml --break-system-packages")
    sys.exit(1)

# ── Font loading ─────────────────────────────────────────────────────────────

def find_font(filename: str) -> Path | None:
    """Search for a font file next to the script, then one directory up."""
    candidates = [
        Path(__file__).parent / filename,
        Path(__file__).parent.parent / filename,
    ]
    return next((p for p in candidates if p.exists()), None)


def font_face_css(family: str, filename: str) -> str:
    """Return a @font-face block with the font embedded as base64, or '' if not found."""
    path = find_font(filename)
    if not path:
        return ""
    ext = path.suffix.lstrip(".")
    fmt = {"otf": "opentype", "ttf": "truetype", "woff": "woff", "woff2": "woff2"}.get(ext, ext)
    b64 = base64.b64encode(path.read_bytes()).decode()
    return (
        f"    @font-face {{\n"
        f"      font-family: '{family}';\n"
        f"      src: url('data:font/{fmt};base64,{b64}') format('{fmt}');\n"
        f"    }}\n"
    )


# ── Section SVG icons (keyed by section title) ────────────────────────────────

SECTION_ICONS = {
    "About Me": '<path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/>',
    "Education": '<path d="M12 3L1.5 8.25 12 13.5l8.57-4.28v5.1h1.93V8.25L12 3zm-5.79 8.54v4.13L12 18.75l5.79-3.08v-4.13L12 14.43l-5.79-2.89z"/>',
    "Research/Work Experience": '<path d="M20 6h-4V4c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v11c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6 0h-4V4h4v2z"/>',
    "Publications (Peer-reviewed)": '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>',
    "Preprints": '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>',
}

# ── CSS (extracted verbatim from the original HTML) ───────────────────────────

CSS = """    @page {
      size: A4;
      margin: 0;
    }

    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    :root {
      --accent: #5B7F5B;
      --head-text: #333333;
      --body-text: #444444;
      --bar-done: #5B7F5B;
      --bar-undone: #E0E0E0;
      --page-pad-top: 0.8cm;
      --page-pad-left: 1cm;
      --page-pad-right: 1cm;
      --page-pad-bottom: 0.9cm;
      --sidebar-width: 28.5%;
      --main-width: 71.5%;
      --gap: 1.05cm;
    }

    html, body {
      font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
      font-size: 10pt;
      color: var(--body-text);
      background: #fff;
      line-height: 1.28;
    }

    .page {
      width: 210mm;
      margin: 0 auto;
      padding: var(--page-pad-top) var(--page-pad-right) var(--page-pad-bottom) var(--page-pad-left);
      display: flex;
      position: relative;
    }

    /* Full-page preview on screen only — avoid min-height in print/PDF or a blank 2nd page can appear */
    @media screen {
      .page {
        min-height: 297mm;
      }
    }

    /* ── Vertical divider ──────────────────────────────── */
    .page::after {
      content: "";
      position: absolute;
      top: 1.28cm;
      bottom: 0.55cm;
      left: calc(var(--page-pad-left) + (210mm - var(--page-pad-left) - var(--page-pad-right)) * 0.285);
      width: 0.4pt;
      background: var(--accent);
    }

    /* ── Left sidebar ──────────────────────────────────── */
    .sidebar {
      width: var(--sidebar-width);
      padding-right: calc(var(--gap) / 2);
      text-align: center;
      flex-shrink: 0;
    }

    .name {
      font-family: 'JetBrainsMono', "Courier New", monospace;
      font-size: 20pt;
      font-weight: normal;
      color: var(--accent);
      letter-spacing: -0.02em;
      white-space: nowrap;
      margin-top: 0.1em;
      margin-bottom: 0.65em;
      text-transform: uppercase;
    }

    .side-section-title {
      font-size: 10pt;
      font-weight: bold;
      color: var(--accent);
      text-transform: uppercase;
      margin-top: 0.85em;
      margin-bottom: 0.12em;
    }

    .side-section-title::after {
      content: "";
      display: block;
      width: 55%;
      height: 0.4pt;
      background: var(--accent);
      margin: 0.15em auto 0.38em;
    }

    .sidebar p,
    .sidebar a {
      font-size: 10pt;
      line-height: 1.5;
    }

    .sidebar a {
      color: var(--accent);
      text-decoration: none;
    }

    .sidebar a:hover {
      text-decoration: underline;
    }

    .sidebar .small-text {
      font-size: 9pt;
    }

    .sidebar .small-text p {
      font-size: 9pt;
      margin-bottom: 0.3em;
    }

    /* ── Language bars ──────────────────────────────────── */
    .lang-bar {
      margin-bottom: 0.32em;
    }

    .lang-bar .label {
      display: block;
      margin-bottom: 0.08em;
    }

    .lang-bar .bar {
      display: block;
      width: 70%;
      height: 4px;
      background: var(--bar-undone);
      margin: 0 auto;
      border-radius: 0;
    }

    .lang-bar .bar .fill {
      display: block;
      height: 100%;
      background: var(--bar-done);
    }

    /* ── Right main column ─────────────────────────────── */
    .main {
      width: var(--main-width);
      padding-left: calc(var(--gap) / 2);
    }

    .main-section-title {
      font-size: 12pt;
      font-weight: bold;
      color: var(--accent);
      text-transform: uppercase;
      margin-top: 0.38em;
      margin-bottom: 0.15em;
      position: relative;
      break-after: avoid;
      page-break-after: avoid;
    }

    .section-icon {
      position: absolute;
      left: -0.6cm;
      top: 50%;
      transform: translate(-50%, -50%);
      width: 26px;
      height: 26px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #fff;
      padding: 4px 3px;
      z-index: 1;
    }

    .section-icon svg {
      width: 18px;
      height: 18px;
      fill: var(--accent);
    }

    /* ── CV entry ──────────────────────────────────────── */
    .cv-entry {
      margin-bottom: 0.18em;
      break-inside: avoid;
      page-break-inside: avoid;
    }

    .cv-entry .entry-title {
      font-weight: bold;
      color: var(--head-text);
    }

    .cv-entry .entry-detail {
      font-size: 9pt;
      color: var(--body-text);
    }

    .cv-entry .entry-detail em {
      font-style: italic;
    }

    /* ── Publication entry ─────────────────────────────── */
    .pub-entry {
      margin-bottom: 0.18em;
      break-inside: avoid;
      page-break-inside: avoid;
    }

    .pub-entry .pub-title {
      font-size: 9.25pt;
      font-weight: bold;
      color: var(--head-text);
      line-height: 1.15;
    }

    .pub-entry .pub-authors {
      font-size: 9pt;
      color: var(--body-text);
    }

    .pub-entry .pub-venue {
      font-size: 9pt;
      font-style: italic;
      color: var(--body-text);
    }

    .about-text {
      margin-bottom: 0.18em;
      orphans: 3;
      widows: 3;
    }

    .equal-note {
      text-align: right;
      font-size: 9pt;
      margin-top: 0.2em;
    }

    @media print {
      html, body {
        height: auto !important;
        margin: 0;
      }
      body { background: none; }
      .page,
      .sidebar,
      .main {
        break-inside: auto;
        page-break-inside: auto;
      }
      .side-section-title,
      .lang-bar,
      .sidebar p,
      .sidebar .small-text p {
        break-inside: avoid;
        page-break-inside: avoid;
      }
      .page {
        margin: 0;
        padding: var(--page-pad-top) var(--page-pad-right) var(--page-pad-bottom) var(--page-pad-left);
        width: 100%;
        min-height: 0 !important;
        height: auto !important;
        page-break-after: avoid;
        break-after: avoid;
      }
    }"""


# ── Inline Markdown → HTML ────────────────────────────────────────────────────

def h(text: str) -> str:
    """HTML-escape a raw text string (ampersands only — < and > don't appear in source)."""
    return text.replace("&", "&amp;")


def md_inline(text: str) -> str:
    """Convert inline markdown (bold, italic) to HTML, then HTML-escape ampersands.

    Special notation:
      {*}  — a literal asterisk that is treated as part of the surrounding
             bold/italic span (use inside **…** to keep * inside <strong>).
             Example: **Baroni L.{*}** → <strong>Baroni L.*</strong>
    """
    # Escape & first (before inserting any HTML tags)
    text = h(text)
    # Temporarily replace {*} placeholder so it survives the bold regex
    STAR_PLACEHOLDER = "\x00STAR\x00"
    text = text.replace("{*}", STAR_PLACEHOLDER)
    # **bold** → <strong>bold</strong>  (non-greedy, so **A** **B** works)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Restore placeholder to literal *
    text = text.replace(STAR_PLACEHOLDER, "*")
    # *italic* → <em>italic</em>
    # Require content to start AND end with a letter/digit so that lone footnote
    # asterisks like "Author*, Other*" are NOT treated as italic delimiters.
    text = re.sub(
        r'(?<![*\w])\*([A-Za-z\d][^*]*[A-Za-z\d]|[A-Za-z\d])\*(?![*\w])',
        r'<em>\1</em>',
        text,
    )
    return text


# ── Markdown source parser ────────────────────────────────────────────────────

def parse_source(path: Path):
    """
    Parse cv_source.md.  Returns (frontmatter_dict, sections).

    sections is a list of dicts:
      { "title": str, "type": "about"|"entries"|"publications",
        "paragraphs": [...],   # for about
        "entries": [...],      # for entries/publications
        "equal_note": str|None }
    """
    text = path.read_text(encoding="utf-8")

    # Split YAML frontmatter
    if not text.startswith("---"):
        raise ValueError("cv_source.md must start with --- YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Could not find closing --- for YAML frontmatter")
    fm = yaml.safe_load(parts[1])
    body = parts[2].strip()

    sections = []
    # Split body into ## sections
    raw_sections = re.split(r'^## ', body, flags=re.MULTILINE)
    for raw in raw_sections:
        raw = raw.strip()
        if not raw:
            continue
        lines = raw.split("\n")
        title = lines[0].strip()
        content = "\n".join(lines[1:]).strip()

        if title == "About Me":
            paragraphs = [p.strip() for p in re.split(r'\n{2,}', content) if p.strip()]
            sections.append({"title": title, "type": "about", "paragraphs": paragraphs})

        elif title.startswith("Publications") or title.startswith("Preprints"):
            entries = parse_pub_section(content)
            sections.append({
                "title": title,
                "type": "publications",
                "entries": entries,
            })

        else:
            entries = parse_entry_section(content)
            sections.append({"title": title, "type": "entries", "entries": entries})

    return fm, sections


def parse_entry_section(content: str):
    """
    Parse a section of ### Title \\n detail lines into entry dicts.
    Returns list of {"title": str, "detail": str}
    """
    entries = []
    blocks = re.split(r'^### ', content, flags=re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n", 1)
        title = lines[0].strip()
        detail = lines[1].strip() if len(lines) > 1 else ""
        entries.append({"title": title, "detail": detail})
    return entries


def parse_pub_section(content: str):
    """
    Parse a publications/preprints section.  Returns a list of entries.
    Each entry: {"title": str, "authors": str, "venue": str}

    HTML comment blocks (<!-- ... -->) are stripped first, so you can
    comment out an entry by wrapping its ### block in <!-- ... -->.
    """
    # Strip HTML comment blocks before parsing
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL).strip()

    entries = []
    blocks = re.split(r'^### ', content, flags=re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        title = lines[0].strip()
        authors = ""
        venue = ""
        for line in lines[1:]:
            line = line.strip()
            if line.startswith("authors:"):
                authors = line[len("authors:"):].strip()
            elif line.startswith("venue:"):
                venue = line[len("venue:"):].strip()
        entries.append({"title": title, "authors": authors, "venue": venue})
    return entries


# ── HTML builder ──────────────────────────────────────────────────────────────

def build_sidebar(fm: dict, ai_safety: bool = False) -> str:
    parts = []

    parts.append(f'    <div class="name">{h(fm["name"])}</div>\n')

    # Personal Information
    parts.append('\n    <!-- Personal Information -->\n')
    parts.append('    <div class="side-section-title">Personal Information</div>\n')
    parts.append(f'    <p>{h(fm["location"])}</p>\n')
    parts.append(f'    <p><a href="mailto:{h(fm["email"])}">{h(fm["email"])}</a></p>\n')
    parts.append(f'    <p>{h(fm["citizenship"])}</p>\n')

    # Links
    parts.append('\n    <!-- Links -->\n')
    parts.append('    <div class="side-section-title">Links</div>\n')
    for link in fm["links"]:
        parts.append(f'    <p><a href="{h(link["url"])}">{h(link["label"])}</a></p>\n')

    # AI Safety Expertise (only in --ai-safety variant, placed before Skills)
    if ai_safety and fm.get("ai_safety_expertise"):
        parts.append('\n    <!-- AI Safety Expertise -->\n')
        parts.append('    <div class="side-section-title">Technical AI Safety Expertise</div>\n')
        parts.append('    <div class="small-text">\n')
        for item in fm["ai_safety_expertise"]:
            parts.append(f'      <p>{h(item)}</p>\n')
        parts.append('    </div>\n')

    # Skills
    parts.append('\n    <!-- Skills -->\n')
    parts.append('    <div class="side-section-title">Strengths &amp; Experience</div>\n')
    parts.append('    <div class="small-text">\n')
    for skill in fm["skills"]:
        parts.append(f'      <p>{h(skill)}</p>\n')
    parts.append('    </div>\n')

    # Languages
    parts.append('\n    <!-- Languages -->\n')
    parts.append('    <div class="side-section-title">Languages</div>\n')
    for lang in fm["languages"]:
        parts.append(
            f'    <div class="lang-bar">\n'
            f'      <span class="label">{h(lang["name"])}</span>\n'
            f'      <span class="bar"><span class="fill" style="width:{lang["level"]}%"></span></span>\n'
            f'    </div>\n'
        )

    # Programming Languages & Tools
    # Use trimmed version in --ai-safety variant (fine-tuning/evals moved to AI Safety section)
    programming = fm.get("programming_ai_safety") if ai_safety else fm["programming"]
    parts.append('\n    <!-- Programming Languages & Tools -->\n')
    parts.append('    <div class="side-section-title">Programming Languages &amp; Tools</div>\n')
    parts.append('    <div class="small-text">\n')
    for item in programming:
        parts.append(f'      <p>{h(item)}</p>\n')
    parts.append('    </div>\n')

    return "".join(parts)


def section_icon_html(title: str) -> str:
    path_d = SECTION_ICONS.get(title, "")
    if not path_d:
        return ""
    return f'<span class="section-icon"><svg viewBox="0 0 24 24">{path_d}</svg></span>'


def build_main(sections: list, equal_note: str | None = None) -> str:
    parts = []

    # Index of the last publication-type section (for equal_note placement)
    last_pub_idx = max(
        (i for i, s in enumerate(sections) if s["type"] == "publications"),
        default=None,
    )

    for i, sec in enumerate(sections):
        title = sec["title"]
        icon = section_icon_html(title)
        # Use short comment label (strip parentheticals) to match original HTML
        comment_label = re.sub(r'\s*\(.*?\)', '', title).strip()
        parts.append(f'\n    <!-- {comment_label} -->\n')
        parts.append(f'    <div class="main-section-title">{icon}{h(title)}</div>\n')

        if sec["type"] == "about":
            for para in sec["paragraphs"]:
                parts.append(f'    <p class="about-text">{md_inline(para)}</p>\n')

        elif sec["type"] == "entries":
            for entry in sec["entries"]:
                parts.append(
                    f'\n    <div class="cv-entry">\n'
                    f'      <div class="entry-title">{h(entry["title"])}</div>\n'
                    f'      <div class="entry-detail">{md_inline(entry["detail"])}</div>\n'
                    f'    </div>\n'
                )

        elif sec["type"] == "publications":
            for pub in sec["entries"]:
                parts.append(
                    f'\n    <div class="pub-entry">\n'
                    f'      <div class="pub-title">{h(pub["title"])}</div>\n'
                    f'      <div class="pub-authors">{md_inline(pub["authors"])}</div>\n'
                    f'      <div class="pub-venue">{h(pub["venue"])}</div>\n'
                    f'    </div>\n'
                )
            # Render equal_note once, after the last pub-type section
            if equal_note and i == last_pub_idx:
                parts.append(f'\n    <p class="equal-note">{h(equal_note)}</p>\n')

    return "".join(parts)


def build_html(fm: dict, sections: list, ai_safety: bool = False) -> str:
    sidebar = build_sidebar(fm, ai_safety=ai_safety)
    main = build_main(sections, equal_note=fm.get("equal_note"))
    name = h(fm["name"])
    name_font_css = font_face_css("JetBrainsMono", "JetBrainsMono-Light.ttf")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} \u2013 CV</title>
  <style>
{name_font_css}{CSS}
  </style>
</head>
<body>

<div class="page">

  <!-- \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550 LEFT SIDEBAR \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550 -->
  <div class="sidebar">

{sidebar}
  </div>

  <!-- \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550 RIGHT COLUMN \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550 -->
  <div class="main">
{main}
  </div>

</div>

</body>
</html>
"""


# ── PDF generation ────────────────────────────────────────────────────────────

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
]


def find_chrome() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def generate_pdf(html_path: Path, pdf_path: Path):
    chrome = find_chrome()
    if not chrome:
        print("Warning: Chrome not found; skipping PDF generation.")
        print("Install Chrome or open the HTML file and print to PDF manually.")
        return

    abs_html = html_path.resolve()
    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={pdf_path.resolve()}",
        "--print-to-pdf-no-header",
        str(abs_html),
    ]
    print(f"Generating PDF via Chrome headless...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Chrome error: {result.stderr}")
    else:
        print(f"PDF written to: {pdf_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build CV HTML (and PDF) from cv_source.md")
    parser.add_argument(
        "-s", "--source",
        default=str(Path(__file__).parent / "cv_source.md"),
        help="Path to cv_source.md (default: cv_source.md next to this script)",
    )
    parser.add_argument(
        "-o", "--output",
        default=str(Path(__file__).parent / "Luca_Baroni_CV_generated.html"),
        help="Output HTML path (default: Luca_Baroni_CV_generated.html)",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Also generate a PDF (path defaults to same name as HTML with .pdf extension)",
    )
    parser.add_argument(
        "--pdf-output",
        default=None,
        metavar="PATH",
        help="Custom output path for the PDF (implies --pdf)",
    )
    parser.add_argument(
        "--preprints",
        action="store_true",
        help="Include the Preprints section (excluded by default)",
    )
    parser.add_argument(
        "--ai-safety",
        action="store_true",
        dest="ai_safety",
        help="AI safety variant: adds AI Safety Expertise section, trims Programming section",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    html_path = Path(args.output)
    pdf_path = Path(args.pdf_output) if args.pdf_output else html_path.with_suffix(".pdf")

    if not source_path.exists():
        print(f"Error: source file not found: {source_path}")
        sys.exit(1)

    print(f"Parsing {source_path}...")
    fm, sections = parse_source(source_path)

    if not args.preprints:
        sections = [s for s in sections if not s["title"].startswith("Preprints")]

    html = build_html(fm, sections, ai_safety=args.ai_safety)
    html_path.write_text(html, encoding="utf-8")
    print(f"HTML written to: {html_path}")

    if args.pdf or args.pdf_output:
        generate_pdf(html_path, pdf_path)


if __name__ == "__main__":
    main()
