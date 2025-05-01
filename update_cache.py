import os
import sys
import json
import calendar
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
from pathlib import Path

APP_ID     = os.environ.get("RAKUTEN_APP_ID", "")
CACHE_FILE = "vacancy_price_cache.json"

def fetch_vacancy_and_price(date: dt.date) -> dict:
    """楽天APIから指定日のvacancyとavg_priceを取得"""
    print(f"🔍 fetching {date}", file=sys.stderr)
    prices = []
    vacancy_total = 0
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    for page in range(1, 4):
        params = {
            "applicationId": APP_ID,
            "format": "json",
            "checkinDate": date.strftime("%Y-%m-%d"),
            "checkoutDate": (date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            "adultNum": 1,
            "largeClassCode": "japan",
            "middleClassCode": "osaka",
            "smallClassCode": "shi",
            "detailClassCode": "D",
            "page": page
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

def update_cache(start_date: dt.date, months: int = 6):
    today = dt.date.today()
    three_months_ago = today - relativedelta(months=3)

    # --- 既存キャッシュ読み込み ---
    cache = {}
    if Path(CACHE_FILE).exists():
        cache = json.loads(Path(CACHE_FILE).read_text(encoding="utf-8"))

    # 古い(3ヶ月前以前)のキーは削除
    cache = {
        k: v for k, v in cache.items()
        if dt.date.fromisoformat(k) >= three_months_ago
    }

    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    # --- 各日付の更新処理 ---
    for m in range(months):
        month_start = (start_date + relativedelta(months=m)).replace(day=1)
        for week in cal.monthdatescalendar(month_start.year, month_start.month):
            for day in week:
                if day.month != month_start.month or day < today:
                    continue

                iso = day.isoformat()
                # APIから取得
                new = fetch_vacancy_and_price(day)
                new_vac = new["vacancy"]
                new_pri = new["avg_price"]

                # キャッシュから前回実行値を取得
                prev = cache.get(iso, {})
                last_vac = prev.get("last_vacancy", prev.get("vacancy", 0))
                last_pri = prev.get("last_avg_price", prev.get("avg_price", 0.0))

                # 差分計算
                vac_diff = new_vac - last_vac
                pri_diff = new_pri - last_pri

                # 新レコード作成
                record = {
                    "vacancy": new_vac,
                    "avg_price": new_pri,
                    "last_vacancy": last_vac,
                    "last_avg_price": last_pri,
                    "vacancy_diff": vac_diff,
                    "avg_price_diff": pri_diff,
                }
                cache[iso] = record

    # --- 保存 ---
    Path(CACHE_FILE).write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("✅ cache updated", file=sys.stderr)

if __name__ == "__main__":
    print("📡 Starting update_cache.py", file=sys.stderr)
    today = dt.date.today()
    update_cache(today)
