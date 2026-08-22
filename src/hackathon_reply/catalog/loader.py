"""Catalog normalization at the boundary of the counting pipeline."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Sequence

from hackathon_reply.contracts.domain import CatalogEntry


class CatalogError(ValueError):
    """Raised when a catalog cannot be read or has no usable entries."""


@dataclass
class _NormalizedRow:
    length_mm: Decimal
    width_mm: Decimal
    height_mm: Decimal
    categories: list[str]


def parse_decimal(value: str | int | float | Decimal) -> Decimal:
    """Parse a finite positive dimension, accepting a comma decimal separator.

    Catalogs encountered at the boundary use either semicolon-delimited rows
    with values such as ``95,50`` or comma-delimited rows where that value was
    split into two CSV fields.  The latter is normalized by ``_row_values``.
    """

    if isinstance(value, Decimal):
        number = value
    else:
        text = str(value).strip().replace("\u00a0", "")
        if not text:
            raise CatalogError("dimension is empty")
        if "," in text and "." in text:
            # The last separator is the decimal separator; the other one is
            # treated as a thousands separator.
            decimal_separator = "," if text.rfind(",") > text.rfind(".") else "."
            thousands_separator = "." if decimal_separator == "," else ","
            text = text.replace(thousands_separator, "").replace(decimal_separator, ".")
        elif "," in text:
            text = text.replace(",", ".")
        try:
            number = Decimal(text)
        except InvalidOperation as exc:
            raise CatalogError(f"invalid decimal: {value!r}") from exc
    if not number.is_finite() or number <= 0:
        raise CatalogError("dimension must be finite and positive")
    return number


def _header_index(row: Sequence[str]) -> dict[str, int] | None:
    normalized = {cell.strip().lower().replace(" ", "_"): index for index, cell in enumerate(row)}
    aliases = {
        "length_mm": ("length_mm", "length", "l"),
        "width_mm": ("width_mm", "width", "w"),
        "height_mm": ("height_mm", "height", "h"),
        "category": ("category", "categories", "class", "label"),
    }
    if not all(any(alias in normalized for alias in names) for names in aliases.values()):
        return None
    return {key: next(normalized[alias] for alias in names if alias in normalized) for key, names in aliases.items()}


def _row_values(row: Sequence[str], header: dict[str, int] | None) -> tuple[str, str, str, str]:
    if header is not None:
        if len(row) == 5 and header == {"length_mm": 0, "width_mm": 1, "height_mm": 2, "category": 3}:
            return row[0], row[1], f"{row[2]},{row[3]}", row[4]
        try:
            return (
                row[header["length_mm"]],
                row[header["width_mm"]],
                row[header["height_mm"]],
                row[header["category"]],
            )
        except IndexError as exc:
            raise CatalogError("row does not contain the declared columns") from exc

    if len(row) == 4:
        return row[0], row[1], row[2], row[3]
    if len(row) == 5:
        # A comma-decimal height in a comma-delimited source is represented by
        # two fields.  This explicit rule is intentionally narrow and keeps
        # malformed rows visible instead of silently shifting dimensions.
        return row[0], row[1], f"{row[2]},{row[3]}", row[4]
    raise CatalogError("row must contain length, width, height, and category")


def _stable_id(length: Decimal, width: Decimal, height: Decimal) -> str:
    key = "|".join(str(value.normalize()) for value in (length, width, height))
    digest = hashlib.sha256(key.encode("ascii")).hexdigest()[:12]
    return f"catalog-{digest}"


def _categories(value: str) -> tuple[str, ...]:
    result: list[str] = []
    for category in value.replace("|", ";").split(";"):
        normalized = category.strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return tuple(result)


def load_catalog(path: str | Path) -> tuple[tuple[CatalogEntry, ...], tuple[str, ...]]:
    """Load normalized catalog entries and human-readable rejected-row reasons."""

    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise CatalogError(f"cannot read catalog: {source}") from exc
    nonempty = [line for line in text.splitlines() if line.strip()]
    if not nonempty:
        raise CatalogError("catalog is empty")
    delimiter = ";" if ";" in nonempty[0] and "," not in nonempty[0].split(";")[0] else ","
    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    header = _header_index(rows[0]) if rows else None
    start = 1 if header is not None else 0
    grouped: dict[tuple[Decimal, Decimal, Decimal], list[str]] = {}
    rejected: list[str] = []
    for line_number, row in enumerate(rows[start:], start=start + 1):
        if not row or not any(cell.strip() for cell in row):
            continue
        try:
            length_text, width_text, height_text, category_text = _row_values(row, header)
            dimensions = (parse_decimal(length_text), parse_decimal(width_text), parse_decimal(height_text))
            categories = _categories(category_text)
            grouped.setdefault(dimensions, [])
            for category in categories:
                if category not in grouped[dimensions]:
                    grouped[dimensions].append(category)
        except (CatalogError, IndexError, TypeError) as exc:
            rejected.append(f"line {line_number}: {exc}")

    entries: list[CatalogEntry] = []
    for dimensions, category_values in grouped.items():
        entries.append(
            CatalogEntry(
                catalog_id=_stable_id(*dimensions),
                length_mm=float(dimensions[0]),
                width_mm=float(dimensions[1]),
                height_mm=float(dimensions[2]),
                categories=tuple(category_values),
            )
        )
    entries.sort(key=lambda entry: (entry.length_mm, entry.width_mm, entry.height_mm, entry.catalog_id))
    if not entries:
        raise CatalogError("catalog contains no valid positive-dimension rows")
    return tuple(entries), tuple(rejected)


def normalize_entries(entries: Iterable[CatalogEntry]) -> tuple[CatalogEntry, ...]:
    """Collapse exact dimensions for callers that already have domain entries."""

    grouped: dict[tuple[float, float, float], list[str]] = {}
    for entry in entries:
        key = (entry.length_mm, entry.width_mm, entry.height_mm)
        categories = grouped.setdefault(key, [])
        for category in entry.categories:
            if category not in categories:
                categories.append(category)
    return tuple(
        CatalogEntry(
            _stable_id(Decimal(str(key[0])), Decimal(str(key[1])), Decimal(str(key[2]))),
            *key,
            tuple(categories),
        )
        for key, categories in sorted(grouped.items())
    )
