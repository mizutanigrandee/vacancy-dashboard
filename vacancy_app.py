import streamlit as st
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import time  # レート制限対策

import streamlit as st
# すでにこの行がある場合は不要です
APP_ID = st.secrets["RAKUTEN_APP_ID"]

# ↓ デバッグ用にシークレットの中身をサイドバーに表示
st.sidebar.write("DEBUG – APP_ID:", APP_ID)


# ① 直書き動作確認用
APP_ID = "YOUR_APPLICATION_ID_HERE"

# --- Streamlit ページ設定 ---
st.set_page_config(
    page_title="空室カレンダー（2か月表示）",
    layout="wide"
)
st.title("楽天トラベル 空室カレンダー（2か月表示）")

# --- API 呼び出し関数 ---
@st.cache_data(ttl=24*60*60)
def fetch_vacancy_count(date: dt.date) -> int:
    """
    指定日のチェックイン 1 泊分の空室ホテル数を取得して返す
    レート制限回避のため、呼び出し後に sleep を挟む
    """
    checkin = date.strftime("%Y-%m-%d")
    checkout = (date + dt.timedelta(days=1)).strftime("%Y-%m-%d")
    params = {
        "applicationId": APP_ID,
        "format": "json",
        "checkinDate": checkin,
        "checkoutDate": checkout,
        "adultNum": 1,
        "latitude": 34.667,
        "longitude": 135.502,
        "datumType": 1,
        "searchRadius": 3
    }
    url = (
        "https://app.rakuten.co.jp/services/api/"
        "Travel/VacantHotelSearch/20170426"
    )
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        count = data.get("pagingInfo", {}).get("recordCount", 0)
    except Exception:
        # エラー時はログ出力せず件数を 0 として扱う
        count = 0
    time.sleep(0.6)
    return count

# --- サイドバー：基準月選択 ---
today = dt.date.today()
baseline = st.sidebar.date_input(
    "基準月を選択",
    today.replace(day=1)
)
# 左：基準月、右：翌月
month1 = baseline.replace(day=1)
month2 = (month1 + relativedelta(months=1)).replace(day=1)

# --- カレンダー描画関数 ---
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(month_date.year, month_date.month)

    html = '<table style="border-collapse: collapse; width: 100%; text-align: center;">'
    headers = ["日","月","火","水","木","金","土"]
    html += '<thead><tr>' + ''.join(
        f'<th style="border:1px solid #aaa; padding:4px; background:#f0f0f0;">{d}</th>'
        for d in headers
    ) + '</tr></thead>'

    html += '<tbody>'
    for week in weeks:
        html += '<tr>'
        for day in week:
            if day == 0:
                html += '<td style="border:1px solid #aaa; padding:8px;"></td>'
            else:
                current = dt.date(month_date.year, month_date.month, day)
                count = fetch_vacancy_count(current)
                html += f'''<td style="border:1px solid #aaa; padding:8px;">
<div><strong>{day}</strong></div>
<div>{count} 件</div>
</td>'''
        html += '</tr>'
    html += '</tbody></table>'
    return html

# --- メイン：左右に2か月分を並べる ---
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)
with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)
