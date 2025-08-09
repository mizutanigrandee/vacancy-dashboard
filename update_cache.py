#!/usr/bin/env python
"""
update_cache.py
– 未来日の在庫・平均料金を取得して
  vacancy_price_cache.json / historical_data.json / demand_spike_history.json を更新
  ＋ GitHub Actions 実行完了のJST時刻を last_updated.json に書き出す
"""

import os
import sys
import json
import calendar
import requests
import datetime as dt
from pathlib import Path
from dateutil.relativedelta import relativedelta

APP_ID = os.environ.get("RAKUTEN_APP_ID", "")
if not APP_ID:
    raise ValueError("❌ RAKUTEN_APP_ID が設定されていません。GitHub Secrets に登録してください。")

CACHE_FILE          = "vacancy_price_cache.json"
PREV_CACHE_FILE     = "vacancy_price_cache_previous.json"
HISTORICAL_FILE     = "historical_data.json"
SPIKE_HISTORY_FILE  = "demand_spike_history.json"
LAST_UPDATED_FILE   = "last_updated.json"   # ← 追加: フロントが読む最終更新メタ

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

def update_cache(start_date: dt.date, months: int = 9) -> dict:
    today             = dt.date.today()
    three_months_ago  = today - relativedelta(months=3)
    cal               = calendar.Calendar(firstweekday=calendar.SUNDAY)

    cache: dict[str, dict] = {}
    if Path(CACHE_FILE).exists():
        cache = json.loads(Path(CACHE_FILE).read_text(encoding="utf-8"))

    old_cache: dict[str, dict] = {}
    if Path(PREV_CACHE_FILE).exists():
        old_cache = json.loads(Path(PREV_CACHE_FILE).read_text(encoding="utf-8"))

    # 過去3か月より前は削除
    cache = {k: v for k, v in cache.items() if dt.date.fromisoformat(k) >= three_months_ago}

    for m in range(months):
        month_start = (start_date + relativedelta(months=m)).replace(day=1)
        for week in cal.monthdatescalendar(month_start.year, month_start.month):
            for day in week:
                # 現在以降の未来日だけ取得
                if day.month != month_start.month or day <= today:
                    continue

                iso      = day.isoformat()
                new_data = fetch_vacancy_and_price(day)
                # API失敗日はスキップし既存値保持（0/0は更新しない）
                if new_data["vacancy"] == 0 and new_data["avg_price"] == 0.0:
                    print(f"⏩ skip {iso} (empty)", file=sys.stderr)
                    continue

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

    Path(CACHE_FILE).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(PREV_CACHE_FILE).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ cache updated", file=sys.stderr)
    return cache

def _is_date_string(s: str) -> bool:
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

    # 未来日の今日時点スナップショットを追記
    for iso, v in cache.items():
        if dt.date.fromisoformat(iso) >= today:
            hist_data.setdefault(iso, {})
            hist_data[iso][today_str] = {
                "vacancy":    v["vacancy"],
                "avg_price":  v["avg_price"],
            }

    # 各対象日の履歴を3か月に圧縮
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

def detect_demand_spikes(cache_data, n_recent=3, pct=0.05):
    """
    cache_data: vacancy_price_cache.json の dict
    - 直近 n_recent 日の“実行日”は除外（安定化のため）
    - 判定対象は “今日以降の宿泊日” のみ（過去日は除外）
    - last_* が無い初回取得や 0 の分母は自動スキップ相当
    """
    sorted_dates = sorted(cache_data.keys())
    today = dt.date.today()

    # 直近n日分の“宿泊日”は除外（必要に応じて変更）
    exclude_exec_dates = {(today - dt.timedelta(days=i)).isoformat() for i in range(n_recent)}

    results = []
    for d in sorted_dates:
        # ★ 過去日の宿泊は判定から除外
        try:
            stay_dt = dt.date.fromisoformat(d)
        except Exception:
            continue
        if stay_dt < today:
            continue
        if d in exclude_exec_dates:
            continue

        rec = cache_data[d]
        last_price = rec.get("last_avg_price", 0)
        last_vac   = rec.get("last_vacancy", 0)
        price_diff = rec.get("avg_price_diff", 0)
        vac_diff   = rec.get("vacancy_diff", 0)

        price_ratio = abs(price_diff / last_price) if last_price else 0
        vac_ratio   = abs(vac_diff   / last_vac)   if last_vac   else 0

        if price_ratio >= pct or vac_ratio >= pct:
            results.append({
                "spike_date": d,
                "price": rec.get("avg_price", 0),
                "last_price": last_price,
                "price_diff": price_diff,
                "price_ratio": price_ratio,
                "vacancy": rec.get("vacancy", 0),
                "last_vac": last_vac,
                "vacancy_diff": vac_diff,
                "vacancy_ratio": vac_ratio,
            })

    print(f"📊 Demand Spikes Detected (future only): {len(results)} 件", file=sys.stderr)
    return results


def save_demand_spike_history(demand_spikes, history_file=SPIKE_HISTORY_FILE):
    """履歴を更新しつつ、全日分から『過去日のspike項目』を自動除去する"""
    today_dt = dt.date.today()
    today_iso = today_dt.isoformat()

    # 既存履歴ロード
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            print(f"⚠️ error loading {history_file}: {e}", file=sys.stderr)
            history = {}
    else:
        history = {}

    # 今日分を差し替え
    history[today_iso] = demand_spikes

    # 90日より前のキーを削除
    limit = (today_dt - dt.timedelta(days=90)).isoformat()
    history = {d: v for d, v in history.items() if d >= limit}

    # ★ 全キーに対して『過去日のspike』を除去（今日実行分で一括クリーン）
    cleaned = {}
    for up_date, items in history.items():
        new_items = []
        for it in items or []:
            sd = it.get("spike_date")
            try:
                if sd and dt.date.fromisoformat(sd) < today_dt:
                    continue  # 過去日のspikeは表示対象外として捨てる
            except Exception:
                pass  # spike_dateが壊れてても無視して通す
            new_items.append(it)
        cleaned[up_date] = new_items

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    print(f"📁 {history_file} cleaned & updated", file=sys.stderr)

# ===== 追加: 最終更新メタの書き出し =====
def write_last_updated():
    """Actions 実行完了時点のJST時刻などを last_updated.json に保存"""
    JST = dt.timezone(dt.timedelta(hours=9))
    now = dt.datetime.now(JST)
    payload = {
        "last_updated_iso": now.isoformat(timespec="seconds"),
        "last_updated_jst": now.strftime("%Y-%m-%d %H:%M:%S JST"),
        "source": "github-actions",
        "git_sha": os.environ.get("GITHUB_SHA", "")[:7],
        "note": "vacancy/price crawl finished",
    }
    try:
        with open(LAST_UPDATED_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"🕒 {LAST_UPDATED_FILE} written: {payload['last_updated_jst']}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ failed to write {LAST_UPDATED_FILE}: {e}", file=sys.stderr)

if __name__ == "__main__":
    print("📡 update_cache.py start", file=sys.stderr)
    cache_now = update_cache(start_date=dt.date.today(), months=9)
    update_history(cache_now)
    demand_spikes = detect_demand_spikes(cache_now, n_recent=3, pct=0.05)
    print(f"Demand spikes for today: {demand_spikes}", file=sys.stderr)
    save_demand_spike_history(demand_spikes)
    # 追加: すべての更新が完了した“最後”に書き出し
    write_last_updated()
    print("✨ all done", file=sys.stderr)
