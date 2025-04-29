import os
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import json
import requests
from pathlib import Path

APP_ID     = os.environ["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"

# ───────────────────────────────────────────────
# 1) 指定日の在庫数・平均価格を楽天APIから取得
# ───────────────────────────────────────────────
def fetch_vacancy_and_price(date: dt.date) -> dict:
    # 過去日は 0 にして早期 return
    if date < dt.date.today():
        return {"vacancy": 0, "avg_price": 0.0}

    prices        = []
    vacancy_total = 0

    for page in range(1, 4):            # 最大 3ページ
        params = {
            "applicationId": APP_ID,
            "format": "json",
            "checkinDate":  date.strftime("%Y-%m-%d"),
            "checkoutDate": (date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            "adultNum": 1,
            "largeClassCode":  "japan",
            "middleClassCode": "osaka",
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
                    room_info_list = hotel_parts[1].get("roomInfo", [])
                    for plan in room_info_list:
                        daily  = plan.get("dailyCharge", {})
                        total  = daily.get("total")
                        if total:
                            prices.append(total)
        except Exception:
            continue

    avg_price = round(sum(prices) / len(prices), 0) if prices else 0.0
    return {"vacancy": vacancy_total, "avg_price": avg_price}

# ───────────────────────────────────────────────
# 2) キャッシュ更新バッチ
# ───────────────────────────────────────────────
def update_batch(start_date: dt.date, months: int = 6):
    today            = dt.date.today()
    three_months_ago = today - relativedelta(months=3)

    # 既存キャッシュ読み込み
    original_data = {}
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            original_data = json.load(f)

    # 3か月より古いデータは削除
    result = {
        k: v for k, v in original_data.items()
        if dt.date.fromisoformat(k) >= three_months_ago
    }

    # 未来半年分を更新しつつ差分を算出
    for m in range(months):
        month_first = (start_date + relativedelta(months=m)).replace(day=1)
        cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
        for week in cal.monthdatescalendar(month_first.year, month_first.month):
            for day in week:
                if day.month == month_first.month and day >= today:
                    iso_today = day.isoformat()
                    iso_prev  = (day - dt.timedelta(days=1)).isoformat()

                    prev_data = original_data.get(iso_prev, {})
                    new_data  = fetch_vacancy_and_price(day)

                    record = {
                        "vacancy":            new_data["vacancy"],
                        "avg_price":          new_data["avg_price"],
                        "previous_vacancy":   prev_data.get("vacancy", 0),
                        "previous_avg_price": prev_data.get("avg_price", 0.0),
                        "vacancy_diff":       new_data["vacancy"] - prev_data.get("vacancy", 0),
                        "avg_price_diff":     new_data["avg_price"] - prev_data.get("avg_price", 0.0)
                    }
                    result[iso_today] = record

    # キャッシュ保存
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

# ───────────────────────────────────────────────
if __name__ == "__main__":
    baseline = dt.date.today().replace(day=1)
    update_batch(baseline)
