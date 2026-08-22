"""Catalog ingestion with locale normalization, stable IDs, and auditable rejects."""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CatalogEntry:
    catalog_id: str
    length_mm: float
    width_mm: float
    height_mm: float
    categories: tuple[str, ...]
    source_rows: tuple[int, ...]

    @property
    def volume_l(self) -> float:
        return self.length_mm * self.width_mm * self.height_mm / 1_000_000


@dataclass(frozen=True)
class RejectedCatalogRow:
    row_number: int
    reason: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class CatalogLoadResult:
    entries: tuple[CatalogEntry, ...]
    rejected_rows: tuple[RejectedCatalogRow, ...]


class CatalogLoader:
    @staticmethod
    def from_csv_path(path: str | Path) -> CatalogLoadResult:
        return CatalogLoader.from_csv_text(Path(path).read_text(encoding="utf-8"))

    @staticmethod
    def from_csv_text(text: str) -> CatalogLoadResult:
        if not text.strip():
            raise ValueError("catalog CSV is empty")
        delimiter = _detect_delimiter(text)
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError("catalog CSV requires a header")
        fields = {_normalize_header(name): name for name in reader.fieldnames if name is not None}
        length_field = _find_field(fields, "length_mm", "length", "l", "comprimento")
        width_field = _find_field(fields, "width_mm", "width", "w", "largura")
        height_field = _find_field(fields, "height_mm", "height", "h", "altura")
        category_field = _find_field(fields, "category", "categories", "categoria", required=False)
        if not all((length_field, width_field, height_field)):
            raise ValueError("catalog CSV must identify length, width, and height fields")

        grouped: dict[tuple[float, float, float], dict[str, Any]] = {}
        rejected: list[RejectedCatalogRow] = []
        for row_number, row in enumerate(reader, start=2):
            try:
                dimensions = (
                    _parse_locale_decimal(row.get(length_field, "")),
                    _parse_locale_decimal(row.get(width_field, "")),
                    _parse_locale_decimal(row.get(height_field, "")),
                )
                if any(value <= 0 for value in dimensions):
                    raise ValueError("dimensions must be positive")
            except ValueError as error:
                rejected.append(RejectedCatalogRow(row_number, str(error), dict(row)))
                continue
            category = (row.get(category_field, "") if category_field else "").strip()
            group = grouped.setdefault(dimensions, {"categories": set(), "rows": []})
            if category:
                group["categories"].add(category)
            group["rows"].append(row_number)

        entries: list[CatalogEntry] = []
        for dimensions, group in grouped.items():
            key = "|".join(f"{value:.6f}" for value in dimensions)
            catalog_id = "catalog-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
            entries.append(
                CatalogEntry(
                    catalog_id=catalog_id,
                    length_mm=dimensions[0],
                    width_mm=dimensions[1],
                    height_mm=dimensions[2],
                    categories=tuple(sorted(group["categories"])),
                    source_rows=tuple(group["rows"]),
                )
            )
        return CatalogLoadResult(tuple(entries), tuple(rejected))


def _detect_delimiter(text: str) -> str:
    try:
        return csv.Sniffer().sniff(text[:2048], delimiters=";,\t").delimiter
    except csv.Error:
        return ";" if ";" in text.splitlines()[0] else ","


def _normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _find_field(fields: dict[str, str], *names: str, required: bool = True) -> str | None:
    for name in names:
        if name in fields:
            return fields[name]
    if required:
        return None
    return None


def _parse_locale_decimal(raw: Any) -> float:
    value = str(raw).strip().replace(" ", "")
    if not value:
        raise ValueError("missing dimension")
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    else:
        value = value.replace(",", ".")
    try:
        result = float(value)
    except ValueError as error:
        raise ValueError("invalid decimal") from error
    if result != result or result in {float("inf"), float("-inf")}:
        raise ValueError("dimension must be finite")
    return result
