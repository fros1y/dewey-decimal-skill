---
name: metadata-extraction
description: Extract author, title, year, and contributor metadata from ebook files (EPUB, PDF). Use when you need to identify a book's bibliographic information from its embedded metadata or filename.
---

# Metadata Extraction

Extract bibliographic metadata from ebook files.

## Priority Order

1. EPUB OPF metadata (most authoritative)
2. PDF document properties
3. Filename parsing (least reliable)
4. Book text content analysis (when embedded metadata and filename are unhelpful)
5. User input (for disambiguation only)

## EPUB Extraction

### Step 1: Find OPF Path

```bash
unzip -p "$file" META-INF/container.xml | grep -oP 'full-path="\K[^"]*'
```

Returns path like `OEBPS/content.opf` or `content.opf`.

### Step 2: Extract Metadata

```bash
unzip -p "$file" "$opf_path" | grep -E '<dc:(creator|title|date|contributor)'
```

### Fields

| Tag | Content |
|-----|---------|
| `<dc:creator>` | Author name(s) |
| `<dc:title>` | Book title |
| `<dc:date>` | Publication date (extract YYYY) |
| `<dc:contributor opf:role="trn">` | Translator |
| `<dc:contributor opf:role="edt">` | Editor |

## PDF Extraction

```bash
pdfinfo "$file" 2>/dev/null | grep -E '^(Title|Author|CreationDate|ModDate):'
```

Extract:
- Title field
- Author field
- CreationDate year (format: D:YYYYMMDDhhmmss)

## Filename Parsing

Parse for hints when metadata insufficient:
- Author: Often at start, before dash or title
- Title: Main text
- Year: Four digits in parentheses or at end

Example: `Charles.Bukowski.-.Love.Is.A.Dog.From.Hell.2007.RETAIL.EPUB.eBook-CTO.epub`
- Author: Charles Bukowski
- Title: Love Is A Dog From Hell
- Year: 2007

## Year Rules

Use publication year of THIS edition, not original work.

- Aristotle's Nicomachean Ethics (ancient) with Irwin translation (2019): use 2019
- Marx's Capital originally 1867: use edition's publication year
- If EPUB date differs from original work date, prefer EPUB date

## Useless Metadata

Some EPUBs have placeholder or garbage metadata. Treat these as missing:
- Title: `[No data]`, `Unknown`, `Untitled`, empty
- Author: `Unknown`, `Anonymous` (unless actually anonymous work), empty
- Date: Only modification date present, no publication date

When OPF metadata is useless, fall back to filename parsing immediately.

## Author Name Normalization

Fix common capitalization issues from metadata:
- `Harold Mcgee` → `Harold McGee` (fix surname caps)
- `CHARLES BUKOWSKI` → `Charles Bukowski` (fix all-caps)
- Preserve intentional lowercase particles: `de Beauvoir`, `van Gogh`

Use `opf:file-as` attribute if present - it often has correct citation format:
```xml
<dc:creator opf:file-as="McGee, Harold">Harold Mcgee</dc:creator>
```

## Translator Verification

Translator info in filenames is often wrong or refers to different editions.
- Verify translator matches publisher/edition (e.g., Penguin 2004 Marx = Fowkes, not Guyer-Wood)
- If translator not in metadata, check ISBN against known editions
- When uncertain, ask user

## Text Content Analysis

When embedded metadata and filename parsing yield no usable author or title, extract readable text from the book's early pages. Title pages and copyright pages together contain almost everything needed: title, author, publisher, edition year, and ISBN.

### EPUB Text Extraction

#### Step 1: Find spine order from OPF

```bash
unzip -p "$file" "$opf_path" | grep -oP 'href="\K[^"?#]*\.(xhtml|html|xml)'
```

This lists content documents in reading order. Take the first two or three items—they are almost always the title page and copyright page.

#### Step 2: Extract plain text from each content document

```bash
unzip -p "$file" "$content_doc" | sed 's/<[^>]*>//g; /^[[:space:]]*$/d'
```

Limit to the first 150 lines of output. Strip HTML tags; the remaining text is sufficient for pattern matching. HTML entities (`&amp;`, `&quot;`, `&apos;`, `&#NNN;`) may remain in the output—interpret them as their character equivalents when extracting field values.

### PDF Text Extraction

```bash
pdftotext -f 1 -l 5 "$file" -
```

Extracts pages 1–5 as plain text. These pages almost always include the title page and copyright page.

If `pdftotext` is unavailable:

```bash
python3 -c "
import sys
try:
    import pypdf
    r = pypdf.PdfReader(sys.argv[1])
    for p in r.pages[:5]:
        print(p.extract_text())
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
" "$file"
```

### Interpreting Extracted Text

Scan the raw text for the following patterns in order.

#### Title page

The title page typically appears on page 1 or the first content document. Characteristics:
- The title is usually the largest or most prominent text block, often isolated on its own line.
- The author byline immediately follows, often prefixed with "By", or stands alone on a line.
- Subtitle follows the title, sometimes separated by a colon or on its own line.

Look for a short (1–10 word) line of text early in the document that matches no obvious chapter/section heading pattern; that is the title candidate.

#### Copyright page

The copyright page follows the title page, usually page 2–4. Extract:

| Pattern | Example | Field |
|---------|---------|-------|
| `© YYYY` or `Copyright YYYY` | `© 2019 Jane Smith` | Year + Author |
| `First published YYYY` | `First published 2019` | Original year |
| `This edition published YYYY` | `This edition published 2021` | Edition year (prefer this) |
| `Published by Publisher, YYYY` | `Published by Penguin, 2021` | Publisher + Year |
| `ISBN[-13]?[: ]+[\d\-X ]{10,17}` | `ISBN 978-0-14-028329-7` | ISBN |
| `Translated by Name` | `Translated by Henry Chadwick` | Translator |
| `Edited by Name` | `Edited by Mary Beard` | Editor |

Prefer the **edition** publication year over the original work year.

#### ISBN lookup

If an ISBN is found in the text, normalize it and validate it before querying the API. ISBN-10 must be exactly 10 characters (9 digits + digit or X check character); ISBN-13 must be exactly 13 digits. Strip all hyphens and spaces before checking length. If validation fails, discard the candidate and continue with text-extracted values only.

```bash
# Normalize: strip hyphens and spaces
ISBN=$(echo "$raw_isbn" | tr -d '[:space:]-')
curl -s "https://openlibrary.org/api/books?bibkeys=ISBN:${ISBN}&format=json&jscmd=data"
```

The response is a JSON object keyed by `"ISBN:XXXXXXXXXX"`. Useful fields:

| JSON path | Field |
|-----------|-------|
| `.title` | Title |
| `.authors[].name` | Author(s) |
| `.publish_date` | Publication date |
| `.publishers[].name` | Publisher |
| `.subjects[].name` | Subjects (useful for Dewey classification) |

If the API returns no data (unknown ISBN or network unavailable), continue with the text-extracted values.

### Text Extraction Quality Notes

- Scanned PDFs without an OCR text layer yield no usable text. In this case skip to user input.
- DRM-protected EPUBs may produce empty or garbled text. Skip to user input.
- Prefer copyright-page year over title-page year when both are present; the copyright page year is the edition year.
- If multiple author candidates appear, prefer the one on the title page over those on the copyright page (which may list editors or translators instead).

## Missing Data

When metadata genuinely unavailable:
- No author: Ask user
- No year: Ask user for "publication year of this edition"
- Ambiguous title: Ask user
- No translator but work is translated: Ask user or look up by ISBN/publisher

Do not guess. Do not proceed without author and title.
