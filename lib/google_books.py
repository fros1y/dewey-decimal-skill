from __future__ import annotations

"""Fetch book metadata from the Google Books API.

Usage:
    python lib/google_books.py --isbn 9780735619678
    python lib/google_books.py --title "Foundation" --author "Asimov"

Outputs a single JSON object with the following keys (all may be null if not
available from the API):

    title       – book title (subtitle appended after " - " when present)
    authors     – list of author name strings
    series      – series name string, or null
    series_index – series volume/index string, or null
    tags        – list of category/genre strings
    rating      – float 0–5, or null
    description – synopsis string, or null
    isbn_13     – ISBN-13 string, or null
    isbn_10     – ISBN-10 string, or null
    published_date – publication date string (YYYY or YYYY-MM-DD), or null

The technique mirrors Calibre's Google Books metadata plugin, which queries
https://www.googleapis.com/books/v1/volumes and parses the volumeInfo object.
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

import requests

API_URL = "https://www.googleapis.com/books/v1/volumes"
REQUEST_TIMEOUT = 15


def _build_query(isbn: Optional[str], title: Optional[str], author: Optional[str]) -> str:
    if isbn:
        return f"isbn:{isbn}"
    parts: List[str] = []
    if title:
        parts.append(f"intitle:{title}")
    if author:
        parts.append(f"inauthor:{author}")
    return " ".join(parts)


def _extract_isbn(identifiers: List[Dict[str, str]], id_type: str) -> Optional[str]:
    for entry in identifiers:
        if entry.get("type") == id_type:
            return entry.get("identifier")
    return None


def fetch_metadata(
    isbn: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Query the Google Books API and return a normalised metadata dict.

    Returns None when no results are found or the query cannot be formed.
    Raises ``requests.HTTPError`` on non-2xx responses.
    """
    query = _build_query(isbn, title, author)
    if not query:
        return None

    response = requests.get(
        API_URL,
        params={"q": query, "maxResults": 1},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    items = data.get("items")
    if not items:
        return None

    volume_info: Dict[str, Any] = items[0].get("volumeInfo", {})

    # Title: combine main title and subtitle (Calibre joins with " - ")
    raw_title: Optional[str] = volume_info.get("title")
    subtitle: Optional[str] = volume_info.get("subtitle")
    if raw_title and subtitle:
        combined_title = f"{raw_title} - {subtitle}"
    else:
        combined_title = raw_title

    # Series: present in volumeInfo.seriesInfo when the book belongs to a series.
    # Use ``or None`` to coerce empty strings returned by the API to None.
    series_info: Dict[str, Any] = volume_info.get("seriesInfo") or {}
    series_name: Optional[str] = series_info.get("shortSeriesBookTitle") or None
    series_index: Optional[str] = series_info.get("bookDisplayNumber") or None

    # Industry identifiers (ISBN-10 / ISBN-13)
    identifiers: List[Dict[str, str]] = volume_info.get("industryIdentifiers") or []
    isbn_13 = _extract_isbn(identifiers, "ISBN_13")
    isbn_10 = _extract_isbn(identifiers, "ISBN_10")

    # Rating: Google Books averageRating is on a 0–5 scale
    average_rating: Optional[float] = volume_info.get("averageRating")

    return {
        "title": combined_title,
        "authors": volume_info.get("authors") or [],
        "series": series_name,
        "series_index": series_index,
        "tags": volume_info.get("categories") or [],
        "rating": average_rating,
        "description": volume_info.get("description") or None,
        "isbn_13": isbn_13,
        "isbn_10": isbn_10,
        "published_date": volume_info.get("publishedDate") or None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch book metadata from the Google Books API (Calibre technique)."
    )
    parser.add_argument("--isbn", help="ISBN-10 or ISBN-13 to look up")
    parser.add_argument("--title", help="Book title for keyword search")
    parser.add_argument("--author", help="Author name for keyword search")
    args = parser.parse_args()

    if not args.isbn and not args.title:
        parser.error("Provide --isbn or --title (optionally with --author)")

    result = fetch_metadata(isbn=args.isbn, title=args.title, author=args.author)
    if result is None:
        json.dump(None, sys.stdout)
        print()
        sys.exit(1)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
