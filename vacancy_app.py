import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import calendar

# --- 設定 ---
APPLICATION_ID = "1080095124292517179"
AREA_PARAMS = {
    "largeClassCode": "japan",
    "middleClassCode": "osaka",
    "smallClassCode": "shi",
    "detailClassCode": "D",
}
ADULT_NUM = 2

# --- 関数：在庫と平均価格を取得 ---
def fetch_vacancy_and_price(date):
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    params = {
        "applicationId": APPLICATION_ID,
        "format": "json",
        "checkinDate": date.strftime("%Y-%m-%d"),
        "checkoutDate": (date + timedelta(days=1)).strftime("%Y-%m-%d"),
        "adultNum": ADULT_NUM,
        **AREA_PARAMS,
        "page": 1,
    }

    hotel_counts = 0
    total_min_charge = 0
    total_hotels = 0

    while True:
        res = requests.get(url, params=params)
        if res.status_code != 200:
            break

        data = res.json()
        hotels = data.get("hotels", [])
        if not hotels:
            break

        for hotel_data in hotels:
            try:
                info = hotel_data['hotel'][0]['hotelBasicInfo']
                charge = int(info.get("hotelMinCharge", 0))
                total_min_charge += charge
                total_hotels += 1
            except:
                continue

        if data['pagingInfo']['last'] <= params['page']:
            break
        else:
            params['page'] += 1

    avg_price = int(total_min_charge / total_hotels) if total_hotels > 0 else None
    return total_hotels, avg_price

# --- 現在の月を設定 ---
tz = pytz.timezone("Asia/Tokyo")
today = datetime.now(tz)
base_date = datetime(today.year, today.month, 1, tzinfo=tz)
st.session_state.setdefault("base_date", base_date)

# --- UI：前月／翌月ボタン ---
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("\u2190 前月"):
        st.session_state.base_date -= timedelta(days=1)
        st.session_state.base_date = st.session_state.base_date.replace(day=1)
with col2:
    if st.button("\u2192 翌月"):
        year = st.session_state.base_date.year + (st.session_state.base_date.month // 12)
        month = st.session_state.base_date.month % 12 + 1
        st.session_state.base_date = datetime(year, month, 1, tzinfo=tz)

# --- タイトルと更新時刻 ---
st.title("楽天トラベル 空室カレンダー（平均価格表示付き）")
st.markdown(f"**最終更新時刻：** {today.strftime('%Y-%m-%d %H:%M:%S')}")

# --- カレンダー表示 ---
def show_calendar(year, month):
    st.subheader(f"{year}年 {month}月")
    cal = calendar.Calendar(firstweekday=6)
    dates = [d for d in cal.itermonthdates(year, month) if d.month == month]
    week_rows = [dates[i:i+7] for i in range(0, len(dates), 7)]

    for week in week_rows:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                hotels, avg_price = fetch_vacancy_and_price(day)
                label = f"{day.day}"
                if hotels:
                    label += f"\n{hotels}件\n平均\u00a5{avg_price:,}"
                st.button(label, key=f"{day}")

# --- 表示処理 ---
base_date = st.session_state.base_date
year, month = base_date.year, base_date.month
show_calendar(year, month)

# 翌月のカレンダーも表示
next_month = (base_date + timedelta(days=32)).replace(day=1)
show_calendar(next_month.year, next_month.month)
