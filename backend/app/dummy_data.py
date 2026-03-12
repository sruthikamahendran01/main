import csv
import json
from functools import lru_cache
from pathlib import Path

from .models import Product

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "products.tsv"


def _safe_load_json(value: str) -> list | dict:
    if not value or value == "null":
        return []
    return json.loads(value)


def _parse_bool(value: str) -> bool:
    return value.strip().upper() == "TRUE"


def _parse_price(row: dict[str, str]) -> float:
    raw = row.get("final_price") or row.get("unit_price") or "0"
    return float(raw)


def _build_tags(row: dict[str, str]) -> tuple[str, ...]:
    tags: list[str] = []
    for field in ("category_name", "root_category_name", "brand", "seller"):
        value = row.get(field, "").strip()
        if value:
            tags.append(value)

    for color in _safe_load_json(row.get("colors", "")):
        if color:
            tags.append(str(color))

    for spec in _safe_load_json(row.get("specifications", "")):
        name = str(spec.get("name", "")).strip()
        value = str(spec.get("value", "")).strip()
        if name:
            tags.append(name)
        if value:
            tags.append(value)

    for attribute in _safe_load_json(row.get("other_attributes", "")):
        name = str(attribute.get("name", "")).strip()
        value = str(attribute.get("value", "")).strip()
        if name:
            tags.append(name)
        if value:
            tags.append(value)

    deduped: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        lowered = tag.lower()
        if lowered not in seen:
            deduped.append(tag)
            seen.add(lowered)
    return tuple(deduped)


def _row_to_product(row: dict[str, str]) -> Product:
    return Product(
        product_id=row["product_id"].strip(),
        title=row["product_name"].strip(),
        category=row["category_name"].strip(),
        root_category=row["root_category_name"].strip(),
        brand=row["brand"].strip(),
        price=_parse_price(row),
        currency=row.get("currency", "USD").strip() or "USD",
        description=row["description"].strip(),
        tags=_build_tags(row),
        rating=float(row["rating"]) if row.get("rating") else None,
        review_count=int(float(row["review_count"])) if row.get("review_count") else None,
        image_url=row.get("main_image", "").strip() or None,
        seller=row.get("seller", "").strip() or None,
        available_for_delivery=_parse_bool(row.get("available_for_delivery", "")),
        available_for_pickup=_parse_bool(row.get("available_for_pickup", "")),
    )


@lru_cache(maxsize=1)
def load_products() -> list[Product]:
    with DATA_FILE.open("r", encoding="utf-8", newline="") as data_file:
        reader = csv.DictReader(data_file, delimiter="\t")
        return [_row_to_product(row) for row in reader]


PRODUCTS = load_products()
