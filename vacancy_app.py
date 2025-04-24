import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
import calendar
import statistics

calendar.setfirstweekday(calendar.SUNDAY)

# --- 1. データ取得ロジック（空室数と平均価格の取得） ---
def fetch_vacancy_data(checkin_date: str) -> (int, float):
    url = f"https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    params = {
        "applicationId": "1080095124292517179",  # ← 本番用には自分のApp IDを使用してください
        "format": "json",
        "checkinDate": checkin_date,
        "checkoutDate": (datetime.datetime.strptime(checkin_date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "latitude": 34.653229,
        "longitude": 135.506882,
        "searchRadius": 3,
        "datumType": 1,
        "hotelThumbnailSize": 3,
        "responseType": "large"
    }

    try:
        res = requests.get(url, params=params)
        data = res.json()
        hotels = data.get("hotels", [])
        prices = []

        for hotel in hotels:
            try:
                total = hotel["hotel"][1]["roomInfo"][0]["dailyCharge"]["total"]
                prices.append(total)
            except (KeyError, IndexError, TypeError):
                continue

        vacancy_count = len(prices)
        avg_price = round(statistics.mean(prices), 0) if prices else None
        return vacancy_count, avg_price

    except Exception as e:
        print("Error:", e)
        return 0, None

# --- 2. カレンダー生成 ---
def generate_vacancy_calendar(month_offset=0):
    base_date = datetime.date.today().replace(day=1) + relativedelta(months=month_offset)
    last_day = calendar.monthrange(base_date.year, base_date.month)[1]

    records = []
    for day in range(1, last_day + 1):
        checkin = base_date.replace(day=day).strftime("%Y-%m-%d")
        vacancy_count, avg_price = fetch_vacancy_data(checkin)
        records.append({
            "日付": base_date.replace(day=day),
            "空室数": vacancy_count,
            "平均価格": avg_price
        })

    df = pd.DataFrame(records)
    return df

# --- 3. Streamlit UI ---
st.title("楽天トラベル 空室カレンダー（平均価格付き）")

selected_month = st.selectbox("表示月を選択", ("今月", "来月"))
offset = 0 if selected_month == "今月" else 1

with st.spinner("データ取得中..."):
    calendar_df = generate_vacancy_calendar(month_offset=offset)

calendar_df["日付"] = calendar_df["日付"].dt.strftime("%Y-%m-%d")
st.dataframe(calendar_df.style.format({"平均価格": "¥{:.0f}"}))
