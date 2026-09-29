"""Persistent OpenCV feature database for locally cached Pokemon cards."""

import hashlib
import json
import logging
import pickle
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import requests

from card_schema import normalize_card


logger = logging.getLogger(__name__)
FEATURE_DENOMINATOR = 35.0
MATCH_THRESHOLD = 47.0
LOWE_RATIO = 0.78
MAX_MATCH_DISTANCE = 64
MIN_GEOMETRIC_MATCHES = 8
MIN_INLIER_RATIO = 0.40
MIN_WINNER_MARGIN = 3
MIN_WINNER_MARGIN_RATIO = 0.12
FEATURE_CACHE_VERSION = 2

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CARD_DATA_FILES = (DATA_DIR / "pokemon_tw.json", DATA_DIR / "pokemon_jp.json")
FEATURE_CACHE = DATA_DIR / "features_cache.pkl"
LOCAL_IMAGE_DIRS = (ROOT / "card_images", DATA_DIR / "card_images")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

orb = cv2.ORB_create(nfeatures=1200)
matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
ONLINE_CARD_FEATURES = {}


def _debug_print(message):
    """Keep CV diagnostics from crashing on Windows legacy console encodings."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_message = str(message).encode(encoding, errors="backslashreplace").decode(encoding)
    print(safe_message, flush=True)


def _load_cards():
    cards = {}
    for path in CARD_DATA_FILES:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            logger.warning("Unable to read card data %s: %s", path, exc)
            continue
        if not isinstance(payload, list):
            continue
        for card in payload:
            source = card.get("source") or ("tw-pokemon" if path.name == "pokemon_tw.json" else "pokemon-jp")
            card = normalize_card(card, source)
            card_id = str(card.get("id") or "").strip()
            if card_id and card.get("image_url"):
                cards[card_id] = card
    return list(cards.values())


def _safe_stem(value):
    return re.sub(r"[^\w.-]+", "_", str(value or "").strip(), flags=re.UNICODE).strip("._").casefold()


def _local_image_index():
    index = {}
    for directory in LOCAL_IMAGE_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                index.setdefault(path.stem.casefold(), []).append(path)
    return index


def _find_local_image(card, image_index, name_counts):
    exact_keys = (_safe_stem(card.get("id")), _safe_stem(card.get("number")))
    for key in exact_keys:
        if key and len(image_index.get(key, [])) == 1:
            return image_index[key][0]

    name_key = _safe_stem(card.get("name"))
    if name_key and name_counts[name_key] == 1 and len(image_index.get(name_key, [])) == 1:
        return image_index[name_key][0]
    return None


def _card_signature(card, local_image):
    local_state = None
    if local_image:
        stat = local_image.stat()
        local_state = [str(local_image.resolve()), stat.st_size, stat.st_mtime_ns]
    source = json.dumps(
        {
            "id": card.get("id"),
            "image_url": card.get("image_url"),
            "local_image": local_state,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _load_feature_cache():
    try:
        with FEATURE_CACHE.open("rb") as handle:
            payload = pickle.load(handle)
        if payload.get("version") != FEATURE_CACHE_VERSION or not isinstance(payload.get("cards"), dict):
            return {}
        return payload["cards"]
    except (FileNotFoundError, EOFError, OSError, pickle.PickleError, AttributeError, ValueError) as exc:
        logger.info("Feature cache unavailable; rebuilding: %s", exc)
        return {}


def _save_feature_cache(features):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = FEATURE_CACHE.with_suffix(".tmp")
    payload = {"version": FEATURE_CACHE_VERSION, "cards": features}
    with temporary.open("wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    temporary.replace(FEATURE_CACHE)


def _compute_descriptors(task):
    card, signature, local_image = task
    image_source = str(local_image) if local_image else card.get("image_url")
    try:
        if local_image:
            image_bytes = local_image.read_bytes()
        else:
            response = requests.get(card["image_url"], timeout=15)
            response.raise_for_status()
            image_bytes = response.content

        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None:
            return None
        if max(image.shape) > 1000:
            scale = 1000 / max(image.shape)
            image = cv2.resize(image, None, fx=scale, fy=scale)
        keypoints, descriptors = orb.detectAndCompute(image, None)
        if descriptors is None:
            return None
        return card["id"], {
            "signature": signature,
            "descriptors": descriptors,
            "keypoint_points": np.float32([keypoint.pt for keypoint in keypoints]),
            "keypoint_count": len(keypoints),
            "name": f"{card['name']} ({card.get('number', card['id'])})",
            "detail": card,
            "image_source": image_source,
        }
    except Exception as exc:
        logger.warning("Feature image failed for %s: %s", image_source, exc)
        return None


def initialize_online_features():
    """Load every cached TW/JP card and reuse persistent descriptors when valid."""
    global ONLINE_CARD_FEATURES
    cards = _load_cards()
    image_index = _local_image_index()
    name_counts = Counter(_safe_stem(card.get("name")) for card in cards)
    cached_features = _load_feature_cache()
    features = {}
    pending = []
    reused_count = 0

    for card in cards:
        local_image = _find_local_image(card, image_index, name_counts)
        signature = _card_signature(card, local_image)
        cached = cached_features.get(card["id"])
        if (
            cached
            and cached.get("signature") == signature
            and isinstance(cached.get("descriptors"), np.ndarray)
            and isinstance(cached.get("keypoint_points"), np.ndarray)
        ):
            cached["detail"] = card
            cached["name"] = f"{card['name']} ({card.get('number', card['id'])})"
            features[card["id"]] = cached
            reused_count += 1
        else:
            pending.append((card, signature, local_image))

    if pending:
        logger.info("[CV] Computing %s new/changed card features", len(pending))
        with ThreadPoolExecutor(max_workers=6) as executor:
            for result in executor.map(_compute_descriptors, pending):
                if result:
                    card_id, feature = result
                    features[card_id] = feature

    ONLINE_CARD_FEATURES = features
    try:
        _save_feature_cache(features)
    except OSError as exc:
        logger.warning("Unable to persist feature cache: %s", exc)
    logger.info(
        "[CV] Feature database ready with %s cards (%s reused, %s requested for recalculation)",
        len(features), reused_count, len(pending),
    )
    return len(features)


def match_card_image(client_image_bytes):
    """Return the best canonical card payload and confidence percentage."""
    if not ONLINE_CARD_FEATURES:
        _debug_print("[CV DEBUG] feature database is empty")
        return None, 0.0
    client = cv2.imdecode(np.frombuffer(client_image_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
    if client is None:
        _debug_print("[CV DEBUG] camera image decode failed")
        return None, 0.0
    if max(client.shape) > 1000:
        scale = 1000 / max(client.shape)
        client = cv2.resize(client, None, fx=scale, fy=scale)
    client_keypoints, client_descriptors = orb.detectAndCompute(client, None)
    _debug_print(
        f"[CV DEBUG] camera_keypoints={len(client_keypoints)} "
        f"descriptors={0 if client_descriptors is None else len(client_descriptors)}"
    )
    if client_descriptors is None:
        return None, 0.0

    client_points = np.float32([keypoint.pt for keypoint in client_keypoints])
    scores = []
    for feature in ONLINE_CARD_FEATURES.values():
        try:
            pairs = matcher.knnMatch(feature["descriptors"], client_descriptors, k=2)
        except cv2.error:
            continue

        ratio_matches = [
            first
            for pair in pairs
            if len(pair) == 2
            for first, second in [pair]
            if first.distance < LOWE_RATIO * second.distance
            and first.distance <= MAX_MATCH_DISTANCE
        ]
        inliers = 0
        inlier_ratio = 0.0
        if len(ratio_matches) >= MIN_GEOMETRIC_MATCHES:
            reference_points = np.float32(
                [feature["keypoint_points"][match.queryIdx] for match in ratio_matches]
            ).reshape(-1, 1, 2)
            observed_points = np.float32(
                [client_points[match.trainIdx] for match in ratio_matches]
            ).reshape(-1, 1, 2)
            try:
                _, mask = cv2.findHomography(
                    reference_points, observed_points, cv2.RANSAC, 5.0
                )
            except cv2.error:
                mask = None
            if mask is not None:
                inliers = int(mask.ravel().sum())
                inlier_ratio = inliers / len(ratio_matches)

        confidence = min(100.0, (inliers / FEATURE_DENOMINATOR) * 100.0)
        scores.append((inliers, inlier_ratio, len(ratio_matches), confidence, feature))
    if not scores:
        return None, 0.0

    scores.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    for rank, (inliers, inlier_ratio, ratio_count, confidence, feature) in enumerate(scores[:3], start=1):
        _debug_print(
            f"[CV DEBUG] top{rank}={feature['name']} "
            f"ratio_matches={ratio_count} inliers={inliers} "
            f"inlier_ratio={inlier_ratio:.2f} confidence={confidence:.2f}%"
        )

    inliers, inlier_ratio, _, confidence, best = scores[0]
    runner_up_matches = scores[1][0] if len(scores) > 1 else 0
    winner_margin = inliers - runner_up_matches
    required_margin = max(MIN_WINNER_MARGIN, round(inliers * MIN_WINNER_MARGIN_RATIO))
    _debug_print(
        f"[CV DEBUG] winner_margin={winner_margin} required_margin={required_margin}"
    )
    logger.info(
        "[CV] Best match %s: %s geometric inliers (%.2f%%)",
        best["name"], inliers, confidence,
    )
    geometrically_valid = (
        inliers >= MIN_GEOMETRIC_MATCHES and inlier_ratio >= MIN_INLIER_RATIO
    )
    if geometrically_valid and confidence >= MATCH_THRESHOLD and winner_margin >= required_margin:
        return best["detail"], confidence
    if confidence >= MATCH_THRESHOLD or not geometrically_valid:
        logger.info("[CV] Match rejected due to weak geometry or ambiguous candidates")
        return None, min(confidence, MATCH_THRESHOLD - 0.01)
    return None, confidence
