import os, json, calendar, requests, datetime as dt
from dateutil.relativedelta import relativedelta
from pathlib import Path

APP_ID     = os.environ["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"

# ---------------- 楽天API -----------------
def fetch_vacancy_and_price(date: dt.date) -> dict:
    if date < dt.date.today():
        return {"vacancy": 0, "avg_price": 0.0}
    prices, vacancy_total = [], 0
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    for page in range(1, 4):
        params = {
            "applicationId": APP_ID,
            "format": "json",
            "checkinDate": date.strftime("%Y-%m-%d"),
            "checkoutDate": (date+dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            "adultNum": 1,
            "largeClassCode": "japan",
            "middleClassCode": "osaka",
            "smallClassCode": "shi",
            "detailClassCode": "D",
            "page": page
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            if page == 1:
                vacancy_total = data.get("pagingInfo", {}).get("recordCount", 0)
            for hotel in data.get("hotels", []):
                try:
                    room_info = hotel["hotel"][1]["roomInfo"]
                    for plan in room_info:
                        total = plan["dailyCharge"].get("total")
                        if total:
                            prices.append(total)
                except Exception:
                    continue
        except Exception:
            continue
    avg = round(sum(prices)/len(prices), 0) if prices else 0.0
    return {"vacancy": vacancy_total, "avg_price": avg}

# ---------------- 更新バッチ -----------------
def update_batch(start_date: dt.date, months: int = 6):
    today = dt.date.today()
    keep_from = today - relativedelta(months=3)

    # ① 既存キャッシュ読込
    old = {}
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)

    # ② 半年分の“生データ”を raw に収集
    raw = {}           # iso -> {"vacancy":..,"avg_price":..}
    cal = calendar.Calendar(calendar.SUNDAY)
    for m in range(months):
        month = (start_date + relativedelta(months=m)).replace(day=1)
        for week in cal.monthdatescalendar(month.year, month.month):
            for day in week:
                if day.month == month.month and day >= today:
                    raw[day.isoformat()] = fetch_vacancy_and_price(day)

    # ③ 差分を後付けで作成
    result = {k: v for k, v in old.items() if dt.date.fromisoformat(k) >= keep_from}
    all_dates = sorted(raw.keys())              # 今回取得した未来日付だけ
    for iso in all_dates:
        day = dt.date.fromisoformat(iso)
        prev_iso = (day - dt.timedelta(days=1)).isoformat()
        prev_rec = result.get(prev_iso, {})     # ← ここは result から見る

        cur = raw[iso]
        record = {
            "vacancy":            cur["vacancy"],
            "avg_price":          cur["avg_price"],
            "previous_vacancy":   prev_rec.get("vacancy", 0),
            "previous_avg_price": prev_rec.get("avg_price", 0.0),
        }
        record["vacancy_diff"]   = record["vacancy"] - record["previous_vacancy"]
        record["avg_price_diff"] = record["avg_price"] - record["previous_avg_price"]
        result[iso] = record      # ← ここで初めて書き込むので次の日に正しく参照される

    # ④ 保存
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    baseline = dt.date.today().replace(day=1)
    update_batch(baseline)
