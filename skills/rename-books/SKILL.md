---
name: rename-books
description: Process ebooks into a cataloged library. Extracts metadata, formats filenames, assigns Dewey categories, and moves files to the library directory. Supports EPUB, PDF, MOBI, AZW, LIT, and HTML formats. Use for batch processing new ebooks or correcting existing catalog entries.
---

# Rename Books

Process ebook files into a cataloged library collection.

## Execution Model

Execute all steps without requesting approval. Do not ask before running commands, reading files, listing directories, computing hashes, or logging operations. Only ask the user for input when metadata is genuinely missing or ambiguous (no author found, unclear Dewey category).

## Location Inference

Before running the workflow, determine the source and destination from the user's instruction.

### Source (input)

Look for an explicit path in the user's instruction:

- A path to a single file (e.g. `~/Downloads/book.epub`, `/tmp/novel.pdf`)
- A path to a directory (e.g. `from ~/Downloads`, `in /mnt/usb/books`)
- The word "arrivals" or "inbox" — treat as `~/Downloads`

Common patterns to detect:

| Instruction fragment | Source |
|----------------------|--------|
| "process /some/path/book.epub" | /some/path/book.epub (single file) |
| "catalog books from /some/dir" | /some/dir/ (directory) |
| "rename /some/dir" | /some/dir/ (directory) |
| "this file: /path/to/book.pdf" | /path/to/book.pdf (single file) |
| no path mentioned | ~/Downloads/ (default) |

### Destination (output)

Look for an explicit destination in the user's instruction:

- "into ~/Library", "to /mnt/storage/books", "destination /path"

| Instruction fragment | Destination |
|----------------------|-------------|
| "into /some/dir" | /some/dir/ |
| "to /some/dir" | /some/dir/ |
| "destination /some/dir" | /some/dir/ |
| no destination mentioned | ~/Books/ (default) |

Resolve `~` to the user's home directory. Convert all inferred paths to absolute paths before use.

## Workflow

### Single File

1. Infer source file and destination directory from user instruction (see Location Inference)
2. Extract metadata using the metadata-extraction skill
3. Format filename using the filename-formatting skill
4. Assign Dewey category using the dewey-classification skill
5. Compute SHA-256 hash: `sha256sum "$file" | cut -d' ' -f1`
6. Append to <destination>/renames.jsonl
7. Move file to destination

### Batch Processing

1. Infer source directory and destination directory from user instruction (see Location Inference)
2. List all EPUB/PDF/MOBI/AZW/LIT/HTML files in source directory
3. For each file, execute steps 2-5 (extract, format, classify, hash)
4. Log all operations to <destination>/renames.jsonl
5. Move all files

## Log Format

Append JSON lines to <destination>/renames.jsonl:

```json
{"hash":"sha256:...","modified":"2025-12-20T12:00:00Z","old_path":"<source>/...","new_path":"<destination>/Food & drink/Author, Name - Title (Year).epub"}
```

Use full absolute paths including category names (e.g., `Literature (Belles-lettres) & rhetoric/American poetry in English/`), not abbreviated codes.

## Constraints

- Source: inferred from user instruction, default ~/Downloads/
- Destination: inferred from user instruction, default ~/Books/[Dewey Category]/[filename]
- Required metadata: author, title, year
- Do not modify file contents
- Preserve file extension

---

## Audit Mode

Verify and correct existing library files. Invoke with: "audit my library" or "audit <library directory>"

### Workflow

1. Infer library directory from user instruction (see Location Inference); default ~/Books/
2. Build hash index from existing <library directory>/renames.jsonl
3. Scan all files in <library directory>/ recursively
4. For each file:
   a. Compute SHA-256 hash
   b. Check for duplicates (same hash, different path)
   c. Extract metadata from file
   d. Parse year from current filename
   e. Compare metadata year vs filename year
   f. If correction needed, rename in place and log

### Duplicate Detection

Before processing, build hash map from all files:

```bash
find <library directory> -type f \( -name "*.epub" -o -name "*.pdf" -o -name "*.mobi" -o -name "*.azw" -o -name "*.azw3" -o -name "*.lit" -o -name "*.html" -o -name "*.htm" -o -name "*.djvu" \) -exec sha256sum {} \;
```

Group by hash. Report duplicates:
```json
{"duplicate_group":"sha256:...","paths":["path1","path2"],"action":"review_needed"}
```

Do not auto-delete duplicates. Report for manual review.

### Year Correction Rules

Only correct year when ALL conditions met:
1. EPUB `<dc:date>` contains a valid year (1900 or later, not in the future)
2. The date is a publication date, not modification date (ignore `opf:event="modification"`)
3. Metadata year differs from filename year
4. Author and title from metadata match filename (same book, just wrong year)

If author/title mismatch: flag for review, do not auto-correct.

### Audit Log Format

```json
{"hash":"sha256:...","modified":"2025-12-20T12:00:00Z","old_path":"<library directory>/.../Book (2004).epub","new_path":"<library directory>/.../Book (2019).epub","audit":"year_correction","reason":"EPUB dc:date=2019, filename had 2004"}
```

Additional audit types:
- `year_correction`: Year updated from metadata
- `duplicate_found`: Hash matches another file
- `verified`: No changes needed, file correct

### Audit Output

After processing, report summary:
- Files scanned: N
- Verified correct: N
- Years corrected: N
- Duplicates found: N (list paths)
- Flagged for review: N (list with reasons)

---

## Reference Skills

This skill orchestrates three companion skills:

- **metadata-extraction** — extracts author, title, year from ebook files
- **filename-formatting** — formats filenames in citation style
- **dewey-classification** — assigns Dewey Decimal codes and shelf locations
