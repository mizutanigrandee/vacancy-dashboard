import streamlit as st
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar

# --- ページ設定 ---
st.set_page_config(
    page_title="空室カレンダー（2か月表示）",
    layout="wide"
)

# --- シークレット情報 ---
APP_ID = st.secrets["RAKUTEN_APP_ID"]

# --- タイトル ---
st.title("楽天トラベル 空室カレンダー（2か月表示）")

# --- 祝日リスト（2025年4月〜5月） ---
HOLIDAYS = {
    dt.date(2025, 4, 29),  # 昭和の日
    dt.date(2025, 5, 3),   # 憲法記念日
    dt.date(2025, 5, 4),   # みどりの日
    dt.date(2025, 5, 5),   # こどもの日
}

# --- VacantHotelSearch API 呼び出し ---
@st.cache_data(ttl=24*60*60)
def fetch_vacancy_count(date: dt.date) -> int:
    if date < dt.date.today():
        return 0

    params = {
        "applicationId": APP_ID,
        "format": "json",
        "checkinDate": date.strftime("%Y-%m-%d"),
        "checkoutDate": (date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
        "adultNum": 1,
        "largeClassCode": "japan",
        "middleClassCode": "osaka",
        "smallClassCode": "D"  # ← detailClassCode: なんば・心斎橋・天王寺・阿倍野・長居
    }

    st.sidebar.write(f"▶ fetch_vacancy_count({date}): {params}")

    url = (
        "https://app.rakuten.co.jp/services/api/"
        "Travel/VacantHotelSearch/20170426"
    )
    try:
        r = requests.get(url, params=params, timeout=10)
        st.sidebar.write(f"  status: {r.status_code}")
        data = r.json()
        st.sidebar.write(f"  resp: {data}")
    except Exception as e:
        st.sidebar.write(f"  request error: {e}")
        return 0

    if r.status_code == 404:
        return 0
    if r.status_code != 200:
        st.sidebar.write(f"API ERROR status {r.status_code}")
        return 0

    return data.get("pagingInfo", {}).get("recordCount", 0)

# --- カレンダー描画関数 ---
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(month_date.year, month_date.month)
    today = dt.date.today()

    html = '<table style="border-collapse:collapse;width:100%;text-align:center;">'
    html += '<thead><tr>' + ''.join(
        f'<th style="border:1px solid #aaa;padding:4px;background:#f0f0f0;">{d}</th>'
        for d in ["日", "月", "火", "水", "木", "金", "土"]
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
