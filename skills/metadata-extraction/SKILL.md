---
name: metadata-extraction
description: Extract author, title, year, and contributor metadata from ebook files (EPUB, PDF, MOBI, AZW, LIT, HTML). Use when you need to identify a book's bibliographic information from its embedded metadata or filename.
---

# Metadata Extraction

Extract bibliographic metadata from ebook files.

## Priority Order

1. EPUB OPF metadata (most authoritative)
2. MOBI/AZW embedded OPF metadata
3. PDF document properties
4. LIT embedded metadata
5. HTML document metadata
6. Filename parsing (least reliable)
7. Book text content analysis (when embedded metadata and filename are unhelpful)
8. Google Books online lookup (to enrich missing or incomplete fields)
9. User input (for disambiguation only)

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

## MOBI/AZW Extraction

MOBI and AZW files embed an OPF package (identical in structure to EPUB). Extract it by
unpacking the file with the `mobi` Python package, then reuse the EPUB OPF parsing steps.

### Step 1: Extract to Temp Directory

```bash
python3 - "$file" << 'PYEOF'
import glob
import mobi
import os
import sys
_, extracted = mobi.extract(sys.argv[1])
opf_files = glob.glob(os.path.join(os.path.dirname(extracted), '**', '*.opf'), recursive=True)
if opf_files:
    with open(opf_files[0]) as f:
        print(f.read())
PYEOF
```

If `mobi` is not installed, install it first: `pip install mobi`

### Step 2: Parse OPF Output

