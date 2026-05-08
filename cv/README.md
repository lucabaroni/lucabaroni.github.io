# CV Build System

Edit `cv_source.md` to update the CV, then run `build_cv.py` to generate HTML and PDF.

## Setup

```bash
pip3 install pyyaml --break-system-packages
```

## Usage

```bash
# HTML only (default output: Luca_Baroni_CV_generated.html)
python3 build_cv.py

# Custom HTML output path
python3 build_cv.py -o my_cv.html

# Also generate a PDF (requires Chrome)
python3 build_cv.py --pdf

# Custom PDF path (implies --pdf)
python3 build_cv.py --pdf-output ~/Desktop/Luca_Baroni_CV.pdf

# Both custom HTML and PDF paths
python3 build_cv.py -o out.html --pdf-output ~/Desktop/cv.pdf

# Include the Preprints section (excluded by default)
python3 build_cv.py --preprints -o cv_with_preprints.html
```

## Editing cv_source.md

The file has two parts: a YAML frontmatter block and a Markdown body.

### YAML frontmatter (`---` … `---`)

Controls the left sidebar. Fields:

| Field | Description |
|---|---|
| `name`, `location`, `email`, `citizenship` | Personal info |
| `links` | List of `{ label, url }` items |
| `skills` | List of bullet strings |
| `languages` | List of `{ name, level }` where `level` is 0–100 |
| `programming` | List of bullet strings |
| `equal_note` | Note rendered after the last publications section (e.g. `"* denotes equal contributions"`) |

### Body sections

Each `##` heading becomes a section in the right column.

**About Me** — free paragraphs, separated by a blank line.

**Education / Research/Work Experience** — each entry is a `###` heading (the bold title) followed by a detail line:

```markdown
### PhD in Computational Neuroscience, Charles University, Prague
September 2020 — Present. Supervisor: Jan Antolík
```

**Publications (Peer-reviewed) / Preprints** — each entry is a `###` heading with `authors:` and `venue:` lines. You can also add an optional `note:` line for status text under the venue:

```markdown
### Paper title here
authors: **Baroni L.***, Other A., Author B.
venue: NeurIPS, 2025
note: Camera-ready in progress. Available upon request.
```

### Inline formatting

| Syntax | Output |
|---|---|
| `**text**` | Bold |
| `*text*` | Italic (content must start and end with a letter/digit) |
| `{*}` | Literal `*` inside a bold span — use `**Name{*}**` to keep the asterisk inside `<strong>` |

### Commenting out entries

Wrap any `###` block in an HTML comment to exclude it from the output:

```markdown
<!-- ### Unpublished paper
authors: ...
venue: arXiv, 2025 -->
```

### Preprints section

The `## Preprints` section is excluded by default. Pass `--preprints` to include it. The `equal_note` always appears after the last publication-type section, regardless of how many sections there are.
