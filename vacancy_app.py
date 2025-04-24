import streamlit as st
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd
import os
import json
import pytz

# --- ページ設定 ---
st.set_page_config(
    page_title="空室カレンダー（2か月表示）",
    layout="wide"
)

# --- シークレット情報 ---
APP_ID = st.secrets["RAKUTEN_APP_ID"]

# --- キャッシュ用ファイル ---
CACHE_FILE = "vacancy_price_cache.json"

# --- 祝日リスト（必要に応じて追加） ---
HOLIDAYS = {
    dt.date(2025, 4, 29),
    dt.date(2025, 5, 3),
    dt.date(2025, 5, 4),
    dt.date(2025, 5, 5),
}

# --- API呼び出し関数（空室数と平均価格） ---
def fetch_vacancy_and_price(date: dt.date) -> dict:
    if date < dt.date.today():
        return {"vacancy": 0, "avg_price": 0.0}

    params = {
        "applicationId": APP_ID,
        "format": "json",
        "checkinDate": date.strftime("%Y-%m-%d"),
        "checkoutDate": (date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
        "adultNum": 1,
        "largeClassCode":  "japan",
        "middleClassCode": "osaka",
        "smallClassCode":  "shi",
        "detailClassCode": "D",
    }

    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return {"vacancy": 0, "avg_price": 0.0}
        data = r.json()
        vacancy = data.get("pagingInfo", {}).get("recordCount", 0)
        prices = []
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
            except Exception as e:
                st.write("例外:", e)
        avg_price = round(sum(prices) / len(prices), 0) if prices else 0.0
        return {"vacancy": vacancy, "avg_price": avg_price}
    except:
        return {"vacancy": 0, "avg_price": 0.0}

# --- バッチ保存／読込 ---
def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# --- バッチ更新 ---
def update_batch(start_date: dt.date, months: int = 2):
    result = {}
    for m in range(months):
        month = (start_date + relativedelta(months=m)).replace(day=1)
        for week in calendar.Calendar(firstweekday=calendar.SUNDAY).monthdatescalendar(month.year, month.month):
            for day in week:
                if day.month == month.month and day >= dt.date.today():
                    result[day.isoformat()] = fetch_vacancy_and_price(day)
    save_cache(result)
    return result

# --- UI操作 ---
today = dt.date.today()
baseline = today.replace(day=1)

if "refresh" not in st.session_state:
    st.session_state.refresh = False

if st.button("🔄 最新情報を取得する"):
    st.session_state.refresh = True

if st.session_state.refresh:
    cache_data = update_batch(baseline)
    st.session_state.refresh = False
else:
    cache_data = load_cache()

# --- カレンダー描画 ---
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(month_date.year, month_date.month)
    today = dt.date.today()

    html = '<table style="border-collapse:collapse;width:100%;text-align:center;">'
    html += '<thead><tr>' + ''.join(
        f'<th style="border:1px solid #aaa;padding:4px;background:#f0f0f0;">{d}</th>'
        for d in ["日","月","火","水","木","金","土"]
    ) + '</tr></thead><tbody>'

    for week in weeks:
        html += '<tr>'
        for day in week:
            if day == 0:
                html += '<td style="border:1px solid #aaa;padding:8px;background:#fff;"></td>'
            else:
                current = dt.date(month_date.year, month_date.month, day)
                if current < today:
                    bg = '#ddd'
                elif current in HOLIDAYS or current.weekday() == 6:
                    bg = '#ffecec'
                elif current.weekday() == 5:
                    bg = '#e0f7ff'
                else:
                    bg = '#fff'

                iso = current.isoformat()
                record = cache_data.get(iso, {"vacancy": 0, "avg_price": 0.0})
                count_html = f'<div>{record["vacancy"]}件</div>'
                price_html = f'<div>￥{int(record["avg_price"]):,}</div>'

                html += (
                    f'<td style="border:1px solid #aaa;padding:8px;background:{bg};">'
                    f'<div><strong>{day}</strong></div>'
                    f'{count_html}{price_html}'
                    '</td>'
                )
        html += '</tr>'
    html += '</tbody></table>'
    return html

# --- 表示 ---
month1 = baseline
month2 = (baseline + relativedelta(months=1)).replace(day=1)
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)

with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)

# --- 更新時刻表示 ---
jst = pytz.timezone('Asia/Tokyo')
now_jst = dt.datetime.now(jst)
st.caption(f"最終更新時刻：{now_jst.strftime('%Y-%m-%d %H:%M:%S')}")
