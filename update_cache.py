import os
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import json
import requests
from pathlib import Path

APP_ID = os.environ["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"

def fetch_vacancy_and_price(date: dt.date) -> dict:
    if date < dt.date.today():
        return {"vacancy": 0, "avg_price": 0.0}

    prices = []
    vacancy_total = 0

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
        url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"

        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            if page == 1:
                vacancy_total = data.get("pagingInfo", {}).get("recordCount", 0)
            for hotel in data.get("hotels", []):
                hotel_parts = hotel.get("hotel", [])
                if len(hotel_parts) >= 2:
                    for plan in hotel_parts[1].get("roomInfo", []):
                        daily = plan.get("dailyCharge", {})
                        total = daily.get("total", None)
                        if total:
                            prices.append(total)
        except:
            continue

    avg_price = round(sum(prices) / len(prices), 0) if prices else 0.0
    return {"vacancy": vacancy_total, "avg_price": avg_price}

def update_batch(start_date: dt.date, months: int = 6):
    today = dt.date.today()
    three_months_ago = today - relativedelta(months=3)

    # --- ① 既存データを読み込み（過去3ヶ月保持）
    result = {}
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            result = json.load(f)
        result = {
            k: v for k, v in result.items()
            if dt.date.fromisoformat(k) >= three_months_ago
        }

    # --- ② 未来半年分の vacancy, avg_price を収集（差分なし）
    future_data = {}
    for m in range(months):
        month = (start_date + relativedelta(months=m)).replace(day=1)
        for week in calendar.Calendar(firstweekday=calendar.SUNDAY).monthdatescalendar(month.year, month.month):
            for day in week:
                if day.month == month.month and day >= today:
                    iso = day.isoformat()
                    future_data[iso] = fetch_vacancy_and_price(day)

    # --- ③ すべてのデータを時系列で並び替え
    all_dates = sorted(set(result.keys()) | set(future_data.keys()))
    full_data = {}

    for i, iso in enumerate(all_dates):
        entry = result.get(iso) or future_data.get(iso)
        if not entry:
            continue

        record = {
            "vacancy": entry["vacancy"],
            "avg_price": entry["avg_price"]
        }

        if i > 0:
            prev_iso = all_dates[i - 1]
            prev_entry = result.get(prev_iso) or future_data.get(prev_iso) or {}
            record["previous_vacancy"] = prev_entry.get("vacancy", 0)
            record["previous_avg_price"] = prev_entry.get("avg_price", 0)
        else:
            record["previous_vacancy"] = 0
            record["previous_avg_price"] = 0

        full_data[iso] = record

    # --- ④ 保存
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    baseline = dt.date.today().replace(day=1)
    update_batch(baseline)
