"""Official Taiwan and Japan Pokemon TCG scrapers with persistent JSON caches."""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from card_schema import normalize_card


logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TW_CACHE = DATA_DIR / "pokemon_tw.json"
JP_CACHE = DATA_DIR / "pokemon_jp.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,ja;q=0.8,en;q=0.7",
}

ENERGY_TYPES = {
    "Grass": "草",
    "Fire": "火",
    "Water": "水",
    "Lightning": "雷",
    "Psychic": "超",
    "Fighting": "鬥",
    "Darkness": "惡",
    "Metal": "鋼",
    "Dragon": "龍",
    "Colorless": "無色",
    "Fairy": "妖精",
    "electric": "雷",
    "lightning": "雷",
    "fire": "火",
    "water": "水",
    "grass": "草",
    "psychic": "超",
    "fighting": "鬥",
    "darkness": "惡",
    "metal": "鋼",
    "steel": "鋼",
    "dark": "惡",
    "dragon": "龍",
    "none": "無色",
    "colorless": "無色",
}

RARITY_NAMES = {
    "c": "C",
    "u": "U",
    "r": "R",
    "rr": "RR",
    "rrr": "RRR",
    "ar": "AR",
    "sar": "SAR",
    "sr": "SR",
    "ur": "UR",
    "chr": "CHR",
    "csr": "CSR",
    "ace": "ACE SPEC",
}


