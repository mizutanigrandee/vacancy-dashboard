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
    print(f"🔍 fetching {date}", file=sys.stderr)
    if date < dt.date.today():
        return {"vacancy": 0, "avg_price": 0.0}

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

def update_batch(start_date: dt.date, months: int = 6):
    today = dt.date.today()
    three_months_ago = today - relativedelta(months=3)

    # ① 既存キャッシュ読み込み
    existing = {}
    if Path(CACHE_FILE).exists():
        existing = json.loads(Path(CACHE_FILE).read_text(encoding="utf-8"))
    # 過去3ヶ月だけ残す
    existing = {
        k: v for k, v in existing.items()
        if dt.date.fromisoformat(k) >= three_months_ago
    }

    # ② 生データ収集
    raw = {}
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    for m in range(months):
        month_start = (start_date + relativedelta(months=m)).replace(day=1)
        for week in cal.monthdatescalendar(month_start.year, month_start.month):
            for d in week:
                if d.month == month_start.month and d >= today:
                    raw[d.isoformat()] = fetch_vacancy_and_price(d)

    # ③ 差分付与
    result = dict(existing)  # 過去3ヶ月分＋これまでの未来データ
    for iso in sorted(raw.keys()):
        d = dt.date.fromisoformat(iso)
        prev_iso = (d - dt.timedelta(days=1)).isoformat()
        prev = result.get(prev_iso, {"vacancy": 0, "avg_price": 0.0})

        cur = raw[iso]
        vac = cur["vacancy"]
        pri = cur["avg_price"]

        # --- ここで「初取得か？」を判定 ---
        is_new = iso not in existing

        # ベースレコード
        rec = {
            "vacancy":            vac,
            "avg_price":          pri,
            "previous_vacancy":   prev["vacancy"],
            "previous_avg_price": prev["avg_price"],
        }

        # diff は「初取得なら 0、そうでなければ計算結果」
        rec["vacancy_diff"]   = 0 if is_new else vac - prev["vacancy"]
        rec["avg_price_diff"] = 0 if is_new else pri - prev["avg_price"]

        result[iso] = rec

    # ④ 書き出し
    Path(CACHE_FILE).write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("✅ cache updated", file=sys.stderr)

if __name__ == "__main__":
    print("📡 Starting update_cache.py", file=sys.stderr)
    baseline = dt.date.today().replace(day=1)
    update_batch(baseline)
