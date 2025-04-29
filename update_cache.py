import os
import json
import requests
import datetime
from dateutil.relativedelta import relativedelta

# --- 設定 ---
CACHE_PATH = "vacancy_price_cache.json"
APPLICATION_ID = os.environ["RAKUTEN_APP_ID"]
AREA_CODE = "D"  # なんば・心斎橋・天王寺・阿倍野・長居

# --- 楽天APIから最新データ取得 ---
def fetch_all_vacancy_and_price():
    base_url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    today = datetime.date.today()
    two_months_later = today + relativedelta(months=2)

    all_data = {}
    current_date = today
    while current_date <= two_months_later:
        checkin_date = current_date.strftime("%Y-%m-%d")

        params = {
            "applicationId": APPLICATION_ID,
            "format": "json",
            "datumType": 1,
            "checkinDate": checkin_date,
            "checkinDateAdjust": 0,
            "areaCode": AREA_CODE,
        }
        response = requests.get(base_url, params=params)
        result = response.json()

        hotels = result.get("hotels", [])
        vacancy_count = len(hotels)
        total_price = 0
        price_count = 0

        for hotel in hotels:
            try:
                price = hotel["hotel"][0]["hotelBasicInfo"]["hotelMinCharge"]
                total_price += price
                price_count += 1
            except (KeyError, IndexError):
                continue

        avg_price = total_price / price_count if price_count > 0 else 0.0

        all_data[checkin_date] = {
            "vacancy": vacancy_count,
            "avg_price": avg_price,
        }

        current_date += datetime.timedelta(days=1)

    return all_data

# --- 1. 既存キャッシュを読み込み ---
try:
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)
except FileNotFoundError:
    cache = {}

# --- 2. 最新データを取得 ---
latest_data = fetch_all_vacancy_and_price()

# --- 3. データ更新処理 ---
for date_str, new_info in latest_data.items():
    new_vacancy = new_info["vacancy"]
    new_price = new_info["avg_price"]

    old_entry = cache.get(date_str, {})
    prev_vacancy = old_entry.get("vacancy", 0)

    vacancy_diff = new_vacancy - prev_vacancy

    cache[date_str] = {
        "vacancy": new_vacancy,
        "avg_price": new_price,
        "previous_vacancy": prev_vacancy,
        "previous_avg_price": old_entry.get("avg_price", 0.0),
        "vacancy_diff": vacancy_diff
    }

# --- 4. 保存 ---
with open(CACHE_PATH, "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print(f"✅ 更新完了：{datetime.datetime.now().isoformat()}")