class OfficialPokemonScraper:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get_soup(self, url: str, **kwargs) -> BeautifulSoup:
        response = self.session.get(url, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    @staticmethod
    def _energy_from_image(src: str) -> str:
        key = Path((src or "").split("?")[0]).stem
        return ENERGY_TYPES.get(key, ENERGY_TYPES.get(key.lower(), "未標示"))

    @staticmethod
    def _rarity_from_soup(soup: BeautifulSoup) -> str:
        rarity_pattern = re.compile(r"(?:^|[^a-z])(sar|ar|sr|ur|rrr|rr|chr|csr|ace|r|u|c)(?:$|[^a-z])", re.I)
        for image in soup.select('img[src*="rar" i], img[class*="rar" i], img[alt*="レア"], img[title*="レア"]'):
            values = " ".join(str(image.get(attr, "")) for attr in ("src", "class", "alt", "title", "data-rarity"))
            stem = Path(image.get("src", "")).stem.lower()
            if stem.endswith("_u_c"):
                return "U/C"
            match = rarity_pattern.search(values)
            if match:
                return RARITY_NAMES.get(match.group(1).lower(), match.group(1).upper())

        for node in soup.select('[data-rarity], [class*="rarity" i], [class*="rare" i]'):
            values = f"{node.get('data-rarity', '')} {node.get_text(' ', strip=True)}"
            match = rarity_pattern.search(values)
            if match:
                return RARITY_NAMES.get(match.group(1).lower(), match.group(1).upper())
        return "未標示"

    @staticmethod
    def _load_cache(path: Path) -> List[Dict]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            source = "tw-pokemon" if path == TW_CACHE else "pokemon-jp"
            return [normalize_card(card, source) for card in data]
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def _save_cache(path: Path, cards: List[Dict]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        existing = OfficialPokemonScraper._load_cache(path)
        merged = {str(card.get("id")): card for card in existing if card.get("id")}
        merged.update({str(card.get("id")): card for card in cards if card.get("id")})
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(list(merged.values()), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _cached_search(path: Path, keyword: str) -> List[Dict]:
        term = keyword.casefold()
        return [
            card for card in OfficialPokemonScraper._load_cache(path)
            if term in str(card.get("name", "")).casefold()
            or term in str(card.get("id", "")).casefold()
            or term in str(card.get("number", "")).casefold()
        ]

    @staticmethod
    def _cached_page(path: Path, keyword: str, limit: int, page: int):
        matches = OfficialPokemonScraper._cached_search(path, keyword)
        start = (page - 1) * limit
        return matches[start:start + limit], len(matches)

    def _fetch_details(self, items: List[Dict], parser, limit: int) -> List[Dict]:
        results = []
        with ThreadPoolExecutor(max_workers=min(6, max(1, len(items)))) as executor:
            futures = {executor.submit(parser, item): item for item in items[:limit]}
            for future in as_completed(futures):
                try:
                    card = future.result()
                    if card:
                        results.append(card)
                except Exception as exc:
                    logger.warning("Official card detail failed: %s", exc)
        order = {item["id"]: index for index, item in enumerate(items)}
        return sorted(results, key=lambda card: order.get(card["id"].split("-", 1)[-1], 9999))

    def search_taiwan_page(self, keyword: str, limit: int = 20, page: int = 1):
        try:
            site_page_size = 20
            start = (page - 1) * limit
            end = start + limit
            first_site_page = (start // site_page_size) + 1
            last_site_page = ((end - 1) // site_page_size) + 1
            items = []
            total = 0
            for site_page in range(first_site_page, last_site_page + 1):
                soup = self._get_soup(
                    "https://asia.pokemon-card.com/tw/card-search/list/",
                    params={"keyword": keyword, "pageNo": site_page},
                )
                total_node = soup.select_one(".resultNumber")
                if total_node:
                    match = re.search(r"\d+", total_node.get_text(" ", strip=True).replace(",", ""))
                    if match:
                        total = int(match.group())
                for card in soup.select("li.card"):
                    link = card.select_one("a[href*='/card-search/detail/']")
                    if not link:
                        continue
                    match = re.search(r"/detail/(\d+)/", link.get("href", ""))
                    if match:
                        items.append({"id": match.group(1), "url": urljoin("https://asia.pokemon-card.com", link["href"])})

            relative_start = start - ((first_site_page - 1) * site_page_size)
            selected = items[relative_start:relative_start + limit]
            cards = self._fetch_details(selected, self._parse_taiwan_detail, len(selected))
            self._save_cache(TW_CACHE, cards)
            inferred_total = ((first_site_page - 1) * site_page_size) + len(items)
            return cards, max(total, inferred_total)
        except Exception as exc:
            logger.error("Taiwan Pokemon search failed: %s", exc)
            return self._cached_page(TW_CACHE, keyword, limit, page)

    def search_taiwan(self, keyword: str, limit: int = 20) -> List[Dict]:
        cards, _total = self.search_taiwan_page(keyword, limit, 1)
        return cards

    def _parse_taiwan_detail(self, item: Dict) -> Dict:
        soup = self._get_soup(item["url"])
        heading = soup.select_one("h1.cardDetail")
        marker = heading.select_one(".evolveMarker") if heading else None
        if marker:
            marker.extract()
        name = heading.get_text(" ", strip=True) if heading else "未命名卡牌"
        hp_node = soup.select_one(".mainInfomation .number, .hitPoint + .number, [class*='hp'] + .number")
        type_image = soup.select_one(".mainInfomation .type + img, .mainInfomation img[src*='/energy/']")
        image = soup.select_one(".cardImage img")
        number_node = soup.select_one(".collectorNumber")
        series_node = soup.select_one(".expansionLinkColumn a")
        series = series_node.get_text(" ", strip=True) if series_node else "未標示"
        series = re.sub(r"^(擴充包|起始牌組|強化擴充包)[「『]?|[」』]$", "", series).strip()
        skills = []
        for skill in soup.select(".skillInformation .skill"):
            skills.append({
                "name": (skill.select_one(".skillName") or skill).get_text(" ", strip=True),
                "damage": skill.select_one(".skillDamage").get_text(" ", strip=True) if skill.select_one(".skillDamage") else "",
                "effect": skill.select_one(".skillEffect").get_text(" ", strip=True) if skill.select_one(".skillEffect") else "",
            })
        return normalize_card({
            "id": f"tw-{item['id']}",
            "name": name,
            "hp": hp_node.get_text(strip=True) if hp_node else 0,
            "type": self._energy_from_image(type_image.get("src", "") if type_image else ""),
            "rarity": self._rarity_from_soup(soup),
            "series": series,
            "price": "-",
            "image_url": image.get("src", "") if image else "",
            "number": number_node.get_text(" ", strip=True) if number_node else item["id"],
            "skills": skills,
            "detail_url": item["url"],
        }, "tw-pokemon")

    def search_japan_page(self, keyword: str, limit: int = 20, page: int = 1):
        try:
            def fetch_payload(site_page):
                response = self.session.get(
                    "https://www.pokemon-card.com/card-search/resultAPI.php",
                    params={
                        "keyword": keyword,
                        "sm_and_keyword": "true",
                        "regulation": "all",
                        "page": site_page,
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()

            first_payload = fetch_payload(1)
            total = int(first_payload.get("hitCnt") or len(first_payload.get("cardList", [])))
            site_page_size = max(1, int(first_payload.get("cardEnd") or 0) - int(first_payload.get("cardStart") or 1) + 1)
            start = (page - 1) * limit
            end = start + limit
            first_site_page = (start // site_page_size) + 1
            last_site_page = ((end - 1) // site_page_size) + 1
            items = []
            for site_page in range(first_site_page, last_site_page + 1):
                payload = first_payload if site_page == 1 else fetch_payload(site_page)
                items.extend({
                    "id": str(card["cardID"]),
                    "url": f"https://www.pokemon-card.com/card-search/details.php/card/{card['cardID']}/regu/all",
                } for card in payload.get("cardList", []))

            relative_start = start - ((first_site_page - 1) * site_page_size)
            selected = items[relative_start:relative_start + limit]
            cards = self._fetch_details(selected, self._parse_japan_detail, len(selected))
            self._save_cache(JP_CACHE, cards)
            return cards, total
        except Exception as exc:
            logger.error("Japan Pokemon search failed: %s", exc)
            return self._cached_page(JP_CACHE, keyword, limit, page)

    def search_japan(self, keyword: str, limit: int = 20) -> List[Dict]:
        cards, _total = self.search_japan_page(keyword, limit, 1)
        return cards

    def _parse_japan_detail(self, item: Dict) -> Dict:
        soup = self._get_soup(item["url"])
        name_node = soup.select_one("h1.Heading1")
        hp_node = soup.select_one(".hp-num, .TopInfo [class*='hp-num']")
        type_node = soup.select_one(".TopInfo .td-r .icon, .TopInfo [class*='icon-']")
        image = soup.select_one(".LeftBox > img.fit")
        subtext = soup.select_one(".LeftBox .subtext")
        number_match = re.search(r"(\d+)\s*/\s*(\d+)", subtext.get_text(" ", strip=True) if subtext else "")
        series_node = soup.select_one(".PopupSub .List_item")
        series = series_node.get_text(" ", strip=True) if series_node else "未標示"
        series = re.sub(r"^(拡張パック|強化拡張パック|スターターセット)\s*", "", series).strip()
        series = series.strip("「」『』")
        icon_class = ""
        if type_node:
            icon_class = next((cls.replace("icon-", "") for cls in type_node.get("class", []) if cls.startswith("icon-")), "")
        return normalize_card({
            "id": f"jp-{item['id']}",
            "name": name_node.get_text(" ", strip=True) if name_node else "未命名卡牌",
            "hp": hp_node.get_text(strip=True) if hp_node else 0,
            "type": ENERGY_TYPES.get(icon_class, "未標示"),
            "rarity": self._rarity_from_soup(soup),
            "series": series,
            "price": "-",
            "image_url": urljoin("https://www.pokemon-card.com", image.get("src", "")) if image else "",
            "number": f"{number_match.group(1)}/{number_match.group(2)}" if number_match else item["id"],
            "detail_url": item["url"],
        }, "pokemon-jp")
