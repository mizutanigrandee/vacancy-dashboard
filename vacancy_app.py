import requests
import json

def fetch_vacancy_count(checkin_date: str, adult_num: int = 2):
    params = {
        'applicationId': APPLICATION_ID,
        'format': 'json',
        'checkinDate': checkin_date,
        'checkoutDate': (datetime.datetime.strptime(checkin_date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        'adultNum': adult_num,
        'largeClassCode': 'japan',
        'middleClassCode': 'osaka',
        'smallClassCode': 'shi',
        'detailClassCode': 'D',
        'hits': 30,
        'page': 1
    }

    response = requests.get(VACANCY_API_URL, params=params)

    # ▼▼▼ JSONレスポンスをログ出力（読みやすく整形）▼▼▼
    print("▼▼▼ APIレスポンス ▼▼▼")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    # 必要な処理（例：ホテル件数、平均料金の抽出など）に続く
    data = response.json()
    hotels = data.get("hotels", [])
    prices = []

    for h in hotels:
        basic = h.get("hotel", {}).get("hotelBasicInfo", {})
        min_charge = basic.get("hotelMinCharge")
        if isinstance(min_charge, (int, float)):
            prices.append(min_charge)

    return {
        "vacant_count": len(hotels),
        "average_price": round(sum(prices) / len(prices)) if prices else None,
        "raw_data": data  # あとで使う可能性もあるので
    }
