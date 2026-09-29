"""Unified card search services for Pokemon (EN/TW/JP) and Yu-Gi-Oh."""

import json
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

import requests

from card_schema import normalize_card
from official_pokemon import OfficialPokemonScraper


logger = logging.getLogger(__name__)
TIMEOUT = 15
ROOT = Path(__file__).resolve().parent
EN_CACHE = ROOT / "data" / "pokemon_en.json"
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def safe_request(url: str, *, params=None, timeout: int = TIMEOUT, attempts: int = 2) -> Optional[requests.Response]:
    response = None
    for attempt in range(max(1, attempts)):
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            if response.status_code not in RETRYABLE_STATUSES:
                return response
            logger.warning(
                "Card API returned HTTP %s for %s (attempt %s/%s)",
                response.status_code, response.url, attempt + 1, attempts,
            )
        except requests.RequestException as exc:
            logger.warning(
                "Card API request failed for %s (attempt %s/%s): %s",
                url, attempt + 1, attempts, exc,
            )
        if attempt + 1 < attempts:
            time.sleep(0.4 * (attempt + 1))
    return response


def _result(cards: List[Dict], total: int, page: int, limit: int) -> Dict:
    return {
        "cards": cards,
        "total": total,
        "pages": math.ceil(total / limit) if total else 0,
        "current_page": page,
    }


def _load_english_cache() -> List[Dict]:
    try:
        payload = json.loads(EN_CACHE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    return [normalize_card(card, "pokemon") for card in payload if isinstance(card, dict)]


def _save_english_cache(cards: List[Dict]) -> None:
    if not cards:
        return
    merged = {card["id"]: card for card in _load_english_cache() if card.get("id")}
    merged.update({card["id"]: card for card in cards if card.get("id")})
    EN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    temporary = EN_CACHE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(list(merged.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(EN_CACHE)


def _search_english_cache(keyword: str, limit: int, page: int) -> Dict:
    term = keyword.casefold()
    cards = [card for card in _load_english_cache() if term in card["name"].casefold()]
    start = (page - 1) * limit
    return _result(cards[start:start + limit], len(cards), page, limit)


def _normalize_tcgdex_card(raw: Dict) -> Dict:
    set_info = raw.get("set") or {}
    image = str(raw.get("image") or "").rstrip("/")
    types = raw.get("types") or []
    attacks = raw.get("attacks") or []
    return normalize_card({
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "hp": raw.get("hp", 0),
        "type": types[0] if types else "未標示",
        "rarity": raw.get("rarity") or "未標示",
        "series": set_info.get("name") or "未標示",
        "price": "-",
        "image_url": f"{image}/high.webp" if image else "",
        "number": raw.get("localId", ""),
        "description": raw.get("description") or "",
        "skills": [
            {
                "name": attack.get("name", ""),
                "damage": attack.get("damage", ""),
                "effect": attack.get("effect", ""),
            }
            for attack in attacks
        ],
    }, "pokemon")


def _get_tcgdex_cards(keyword: str, limit: int, page: int) -> Optional[Dict]:
    endpoint = "https://api.tcgdex.net/v2/en/cards"
    response = safe_request(
        endpoint,
        params={"name": keyword, "category": "Pokemon"},
        timeout=20,
    )
    if response is None or response.status_code != 200:
        return None
    try:
        briefs = response.json()
    except requests.JSONDecodeError:
        return None
    if not isinstance(briefs, list):
        return None

    # TCGdex keeps a few catalogue placeholders without artwork. They cannot be
    # rendered by this application, so exclude them before paginating.
    briefs = [brief for brief in briefs if brief.get("id") and brief.get("image")]
    total = len(briefs)
    start = (page - 1) * limit
    selected = briefs[start:start + limit]

    def fetch_detail(brief):
        card_id = brief.get("id")
        if not card_id:
            return None
        detail = safe_request(f"{endpoint}/{card_id}", timeout=20)
        if detail is None or detail.status_code != 200:
            return None
        try:
            payload = detail.json()
            if not payload.get("image") and brief.get("image"):
                payload["image"] = brief["image"]
            card = _normalize_tcgdex_card(payload)
            if not card["image_url"] or card["hp"] <= 0 or card["type"] == "未標示":
                return None
            return card
        except (requests.JSONDecodeError, TypeError, ValueError):
            return None

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(selected)))) as executor:
        cards = [card for card in executor.map(fetch_detail, selected) if card]
    _save_english_cache(cards)
    return _result(cards, total, page, limit)


