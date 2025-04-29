import os, datetime as dt, calendar, json, requests
from pathlib import Path
from dateutil.relativedelta import relativedelta

APP_ID     = os.environ["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"

def fetch_vacancy_and_price(day: dt.date) -> dict:
    if day < dt.date.today():
        return {"vacancy": 0, "avg_price": 0.0}

    prices, vacancy_total = [], 0
    for page in range(1, 4):
        params = {
            "applicationId":  APP_ID,
            "format":         "json",
            "checkinDate":    day.strftime("%Y-%m-%d"),
            "checkoutDate":   (day+dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            "adultNum":       1,
            "largeClassCode": "japan",
            "middleClassCode":"osaka",
            "smallClassCode": "shi",      # ← 必須だった
            "detailClassCode":"D",
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
                parts = hotel.get("hotel", [])
                if len(parts) >= 2:
                    for plan in parts[1].get("roomInfo", []):
                        total = plan.get("dailyCharge", {}).get("total")
                        if total:
                            prices.append(total)
        except Exception:
            continue
    avg = round(sum(prices)/len(prices),0) if prices else 0.0
    return {"vacancy": vacancy_total, "avg_price": avg}

def update_batch(start: dt.date, months=6):
    today = dt.date.today()
    three_months_ago = today - relativedelta(months=3)

    prev = {}
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE,"r",encoding="utf-8") as f:
            prev = json.load(f)

    # 古いレコードを間引き
    result = {k:v for k,v in prev.items()
              if dt.date.fromisoformat(k) >= three_months_ago}

    cal = calendar.Calendar()
    for m in range(months):
        first = (start+relativedelta(months=m)).replace(day=1)
        for week in cal.monthdatescalendar(first.year, first.month):
            for day in week:
                if day.month!=first.month or day<today: continue
                iso, iso_yest = day.isoformat(), (day-dt.timedelta(days=1)).isoformat()
                prev_day  = prev.get(iso_yest, {})
                new       = fetch_vacancy_and_price(day)

                # 保護：取得失敗(0) なら上書きしない
                if new["vacancy"]==0 and prev_day:
                    result[iso] = prev.get(iso, prev_day)
                    continue

                result[iso] = {
                    "vacancy":            new["vacancy"],
                    "avg_price":          new["avg_price"],
                    "previous_vacancy":   prev_day.get("vacancy",0),
                    "previous_avg_price": prev_day.get("avg_price",0.0),
                    "vacancy_diff":       new["vacancy"]-prev_day.get("vacancy",0),
                    "avg_price_diff":     new["avg_price"]-prev_day.get("avg_price",0.0)
                }

    with open(CACHE_FILE,"w",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2)

if __name__ == "__main__":
    update_batch(dt.date.today().replace(day=1))
