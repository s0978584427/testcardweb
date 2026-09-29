"""Unified card search services for Pokemon (EN/TW/JP) and Yu-Gi-Oh."""

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import requests

from card_schema import normalize_card
from official_pokemon import OfficialPokemonScraper


logger = logging.getLogger(__name__)
TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def safe_request(url: str, *, params=None, timeout: int = TIMEOUT) -> Optional[requests.Response]:
    try:
        return requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    except requests.RequestException as exc:
        logger.error("Card API request failed: %s", exc)
        return None


def _result(cards: List[Dict], total: int, page: int, limit: int) -> Dict:
    return {
        "cards": cards,
        "total": total,
        "pages": math.ceil(total / limit) if total else 0,
        "current_page": page,
    }


def get_pokemon_tcg_cards(keyword: str, limit: int = 20, page: int = 1) -> Dict:
    """Search the international English Pokemon TCG API."""
    response = safe_request(
        "https://api.pokemontcg.io/v2/cards",
        params={"q": f'name:"{keyword}"', "page": page, "pageSize": limit},
    )
    if response is None or response.status_code != 200:
        return _result([], 0, page, limit)

    payload = response.json()
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
    total = int(payload.get("totalCount", len(cards)))
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
