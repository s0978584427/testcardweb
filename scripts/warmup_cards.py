#!/usr/bin/env python3
"""Expand official TW/JP Pokemon caches and persist their ORB features."""

import argparse
import json
import logging
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from card_schema import REQUIRED_CARD_FIELDS, normalize_card  # noqa: E402
from official_pokemon import JP_CACHE, TW_CACHE, OfficialPokemonScraper  # noqa: E402


TW_KEYWORDS = (
    "皮卡丘", "噴火龍", "超夢", "夢幻", "伊布", "妙蛙種子", "小火龍", "傑尼龜",
    "耿鬼", "路卡利歐", "烈空坐", "快龍", "沙奈朵", "甲賀忍蛙", "暴鯉龍",
    "卡比獸", "拉帝亞斯", "拉帝歐斯", "蒼響", "密勒頓",
)
JP_KEYWORDS = (
    "ピカチュウ", "リザードン", "ミュウツー", "ミュウ", "イーブイ", "フシギダネ",
    "ヒトカゲ", "ゼニガメ", "ゲンガー", "ルカリオ", "レックウザ", "カイリュー",
    "サーナイト", "ゲッコウガ", "ギャラドス", "カビゴン", "ラティアス",
    "ラティオス", "ザシアン", "ミライドン",
)
PLACEHOLDERS = {"", "未標示", "n/a", "na", "none", "null", "unknown", "-"}


def console(message):
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe = str(message).encode(encoding, errors="backslashreplace").decode(encoding)
    print(safe, flush=True)


def load_valid_cards(path, source):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []

    cards = {}
    for raw in payload if isinstance(payload, list) else []:
        card = normalize_card(raw, source)
        has_fields = all(field in card for field in REQUIRED_CARD_FIELDS)
        has_identity = card["id"] and card["name"] and card["image_url"]
        is_pokemon = card["hp"] > 0 and str(card["type"]).casefold() not in PLACEHOLDERS
        if has_fields and has_identity and is_pokemon:
            cards[card["id"]] = card
    return list(cards.values())


def save_cards(path, cards):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def source_count(path, source):
    return len(load_valid_cards(path, source))


def fetch_until(scraper, source, target_count, batch_size, delay):
    if source == "tw-pokemon":
        path, keywords, search = TW_CACHE, TW_KEYWORDS, scraper.search_taiwan_page
    else:
        path, keywords, search = JP_CACHE, JP_KEYWORDS, scraper.search_japan_page

    current = source_count(path, source)
    console(f"[{source}] starting with {current} valid cards; target={target_count}")
    jobs = [(keyword, page) for page in (1, 2, 3) for keyword in keywords]
    stagnant_jobs = 0

    for keyword, page in jobs:
        if current >= target_count:
            break
        request_limit = min(batch_size, target_count - current)
        before = current
        try:
            cards, total = search(keyword, limit=request_limit, page=page)
            current = source_count(path, source)
            added = current - before
            console(
                f"[{source}] keyword={keyword!r} page={page} "
                f"received={len(cards)} source_total={total} added={added} cached={current}"
            )
        except Exception as exc:
            logging.exception("Warmup query failed for %s/%s", source, keyword)
            console(f"[{source}] query failed: {exc}")
            added = 0

        stagnant_jobs = stagnant_jobs + 1 if added <= 0 else 0
        if stagnant_jobs >= 12:
            console(f"[{source}] stopping after {stagnant_jobs} consecutive queries without new cards")
            break
        time.sleep(delay)
    return current


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=360, help="Combined target, from 300 to 500")
    parser.add_argument("--batch-size", type=int, default=20, help="Cards requested per official query")
    parser.add_argument("--delay", type=float, default=0.25, help="Pause between official queries")
    parser.add_argument("--skip-features", action="store_true", help="Only refresh JSON caches")
    return parser.parse_args()


def main():
    args = parse_args()
    if not 300 <= args.target <= 500:
        raise SystemExit("--target must be between 300 and 500")
    args.batch_size = min(40, max(1, args.batch_size))
    args.delay = max(0.0, args.delay)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    scraper = OfficialPokemonScraper(timeout=20)
    tw_target = round(args.target * 0.55)
    jp_target = args.target - tw_target

    tw_count = fetch_until(scraper, "tw-pokemon", tw_target, args.batch_size, args.delay)
    jp_count = fetch_until(scraper, "pokemon-jp", jp_target, args.batch_size, args.delay)

    # Normalize and atomically remove non-Pokemon results before feature generation.
    tw_cards = load_valid_cards(TW_CACHE, "tw-pokemon")
    jp_cards = load_valid_cards(JP_CACHE, "pokemon-jp")
    save_cards(TW_CACHE, tw_cards)
    save_cards(JP_CACHE, jp_cards)
    tw_count, jp_count = len(tw_cards), len(jp_cards)
    total = tw_count + jp_count
    console(f"[JSON READY] TW={tw_count} JP={jp_count} TOTAL={total}")

    if total < 300:
        raise SystemExit(f"Only {total} valid cards were collected; at least 300 are required")

    if not args.skip_features:
        from database import FEATURE_CACHE, initialize_online_features

        feature_count = initialize_online_features()
        console(f"[FEATURES READY] cards={feature_count} cache={FEATURE_CACHE}")
        if feature_count != total:
            raise SystemExit(
                f"Feature count mismatch: JSON has {total}, cache has {feature_count}"
            )

    if total < args.target:
        console(f"[WARNING] Requested {args.target}, but official searches yielded {total} valid cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
