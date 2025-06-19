#!/usr/bin/env python
"""
update_cache.py
– 未来日の在庫・平均料金を取得して
  vacancy_price_cache.json / historical_data.json を更新
"""

import os
import sys
import json
import calendar
import requests
import datetime as dt
from pathlib import Path
from dateutil.relativedelta import relativedelta

# --------------------------------------------------
# 定数・環境変数
# --------------------------------------------------
APP_ID = os.environ.get("RAKUTEN_APP_ID", "")
if not APP_ID:
    raise ValueError("❌ RAKUTEN_APP_ID が設定されていません。GitHub Secrets に登録してください。")

CACHE_FILE      = "vacancy_price_cache.json"          # 現行キャッシュ
PREV_CACHE_FILE = "vacancy_price_cache_previous.json" # 前回巡回分キャッシュ
HISTORICAL_FILE = "historical_data.json"              # 日付別の履歴を保持

# --------------------------------------------------
# 楽天 API から 1 日分取得
# --------------------------------------------------
def fetch_vacancy_and_price(date: dt.date) -> dict:
    print(f"🔍 fetching {date}", file=sys.stderr)

    prices: list[int] = []
    vacancy_total     = 0

    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    for page in range(1, 4):
        params = {
            "applicationId": APP_ID,
            "format": "json",
            "checkinDate":  date.strftime("%Y-%m-%d"),
            "checkoutDate": (date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            "adultNum": 1,
            # なんば・心斎橋・天王寺・阿倍野・長居（＝大阪市中央区・浪速区周辺）
            "largeClassCode":  "japan",
            "middleClassCode": "osaka",
            "smallClassCode":  "shi",
            "detailClassCode": "D",
            "page": page,
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ⚠️ fetch error on {date} page {page}: {e}", file=sys.stderr)
            continue

        # 1 ページ目にのみ総在庫数が載る
        if page == 1:
            vacancy_total = data.get("pagingInfo", {}).get("recordCount", 0)

        for hotel in data.get("hotels", []):
            parts = hotel.get("hotel", [])
            if len(parts) >= 2:
                for plan in parts[1].get("roomInfo", []):
                    total = plan.get("dailyCharge", {}).get("total")
                    if total is not None:
                        prices.append(total)

    avg_price = round(sum(prices) / len(prices), 0) if prices else 0.0
    print(f"   → avg_price = {avg_price}  (vacancy={vacancy_total})", file=sys.stderr)
    return {"vacancy": vacancy_total, "avg_price": avg_price}

# --------------------------------------------------
# メイン処理
# --------------------------------------------------
def update_cache(start_date: dt.date, months: int = 9) -> dict:
    """未来日データを取得して cache/historical を更新 → 新 cache を返す"""
    today             = dt.date.today()
    three_months_ago  = today - relativedelta(months=3)
    cal               = calendar.Calendar(firstweekday=calendar.SUNDAY)

    # 既存キャッシュ
    cache: dict[str, dict] = {}
    if Path(CACHE_FILE).exists():
        cache = json.loads(Path(CACHE_FILE).read_text(encoding="utf-8"))

    # 前回巡回キャッシュ
    old_cache: dict[str, dict] = {}
    if Path(PREV_CACHE_FILE).exists():
        old_cache = json.loads(Path(PREV_CACHE_FILE).read_text(encoding="utf-8"))

    # 3 か月より古いキーは削除（メインキャッシュのみ保持）
    cache = {k: v for k, v in cache.items() if dt.date.fromisoformat(k) >= three_months_ago}

    # ---------------- 未来日を取得 ----------------
    for m in range(months):
        month_start = (start_date + relativedelta(months=m)).replace(day=1)
        for week in cal.monthdatescalendar(month_start.year, month_start.month):
            for day in week:
                # 対象：未来日（今日より後）かつ当該月
                if day.month != month_start.month or day <= today:
                    continue

                iso      = day.isoformat()
                new_data = fetch_vacancy_and_price(day)
                if new_data["vacancy"] == 0 and new_data["avg_price"] == 0.0:
                    print(f"⏩ skip {iso} (empty)", file=sys.stderr)
                    continue

                # 前回との差分計算
                prev          = old_cache.get(iso, {})
                last_vac      = prev.get("vacancy", new_data["vacancy"])
                last_price    = prev.get("avg_price", new_data["avg_price"])
                vac_diff      = new_data["vacancy"] - last_vac
                price_diff    = new_data["avg_price"] - last_price

                cache[iso] = {
                    "vacancy":        new_data["vacancy"],
                    "avg_price":      new_data["avg_price"],
                    "last_vacancy":   last_vac,
                    "last_avg_price": last_price,
                    "vacancy_diff":   vac_diff,
                    "avg_price_diff": price_diff,
                }

    # 保存
    Path(CACHE_FILE).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(PREV_CACHE_FILE).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ cache updated", file=sys.stderr)
    return cache

# --------------------------------------------------
# 履歴 (historical_data.json) をアップデート
# --------------------------------------------------
def _is_date_string(s: str) -> bool:
    """ISO 形式の日付文字列なら True"""
    try:
        dt.date.fromisoformat(s)
        return True
    except ValueError:
        return False

def update_history(cache: dict):
    today       = dt.date.today()
    today_str   = today.isoformat()
    hist_data: dict[str, dict] = {}

    if Path(HISTORICAL_FILE).exists():
        try:
            with open(HISTORICAL_FILE, encoding="utf-8") as f:
                hist_data = json.load(f)
        except Exception as e:
            print(f"⚠️ error loading historical_data.json: {e}", file=sys.stderr)

    # 1) 未来日の today's snapshot 追加
    for iso, v in cache.items():
        if dt.date.fromisoformat(iso) >= today:
            hist_data.setdefault(iso, {})
            hist_data[iso][today_str] = {
                "vacancy":    v["vacancy"],
                "avg_price":  v["avg_price"],
            }

    # 2) 3 か月より古い履歴は削除
    for date_key in list(hist_data.keys()):
        if not _is_date_string(date_key):
            print(f"⚠️ skip legacy key {date_key}", file=sys.stderr)
            continue

        date_dt = dt.date.fromisoformat(date_key)
        limit   = date_dt - relativedelta(months=3)

        for hist_key in list(hist_data[date_key].keys()):
            if not _is_date_string(hist_key):
                print(f"⚠️ skip legacy hist_key {hist_key}", file=sys.stderr)
                del hist_data[date_key][hist_key]
                continue

            hist_dt = dt.date.fromisoformat(hist_key)
            if hist_dt < limit:
                del hist_data[date_key][hist_key]

        if not hist_data[date_key]:
            del hist_data[date_key]

    Path(HISTORICAL_FILE).write_text(json.dumps(hist_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("📁 historical_data.json updated", file=sys.stderr)

# --------------------------------------------------
# エントリーポイント
# --------------------------------------------------
if __name__ == "__main__":
    print("📡 update_cache.py start", file=sys.stderr)
    cache_now = update_cache(start_date=dt.date.today(), months=9)
    update_history(cache_now)
    print("✨ all done", file=sys.stderr)
