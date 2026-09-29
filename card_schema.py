"""Canonical card payload helpers shared by scrapers, APIs, CV, and UI."""

import re
from typing import Any, Dict


REQUIRED_CARD_FIELDS = (
    "id",
    "name",
    "hp",
    "type",
    "rarity",
    "series",
    "price",
    "image_url",
)


def parse_hp(value: Any) -> int:
    """Return a numeric HP value. Non-Pokemon cards use 0."""
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else 0


def clean_card_text(value: Any, fallback: str = "未標示") -> str:
    """Normalize empty API placeholders so the UI never leaks N/A-like values."""
    text = str(value or "").strip()
    if text.casefold() in {"", "n/a", "na", "none", "null", "unknown", "-"}:
        return fallback
    return text


def normalize_card(card: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Normalize every card source to the public API contract."""
    stats = card.get("stats") if isinstance(card.get("stats"), dict) else {}
    types = stats.get("types") if isinstance(stats.get("types"), list) else []
    series = card.get("series")
    if isinstance(series, list):
        series = series[0].get("name", "") if series else ""

    normalized = {
        **card,
        "id": str(card.get("id") or card.get("number") or ""),
        "name": str(card.get("name") or card.get("title") or "未命名卡牌").strip(),
        "hp": parse_hp(card.get("hp", stats.get("hp"))),
        "type": clean_card_text(
            card.get("type")
            or stats.get("attribute")
            or (types[0] if types else "")
            or stats.get("type")
        ),
        "rarity": clean_card_text(card.get("rarity") or stats.get("rarity")),
        "series": clean_card_text(series or stats.get("set")),
        "price": card.get("price") if card.get("price") not in (None, "") else "-",
        "image_url": str(
            card.get("image_url") or card.get("img_large") or card.get("img_url") or ""
        ).strip(),
        "source": source,
    }

    # Compatibility aliases for older clients. Canonical fields above are authoritative.
    normalized["title"] = normalized["name"]
    normalized["img_url"] = normalized["image_url"]
    normalized["img_large"] = normalized["image_url"]
    normalized["stats"] = {
        **stats,
        "hp": normalized["hp"],
        "type": normalized["type"],
        "types": types or [normalized["type"]],
        "rarity": normalized["rarity"],
        "set": normalized["series"],
    }
    return normalized


def has_required_fields(card: Dict[str, Any]) -> bool:
    return all(field in card for field in REQUIRED_CARD_FIELDS)
