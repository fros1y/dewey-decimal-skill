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
7. User input (for disambiguation only)

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

## Missing Data

When metadata genuinely unavailable:
- No author: Ask user
- No year: Ask user for "publication year of this edition"
- Ambiguous title: Ask user
- No translator but work is translated: Ask user or look up by ISBN/publisher

Do not guess. Do not proceed without author and title.
