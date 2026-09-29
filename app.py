"""Flask entry point for the official card catalogue and image recognition."""

import base64
import logging
import os
import threading

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from card_apis import SOURCE_HANDLERS, search_all_cards_paginated, search_source


logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
allowed_origins = [
    "http://localhost:5000", "http://127.0.0.1:5000",
    "http://localhost:3000", "http://127.0.0.1:3000",
]
if os.environ.get("RENDER_EXTERNAL_URL"):
    allowed_origins.append(os.environ["RENDER_EXTERNAL_URL"])
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/identify", methods=["POST"])
def identify_card():
    from database import MATCH_THRESHOLD, match_card_image

    payload = request.get_json(silent=True) or {}
    encoded = payload.get("image", "")
    if not encoded:
        return jsonify({"status": "error", "error": "No image provided"}), 400
    try:
        image_bytes = base64.b64decode(encoded.split(",", 1)[-1], validate=True)
    except (ValueError, TypeError):
        return jsonify({"status": "error", "error": "Invalid base64 image"}), 400

    matched_card, confidence = match_card_image(image_bytes)
    if matched_card and confidence >= MATCH_THRESHOLD:
        return jsonify({
            "status": "success", "match": matched_card,
            "confidence": round(confidence, 2), "cards": [matched_card],
        })
    return jsonify({
        "status": "fail",
        "error": "找不到匹配的卡面或畫面特徵不足",
        "confidence": round(confidence, 2), "match": matched_card,
    })


def _search_arguments():
    keyword = request.args.get("keyword", "").strip()
    source = request.args.get("source", "all").lower()
    try:
        page = max(1, int(request.args.get("page", "1")))
        limit = min(100, max(1, int(request.args.get("limit", "50"))))
    except ValueError as exc:
        raise ValueError("page 與 limit 必須是整數") from exc
    if len(keyword) < 2:
        raise ValueError("搜索關鍵字至少 2 個字符")
    valid_sources = [*SOURCE_HANDLERS.keys(), "all"]
    if source not in valid_sources:
        raise ValueError(f"無效的來源: {source}; 有效來源: {', '.join(valid_sources)}")
    return keyword, source, page, limit


@app.route("/api/cards/search")
def search_cards():
    try:
        keyword, source, page, limit = _search_arguments()
        if source == "all":
            return jsonify({
                "keyword": keyword, "source": "all",
                "results": search_all_cards_paginated(keyword, limit, page),
            })
        return jsonify({
            "keyword": keyword, "source": source,
            **search_source(source, keyword, limit, page),
        })
    except ValueError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Card search failed")
        return jsonify({"status": "error", "error": "搜尋失敗", "details": str(exc)}), 500


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "資源未找到"}), 404


def _warm_feature_database():
    if app.config.get("TESTING") or os.environ.get("DISABLE_CV_WARMUP") == "1":
        return
    from database import initialize_online_features
    initialize_online_features()


threading.Thread(target=_warm_feature_database, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
