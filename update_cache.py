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
                try:
                    hotel_parts = hotel.get("hotel", [])
                    if len(hotel_parts) >= 2:
                        room_info_list = hotel_parts[1].get("roomInfo", [])
                        for plan in room_info_list:
                            daily = plan.get("dailyCharge", {})
                            total = daily.get("total", None)
                            if total:
                                prices.append(total)
                except:
                    continue
        except:
            continue
    avg_price = round(sum(prices) / len(prices), 0) if prices else 0.0
    return {"vacancy": vacancy_total, "avg_price": avg_price}


def update_batch(start_date: dt.date, months: int = 6):
    today = dt.date.today()
    three_months_ago = today - relativedelta(months=3)

    # --- load original
    original_data = {}
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            original_data = json.load(f)

    # --- step1: get new raw data
    result = {
        k: v for k, v in original_data.items()
        if dt.date.fromisoformat(k) >= three_months_ago
    }

    new_raw = {}
    for m in range(months):
        month = (start_date + relativedelta(months=m)).replace(day=1)
        for week in calendar.Calendar(firstweekday=calendar.SUNDAY).monthdatescalendar(month.year, month.month):
            for day in week:
                if day.month == month.month and day >= today:
                    iso = day.isoformat()
                    new_raw[iso] = fetch_vacancy_and_price(day)

    # --- step2: inject into result with proper previous-day diff
    sorted_dates = sorted(new_raw.keys())
    for iso in sorted_dates:
        day = dt.date.fromisoformat(iso)
        prev_day = day - dt.timedelta(days=1)
        prev_iso = prev_day.isoformat()
        current = new_raw[iso]
        previous = result.get(prev_iso, {})

        record = {
            "vacancy": current["vacancy"],
            "avg_price": current["avg_price"],
            "previous_vacancy": previous.get("vacancy", 0),
            "previous_avg_price": previous.get("avg_price", 0.0),
            "vacancy_diff": current["vacancy"] - previous.get("vacancy", 0),
            "avg_price_diff": current["avg_price"] - previous.get("avg_price", 0.0)
        }
        result[iso] = record

    # --- write back
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    baseline = dt.date.today().replace(day=1)
    update_batch(baseline)