def get_pokemon_tcg_cards(keyword: str, limit: int = 20, page: int = 1) -> Dict:
    """Search the international English Pokemon TCG API."""
    response = safe_request(
        "https://api.pokemontcg.io/v2/cards",
        params={"q": f'name:"{keyword}"', "page": page, "pageSize": limit},
    )
    if response is None or response.status_code != 200:
        logger.warning("Pokemon TCG API unavailable; using TCGdex fallback for %r", keyword)
        fallback = _get_tcgdex_cards(keyword, limit, page)
        return fallback if fallback is not None else _search_english_cache(keyword, limit, page)

    try:
        payload = response.json()
    except requests.JSONDecodeError:
        logger.warning("Pokemon TCG API returned invalid JSON; using TCGdex fallback")
        fallback = _get_tcgdex_cards(keyword, limit, page)
        return fallback if fallback is not None else _search_english_cache(keyword, limit, page)
    cards = []
    for raw in payload.get("data", []):
        images = raw.get("images") or {}
        set_info = raw.get("set") or {}
        cards.append(normalize_card({
            "id": raw.get("id", ""),
            "name": raw.get("name", ""),
            "hp": raw.get("hp", 0),
            "type": (raw.get("types") or ["未標示"])[0],
            "rarity": raw.get("rarity") or "未標示",
            "series": set_info.get("name") or "未標示",
            "price": "-",
            "image_url": images.get("large") or images.get("small") or "",
            "number": raw.get("number", ""),
            "description": f"{set_info.get('name', '')} - {raw.get('rarity', '')}".strip(" -"),
            "skills": [
                {"name": attack.get("name", ""), "damage": attack.get("damage", ""), "effect": attack.get("text", "")}
                for attack in raw.get("attacks", [])
            ],
        }, "pokemon"))
    if not cards:
        fallback = _get_tcgdex_cards(keyword, limit, page)
        return fallback if fallback is not None else _search_english_cache(keyword, limit, page)
    total = int(payload.get("totalCount", len(cards)))
    _save_english_cache(cards)
    return _result(cards, total, page, limit)


def get_yugioh_cards(keyword: str, limit: int = 20, page: int = 1) -> Dict:
    """Search YGOPRODeck and normalize its monster/spell/trap payloads."""
    response = None
    for parameter in ("name", "fname"):
        candidate = safe_request(
            "https://db.ygoprodeck.com/api/v7/cardinfo.php",
            params={parameter: keyword},
        )
        if candidate is not None and candidate.status_code == 200:
            response = candidate
            break
    if response is None:
        return _result([], 0, page, limit)

    raw_cards = response.json().get("data", [])
    total = len(raw_cards)
    offset = (page - 1) * limit
    cards = []
    for raw in raw_cards[offset:offset + limit]:
        images = raw.get("card_images") or [{}]
        sets = raw.get("card_sets") or []
        first_set = sets[0] if sets else {}
        prices = raw.get("card_prices") or [{}]
        cards.append(normalize_card({
            "id": raw.get("id", ""),
            "name": raw.get("name", ""),
            "hp": 0,
            "type": raw.get("attribute") or raw.get("race") or raw.get("type") or "未標示",
            "rarity": first_set.get("set_rarity_code") or first_set.get("set_rarity") or "未標示",
            "series": first_set.get("set_name") or "未標示",
            "price": prices[0].get("tcgplayer_price") or "-",
            "image_url": images[0].get("image_url") or "",
            "description": raw.get("desc", ""),
            "stats": {
                "card_type": raw.get("type", ""), "attribute": raw.get("attribute", ""),
                "level": raw.get("level", 0), "atk": raw.get("atk", 0),
                "def": raw.get("def", 0), "race": raw.get("race", ""),
            },
        }, "yugioh"))
    return _result(cards, total, page, limit)


def _paginate(cards: List[Dict], total: int, limit: int, page: int) -> Dict:
    """Build pagination metadata from the source total, not the current page size."""
    return _result(cards, total, page, limit)


def get_taiwan_pokemon_cards(keyword: str, limit: int = 20, page: int = 1) -> Dict:
    cards, total = OfficialPokemonScraper().search_taiwan_page(keyword, limit=limit, page=page)
    return _paginate(cards, total, limit, page)


def get_japan_pokemon_cards(keyword: str, limit: int = 20, page: int = 1) -> Dict:
    cards, total = OfficialPokemonScraper().search_japan_page(keyword, limit=limit, page=page)
    return _paginate(cards, total, limit, page)


SOURCE_HANDLERS = {
    "pokemon": get_pokemon_tcg_cards,
    "pokemon-en": get_pokemon_tcg_cards,
    "tw-pokemon": get_taiwan_pokemon_cards,
    "pokemon-jp": get_japan_pokemon_cards,
    "yugioh": get_yugioh_cards,
}


def search_source(source: str, keyword: str, limit: int = 20, page: int = 1) -> Dict:
    handler = SOURCE_HANDLERS.get(source)
    if not handler:
        raise ValueError(f"Unsupported card source: {source}")
    return handler(keyword, limit, page)


def search_all_cards_paginated(keyword: str, limit: int = 20, page: int = 1) -> Dict[str, Dict]:
    sources = ("pokemon", "tw-pokemon", "pokemon-jp", "yugioh")
    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        futures = {source: executor.submit(search_source, source, keyword, limit, page) for source in sources}
        return {source: future.result() for source, future in futures.items()}


def get_all_card_sources(keyword: str) -> Dict[str, List[Dict]]:
    results = search_all_cards_paginated(keyword, limit=5, page=1)
    return {source: result.get("cards", []) for source, result in results.items()}
