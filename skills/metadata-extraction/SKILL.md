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
4. Google Books online lookup (to enrich missing or incomplete fields)
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
