import streamlit as st
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import time

# --- ページ設定 ---
st.set_page_config(
    page_title="空室カレンダー（2か月表示）",
    layout="wide"
)

# --- 秘密情報の読み込み ---
APP_ID = st.secrets["RAKUTEN_APP_ID"]

# --- タイトル ---
st.title("楽天トラベル 空室カレンダー（2か月表示）")

# --- API 呼び出し関数 ---
@st.cache_data(ttl=24*60*60)
def fetch_vacancy_count(date: dt.date) -> int:
    """
    当日前はスキップし、未来日について VacantHotelSearch の recordCount を返す
    """
    # 過去日付はAPI呼び出しせず0件
    if date < dt.date.today():
        return 0

    params = {
        "applicationId": APP_ID,
        "format": "json",
        "checkinDate": date.strftime("%Y-%m-%d"),
        "checkoutDate": (date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
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
        count = 0
    finally:
        time.sleep(0.6)
    return count

# --- カレンダー描画関数 ---
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(month_date.year, month_date.month)

    html = '<table style="border-collapse:collapse;width:100%;text-align:center;">'
    # ヘッダー
    html += '<thead><tr>' + ''.join(
        f'<th style="border:1px solid #aaa;padding:4px;background:#f0f0f0;">{d}</th>'
        for d in ["日","月","火","水","木","金","土"]
    ) + '</tr></thead>'

    html += '<tbody>'
    for week in weeks:
        html += '<tr>'
        for day in week:
            if day == 0:
                html += '<td style="border:1px solid #aaa;padding:8px;"></td>'
            else:
                current = dt.date(month_date.year, month_date.month, day)
                count = fetch_vacancy_count(current)
                # 件数0は空白表示
                count_html = f'<div>{count} 件</div>' if count > 0 else ''
                html += (
                    f'<td style="border:1px solid #aaa;padding:8px;">'
                    f'<div><strong>{day}</strong></div>'
                    f'{count_html}'
                    '</td>'
                )
        html += '</tr>'
    html += '</tbody></table>'
    return html

# --- レイアウト: 2か月を並べる ---
today = dt.date.today()
baseline = st.sidebar.date_input("基準月を選択", today.replace(day=1))
month1 = baseline.replace(day=1)
month2 = (month1 + relativedelta(months=1)).replace(day=1)

col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)
with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)
