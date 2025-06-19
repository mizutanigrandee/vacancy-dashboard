#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
vacancy-dashboard 予約在庫 & 料金データ取得スクリプト
毎日 GitHub Actions から呼ばれて
  • vacancy_price_cache.json        … 直近 3 か月分の最新データ
  • vacancy_price_cache_previous.json … 1 日前データ（差分計算用バックアップ）
  • historical_data.json            … 未来日ごとの履歴（3 か月分まで保持）
を更新します。
"""

import os
import sys
import json
import calendar
import requests
import datetime as dt
from pathlib import Path
from dateutil.relativedelta import relativedelta

# ──────────────────────────────────
# 定数
# ──────────────────────────────────
APP_ID          = os.environ.get("RAKUTEN_APP_ID", "")
if not APP_ID:
    raise ValueError("❌ RAKUTEN_APP_ID が設定されていません。GitHub Secrets に登録されていますか？")

CACHE_FILE      = "vacancy_price_cache.json"
PREV_CACHE_FILE = "vacancy_price_cache_previous.json"
HISTORICAL_FILE = "historical_data.json"


# ──────────────────────────────────
# 楽天トラベル API から 1 日分の在庫数・平均単価を取得
# ──────────────────────────────────
def fetch_vacancy_and_price(target: dt.date) -> dict:
    print(f"🔍 fetching {target}", file=sys.stderr)
    prices: list[float] = []
    vacancy_total = 0

    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    for page in range(1, 4):                                   # 上位 3 ページ ≒ 90 施設
        params = {
            "applicationId": APP_ID,
            "format": "json",
            "checkinDate":  target.strftime("%Y-%m-%d"),
            "checkoutDate": (target + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            "adultNum": 1,
            "largeClassCode":  "japan",
            "middleClassCode": "osaka",
            "smallClassCode":  "shi",
            "detailClassCode": "D",
            "page": page,
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"  ⚠️ fetch error on {target} page {page}: {e}", file=sys.stderr)
            continue

        # 1 ページ目の recordCount が残室（施設）数
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


# ──────────────────────────────────
# メイン更新処理
# ──────────────────────────────────
def update_cache(start_date: dt.date, months: int = 9) -> dict:
    """
    ・未来日（start_date から months か月分）の最新データを取得して cache を更新
    ・前日との差分を計算して記録
    ・historic_data.json 追記もここでは行わない（main 節で実施）
    """
    today = dt.date.today()
    three_months_ago = today - relativedelta(months=3)

    # 既存キャッシュ
    cache: dict[str, dict] = {}
    if Path(CACHE_FILE).exists():
        cache = json.loads(Path(CACHE_FILE).read_text(encoding="utf-8"))

    # 前回（前日）取得キャッシュ
    old_cache: dict[str, dict] = {}
    if Path(PREV_CACHE_FILE).exists():
        old_cache = json.loads(Path(PREV_CACHE_FILE).read_text(encoding="utf-8"))

    # 3 か月より古いキーを削除
    cache = {
        k: v for k, v in cache.items()
        if dt.date.fromisoformat(k) >= three_months_ago
    }

    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)

    # ── データ取得ループ ──
    for m in range(months):
        base_month = (start_date + relativedelta(months=m)).replace(day=1)
        for week in cal.monthdatescalendar(base_month.year, base_month.month):
            for day in week:
                # 対象月かつ “今日以降” の日付のみ
                if day.month != base_month.month or day < today:
                    continue

                iso = day.isoformat()
                new = fetch_vacancy_and_price(day)
                if new["vacancy"] == 0 and new["avg_price"] == 0:
                    print(f"⏩ skip {iso} : empty result", file=sys.stderr)
                    continue

                new_vac, new_pri = new["vacancy"], new["avg_price"]
                prev = old_cache.get(iso, {})

                last_vac = prev.get("vacancy", new_vac)
                last_pri = prev.get("avg_price", new_pri)

                record = {
                    "vacancy":        new_vac,
                    "avg_price":      new_pri,
                    "last_vacancy":   last_vac,
                    "last_avg_price": last_pri,
                    "vacancy_diff":   new_vac - last_vac,
                    "avg_price_diff": new_pri - last_pri,
                }
                cache[iso] = record

    # 保存
    Path(CACHE_FILE).write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("✅ cache updated", file=sys.stderr)

    # “今回” を next run 用 previous として保存
    Path(PREV_CACHE_FILE).write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return cache


# ──────────────────────────────────
# historical_data.json の保守 / 追記
# ──────────────────────────────────
def update_history(cache: dict):
    today = dt.date.today()
    today_str = today.isoformat()

    hist: dict[str, dict] = {}
    if Path(HISTORICAL_FILE).exists():
        try:
            with open(HISTORICAL_FILE, "r", encoding="utf-8") as f:
                hist = json.load(f)
        except Exception as e:
            print(f"⚠️ error loading history: {e}", file=sys.stderr)

    # 1) 今日以降のデータを履歴に追記
    for iso, v in cache.items():
        iso_date = dt.date.fromisoformat(iso)
        if iso_date >= today:
            hist.setdefault(iso, {})
            hist[iso][today_str] = {
                "vacancy":   v["vacancy"],
                "avg_price": v["avg_price"],
            }

    # 2) 各日付の履歴を「その日から 3 か月超えたら削除」
    for date_key in list(hist.keys()):
        date_dt = dt.date.fromisoformat(date_key)
        limit   = date_dt - relativedelta(months=3)
        for hist_key in list(hist[date_key].keys()):
            if dt.date.fromisoformat(hist_key) < limit:
                del hist[date_key][hist_key]
        if not hist[date_key]:      # 空なら削除
            del hist[date_key]

    # 保存
    Path(HISTORICAL_FILE).write_text(
        json.dumps(hist, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("📁 historical_data.json updated", file=sys.stderr)


# ──────────────────────────────────
# エントリポイント
# ──────────────────────────────────
if __name__ == "__main__":
    print("📡 Starting update_cache.py", file=sys.stderr)
    base = dt.date.today()
    new_cache = update_cache(base, months=9)
    update_history(new_cache)