Apply the same field extraction as [EPUB Extraction](#epub-extraction) — the OPF structure
is identical.

### Fields

| Tag | Content |
|-----|---------|
| `<dc:creator>` | Author name(s) |
| `<dc:title>` | Book title |
| `<dc:date>` | Publication date (extract YYYY) |
| `<dc:contributor opf:role="trn">` | Translator |
| `<dc:contributor opf:role="edt">` | Editor |

If the `mobi` package is unavailable and `ebook-meta` (Calibre) is installed, use that instead:

```bash
ebook-meta "$file"
```

---

## LIT Extraction

LIT (Microsoft Reader) files embed OEB/OPF metadata. If `ebook-meta` (Calibre) is installed,
use it directly:

```bash
ebook-meta "$file" 2>/dev/null
```

Extract from its output:
- `Title` field → title
- `Author(s)` field → author(s)
- `Published` field → year (first four digits)
- `Translator` field → translator

If Calibre is unavailable, try extracting raw text strings and searching for metadata markers:

```bash
strings "$file" | grep -E -i '(Author|Creator|Title|Date|Publisher):' | head -20
```

Use filename parsing as the final fallback for LIT files when neither tool is available.

---

## HTML Extraction

HTML ebooks embed bibliographic data in `<meta>` tags and the `<title>` element. Parse them
with a Python one-liner using BeautifulSoup (already a project dependency):

```bash
python3 - "$file" << 'PYEOF'
from bs4 import BeautifulSoup
import sys

with open(sys.argv[1], encoding='utf-8', errors='replace') as f:
    soup = BeautifulSoup(f, 'html.parser')

# Title: prefer <meta name="title"> or <meta property="og:title">, fall back to <title>
title = (
    (soup.find('meta', attrs={'name': 'title'}) or {}).get('content')
    or (soup.find('meta', attrs={'property': 'og:title'}) or {}).get('content')
    or (soup.find('meta', attrs={'name': 'DC.title'}) or {}).get('content')
    or (soup.title.string if soup.title else None)
)

# Author: check common meta-tag names in priority order
author = (
    (soup.find('meta', attrs={'name': 'author'}) or {}).get('content')
    or (soup.find('meta', attrs={'name': 'DC.creator'}) or {}).get('content')
    or (soup.find('meta', attrs={'property': 'og:author'}) or {}).get('content')
    or (soup.find('meta', attrs={'name': 'citation_author'}) or {}).get('content')
)

# Date: publication year
date = (
    (soup.find('meta', attrs={'name': 'date'}) or {}).get('content')
    or (soup.find('meta', attrs={'name': 'DC.date'}) or {}).get('content')
    or (soup.find('meta', attrs={'name': 'citation_date'}) or {}).get('content')
    or (soup.find('meta', attrs={'name': 'pubdate'}) or {}).get('content')
)

if title:
    print('Title:', title.strip())
if author:
    print('Author:', author.strip())
if date:
    print('Date:', date.strip())
PYEOF
```

### Fields

| Meta tag | Content |
|----------|---------|
| `<meta name="author">` / `<meta name="DC.creator">` | Author name |
| `<meta name="title">` / `<meta property="og:title">` | Book title |
| `<meta name="date">` / `<meta name="DC.date">` | Publication date (extract YYYY) |
| `<title>` | Fallback for title when no meta title present |

Use filename parsing when none of these tags are present.

---

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

## Online Metadata Enrichment (Google Books)

Use the Google Books API to fill in fields that embedded metadata cannot
provide reliably: series, tags, rating, description, and ISBN. This mirrors
the technique used by Calibre's built-in Google Books metadata plugin.

### When to Enrich

After extracting local metadata (steps 1–3 above), run an online lookup when
**any** of the following fields are missing or empty:

- Series / series index
- Tags / subjects
- Rating
- Description / synopsis
- ISBN-13 or ISBN-10

You may also run a lookup to verify or correct the title and authors when the
local metadata appears garbled or placeholder-like.

### Running the Lookup

Use `lib/google_books.py` (requires the `requests` library).

**By ISBN** (most accurate — prefer when ISBN is already known):

```bash
python lib/google_books.py --isbn "$isbn"
```

**By title and author** (fallback when ISBN is unavailable):

```bash
python lib/google_books.py --title "$title" --author "$author"
```

Both forms output a single JSON object. A null result means no match was found.

### API Technique

The script queries:

```
GET https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1
```

No API key is required for public-domain lookups. Rate limits apply; do not
hammer the endpoint in tight loops.

### Response Field Mapping

| Script output key | Google Books API field                               | Calibre equivalent |
|-------------------|------------------------------------------------------|--------------------|
| `title`           | `volumeInfo.title` + `subtitle`                      | title              |
| `authors`         | `volumeInfo.authors[]`                               | authors            |
| `series`          | `volumeInfo.seriesInfo.shortSeriesBookTitle`          | series             |
| `series_index`    | `volumeInfo.seriesInfo.bookDisplayNumber`             | series_index       |
| `tags`            | `volumeInfo.categories[]`                            | tags               |
| `rating`          | `volumeInfo.averageRating`                           | rating (0–5 scale) |
| `description`     | `volumeInfo.description`                             | comments           |
| `isbn_13`         | `industryIdentifiers[ISBN_13]`                       | isbn               |
| `isbn_10`         | `industryIdentifiers[ISBN_10]`                       | isbn               |
| `published_date`  | `volumeInfo.publishedDate`                           | pubdate            |

### Merge Rules

Apply online results only where local metadata is absent or unusable:

1. **Title/Authors** – keep local value; only adopt online value when local
   metadata is flagged as useless (see Useless Metadata section above).
2. **Series / series_index** – use online value; embedded OPF rarely carries
   series info.
3. **Tags** – use online `categories` list as the initial tag set; append any
   subject tags already present in OPF.
4. **Rating** – use online `averageRating`; no reliable local source exists.
5. **Description** – use online `description` when OPF has no `<dc:description>`.
6. **ISBN** – prefer ISBN-13; fall back to ISBN-10. Adopt online value when
   not present locally.
7. **Published date** – do not override a local date with the online date;
   embedded dates are edition-specific (see Year Rules above).

### Amazon Metadata

Calibre's Amazon plugin retrieves the same fields by scraping Amazon product
pages. Amazon does not provide a public free API, so scraping is required;
this is fragile and subject to change without notice.

For most use cases the Google Books API provides equivalent coverage. When a
book is absent from Google Books (common for self-published or niche titles),
fall back to manual ISBN lookup at:

- https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data
- https://www.worldcat.org/isbn/{isbn} (browser lookup only)

### Example Workflow

```bash
# 1. Extract embedded metadata
isbn=$(unzip -p "$file" "$opf_path" | grep -oP '<dc:identifier[^>]*>\K[^<]*' | grep -E '^97[89]')

# 2. Enrich via Google Books
metadata=$(python lib/google_books.py --isbn "$isbn")

# 3. Parse fields
title=$(echo "$metadata"        | python -c "import json,sys; d=json.load(sys.stdin); print(d['title'] or '')")
authors=$(echo "$metadata"      | python -c "import json,sys; d=json.load(sys.stdin); print('; '.join(d['authors']))")
series=$(echo "$metadata"       | python -c "import json,sys; d=json.load(sys.stdin); print(d['series'] or '')")
series_index=$(echo "$metadata" | python -c "import json,sys; d=json.load(sys.stdin); print(d['series_index'] or '')")
tags=$(echo "$metadata"         | python -c "import json,sys; d=json.load(sys.stdin); print(', '.join(d['tags']))")
rating=$(echo "$metadata"       | python -c "import json,sys; d=json.load(sys.stdin); print(d['rating'] or '')")
description=$(echo "$metadata"  | python -c "import json,sys; d=json.load(sys.stdin); print(d['description'] or '')")
```
