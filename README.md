# Dewey Decimal Skill

Organize ebooks by the [Dewey Decimal](https://en.wikipedia.org/wiki/Dewey_decimal_classification) system with strict renaming rules. Four standalone skills that can be installed individually or together.

| skill                | description                                                             |
|:---------------------|:------------------------------------------------------------------------|
| metadata-extraction  | unzips .epub files and inspects metadata for author, contributors, year |
| filename-formatting  | OCD filename rules for translators, edition, ancient authors, etc.      |
| dewey-classification | organizes files by inferring Dewey Decimal codes from OCLC index        |
| rename-books         | orchestrates the above three skills into a full cataloging workflow      |

## Installation

### VS Code / Copilot

Install individual skills from the repo using their skill paths:

```
skills/dewey-classification/SKILL.md
skills/metadata-extraction/SKILL.md
skills/filename-formatting/SKILL.md
skills/rename-books/SKILL.md
```

Or install all skills by pointing your agent at this repository.

### Claude Code

Copy the skill directories into your global config:

```bash
git clone https://github.com/fros1y/dewey-decimal-skill /tmp/dewey-decimal-skill
cp -r /tmp/dewey-decimal-skill/skills/* ~/.claude/skills/
```

### Manual

Copy any skill folder from `skills/` into your agent's skill directory (e.g. `~/.agents/skills/`).

## Usage

The **rename-books** skill processes ebooks from `~/Downloads` and catalogs them into `~/Books/` by default. You can override either path in your instruction:

```
catalog books from /mnt/usb/books into ~/Library
process ~/Downloads/novel.epub
```

For single-file processing, specify the file path. For batch processing, point it at a directory.

### History File

The skill logs every operation to `<library directory>/renames.jsonl`, documenting the before/after filenames, paths, and SHA-256 hash of each book processed.

### Regenerating `codes.md`

The committed `skills/dewey-classification/codes.md` is a static snapshot of the DDC third summary. To rebuild from source:

```bash
pip install uv
uv run python main.py > skills/dewey-classification/codes.md
```

The classification codes are indexed and cross-compared by these sources:
- `lib/illinois.py` - https://www.library.illinois.edu/infosci/research/guides/dewey/
- `lib/oclc.py` - https://www.oclc.org/content/dam/oclc/dewey/ddc23-summaries.pdf

These are orchestrated together by `main.py` to create `codes.md`, which is provided in this repo.

> [!NOTE]
> DDC is proprietary and maintained by OCLC. [OpenLibrary](https://openlibrary.org/)
> exposes `dewey_decimal_class` in its Books API, but coverage appears uneven; I couldn't find
> a public, comprehensive ISBN↔DDC mapping. [WorldCat](https://www.worldcat.org/) doesn't
> provide a free bulk ISBN <-> DDC mapping.

Having already learned the topology of DDC codes with respect to library shelving, categorizing by [Library of Congress](https://www.loc.gov/standards) coding is unnatural to me, as much as I would prefer myself and all libraries to adopt it.

## License

- Code - [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html)
- Text - [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

