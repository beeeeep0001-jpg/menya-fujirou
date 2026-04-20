#!/usr/bin/env python3
"""
MEO Ranking via Google Places API (New) - Text Search
Usage: python meo_rank_api.py "店舗名" "エリア" "業種" [--api-key KEY]
Output: JSON with rankings for 7 keywords
"""

import json
import sys
import os
import time
import argparse
import requests
from pathlib import Path

# .env ファイルを手動ロード（python-dotenv 不要）
def _load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

PLACES_API_URL = "https://places.googleapis.com/v1/places:searchText"

# Coordinates for location bias (lat, lng, radius_meters)
LOCATION_CONFIGS = {
    "恵比寿": {"lat": 35.6467, "lng": 139.7102, "radius": 800},
    "新橋":   {"lat": 35.6662, "lng": 139.7574, "radius": 600},
    "新宿":   {"lat": 35.6896, "lng": 139.7006, "radius": 800},
    "渋谷":   {"lat": 35.6580, "lng": 139.7016, "radius": 700},
    "六本木": {"lat": 35.6628, "lng": 139.7318, "radius": 600},
    "青山":   {"lat": 35.6655, "lng": 139.7180, "radius": 600},
    "麻布":   {"lat": 35.6547, "lng": 139.7365, "radius": 600},
    "default":{"lat": 35.6762, "lng": 139.6503, "radius": 1000},
}

def get_location(area: str) -> dict:
    for key, val in LOCATION_CONFIGS.items():
        if key in area:
            return val
    return LOCATION_CONFIGS["default"]


def build_keywords(store_name: str, area: str, biz_type: str) -> list[str]:
    """業種に応じた7キーワードを生成"""
    area_short = area.replace("駅", "").replace("周辺", "").strip()

    biz_map = {
        "ホテル": [
            f"{area_short} ホテル おすすめ",
            f"{area_short} アパートホテル",
            f"{area_short} サービスアパートメント",
            f"{area_short} 長期滞在 ホテル",
            f"{area_short} 家族 宿泊",
            f"{area_short} ホテル 格安",
            f"渋谷 ホテル おすすめ",
        ],
        "旅館": [
            f"{area_short} 旅館 おすすめ",
            f"{area_short} ホテル おすすめ",
            f"{area_short} アパートホテル",
            f"{area_short} 長期滞在",
            f"{area_short} 宿泊 おすすめ",
            f"{area_short} 家族 宿泊",
            f"渋谷 宿泊 おすすめ",
        ],
        "学習塾": [
            f"{area_short} 学習塾 おすすめ",
            f"{area_short} 個別指導塾",
            f"{area_short} 塾 小学生",
            f"{area_short} 塾 中学生",
            f"{area_short} 塾 高校生",
            f"{area_short} 補習塾",
            f"{area_short} 進学塾",
        ],
        "整体": [
            f"{area_short} 整体 おすすめ",
            f"{area_short} 整骨院",
            f"{area_short} 肩こり 整体",
            f"{area_short} 腰痛 整体",
            f"{area_short} マッサージ おすすめ",
            f"{area_short} 骨盤矯正",
            f"{area_short} 整体 即日",
        ],
        "居酒屋": [
            f"{area_short} 居酒屋 おすすめ",
            f"{area_short} 居酒屋 個室",
            f"{area_short} 居酒屋 宴会",
            f"{area_short} 飲み放題 居酒屋",
            f"{area_short} 居酒屋 安い",
            f"{area_short} 海鮮 居酒屋",
            f"{area_short} 創作居酒屋",
        ],
    }

    # 業種マッチング
    for key, kws in biz_map.items():
        if key in biz_type:
            return kws

    # デフォルト（業種をそのまま使う）
    return [
        f"{area_short} {biz_type} おすすめ",
        f"{area_short} {biz_type} 人気",
        f"{area_short} {biz_type} 評判",
        f"{area_short} {biz_type} 安い",
        f"{area_short} {biz_type} 近く",
        f"{area_short} おすすめ {biz_type}",
        f"東京 {biz_type} おすすめ {area_short}",
    ]


def search_places(query: str, location: dict, api_key: str, max_results: int = 20) -> list[dict]:
    """Google Places API Text Search で順位取得"""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.types",
    }
    body = {
        "textQuery": query,
        "languageCode": "ja",
        "maxResultCount": max_results,
        "locationBias": {
            "circle": {
                "center": {"latitude": location["lat"], "longitude": location["lng"]},
                "radius": location["radius"],
            }
        },
    }
    resp = requests.post(PLACES_API_URL, headers=headers, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("places", [])


def find_rank(places: list[dict], store_name: str) -> str:
    """店舗名で順位検索（部分一致）"""
    name_lower = store_name.lower()
    for i, place in enumerate(places, 1):
        display = place.get("displayName", {}).get("text", "")
        if name_lower in display.lower() or display.lower() in name_lower:
            return str(i)
    return "21位以下"


def run(store_name: str, area: str, biz_type: str, api_key: str) -> dict:
    location = get_location(area)
    keywords = build_keywords(store_name, area, biz_type)

    results = []
    for kw in keywords:
        try:
            places = search_places(kw, location, api_key)
            rank = find_rank(places, store_name)
            results.append({"keyword": kw, "rank": rank, "total": len(places)})
            print(f"  [{rank:>8}] {kw}", flush=True)
            time.sleep(0.3)
        except Exception as e:
            results.append({"keyword": kw, "rank": "エラー", "error": str(e)})
            print(f"  [   ERROR] {kw} → {e}", flush=True)

    best = [r for r in results if r["rank"].replace("位", "").isdigit()]
    worst_rank = max((int(r["rank"].replace("位","")) for r in best), default=99)
    best_rank = min((int(r["rank"].replace("位","")) for r in best), default=99)

    return {
        "store": store_name,
        "area": area,
        "biz_type": biz_type,
        "location": location,
        "rankings": results,
        "summary": {
            "best_rank": best_rank if best else None,
            "worst_rank": worst_rank if best else None,
            "top3_count": sum(1 for r in best if int(r["rank"].replace("位","")) <= 3),
            "top10_count": sum(1 for r in best if int(r["rank"].replace("位","")) <= 10),
        }
    }


def main():
    parser = argparse.ArgumentParser(description="MEO Rank via Google Places API")
    parser.add_argument("store", help="店舗名")
    parser.add_argument("area", help="エリア（例: 恵比寿）")
    parser.add_argument("biz_type", help="業種（例: ホテル）")
    parser.add_argument("--api-key", default=os.environ.get("GOOGLE_PLACES_API_KEY", ""), help="Google Places API (New) Key")
    parser.add_argument("--output", default=None, help="JSON出力ファイルパス")
    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: GOOGLE_MAPS_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== MEO順位計測: {args.store} / {args.area} / {args.biz_type} ===")
    result = run(args.store, args.area, args.biz_type, args.api_key)

    out_path = args.output or f"meo_result_{args.store.replace(' ', '_')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n--- サマリー ---")
    print(f"最高順位: {result['summary']['best_rank']}位")
    print(f"最低順位: {result['summary']['worst_rank']}位")
    print(f"トップ10入り: {result['summary']['top10_count']}/7 KW")
    print(f"JSON保存: {out_path}")
    return result


if __name__ == "__main__":
    main()
