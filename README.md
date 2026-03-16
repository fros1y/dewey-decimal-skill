# Dewey Decimal Skill

A Claude agent to organize ebooks by the [Dewey Decimal](https://en.wikipedia.org/wiki/Dewey_decimal_classification) system with OCD renaming rules through three distinct Skills. Codex Skills are brand new; supporting Codex would likely require some rework. See https://developers.openai.com/codex/skills for adapting these skills to Codex's format.

| skill                | description                                                             |
|:---------------------|:------------------------------------------------------------------------|
| metadata-extraction  | unzips .epub files and inspects metadata for author, contributors, year |
| filename-formatting  | OCD filename rules for translators, edition, ancient authors, etc.      |
| dewey-classification | organizes files by inferring Dewey Decimal codes from OCLC index        |

## Setup

Clone this repository into `~/.claude`:

```bash
git clone https://github.com/fros1y/dewey-decimal-skill ~/.claude
```

> [!NOTE]
> If you already have files in `~/.claude`, copy the subdirectories instead:
> ```bash
> git clone https://github.com/fros1y/dewey-decimal-skill /tmp/dewey-decimal-skill
> cp -r /tmp/dewey-decimal-skill/.claude/. ~/.claude/
> ```

That's it. No install step required. The agent uses `~/Downloads` as the default source directory and `~/Books` as the default library directory. You can override either at any time by mentioning the path in your instruction (see [Usage](#usage)).

## Usage

Run the agent:
```bash
claude --agent rename-books
```

The agent will process ebooks from `~/Downloads` and move them into `~/Books/` by default.

You can specify different paths directly in your instruction:

```
catalog books from /mnt/usb/books into ~/Library
process ~/Downloads/novel.epub
```

For single-file processing, specify the file path. For batch processing, point it at a directory.

### History File

The agent stores a history file documenting the before and after filenames, paths, and hash of each book it processes at `<library directory>/renames.jsonl`.

### Regenerating `data/codes.md`

The committed `.claude/data/codes.md` is a static snapshot of the DDC third summary. If you want to rebuild it from source:

```bash
pip install uv
uv run python main.py > .claude/data/codes.md
```

The Classification codes are indexed and cross-compared by these sources:
- `lib/illinois.py` - https://www.library.illinois.edu/infosci/research/guides/dewey/
- `lib/oclc.py` - https://www.oclc.org/content/dam/oclc/dewey/ddc23-summaries.pdf

These are orchestrated together by `main.py` to create `data/codes.md`, which is provided in this repo.

> [!NOTE]
> DDC is proprietary and maintained by OCLC. [OpenLibrary](https://openlibrary.org/)
> exposes `dewey_decimal_class` in its Books API, but coverage appears uneven; I couldn’t find
> a public, comprehensive ISBN↔DDC mapping. [WorldCat](https://www.worldcat.org/) doesn’t
> provide a free bulk ISBN <-> DDC mapping.

Having already learned the topology of DDC codes with respect to library shelving, categorizing by [Library of Congress](https://www.loc.gov/standards) coding is unnatural to me, as much as I would prefer myself and all libraries to adopt it.

## License

- Code - [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html)
- Text - [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

