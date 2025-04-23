import streamlit as st
import datetime as dt
from dateutil.relativedelta import relativedelta
import requests
import calendar

# ページ設定
st.set_page_config(page_title="楽天トラベル 空室カレンダー（2か月表示）", layout="wide")
calendar.setfirstweekday(calendar.SUNDAY)

# シークレット情報
APP_ID = st.secrets["RAKUTEN_APP_ID"]

# タイトル
st.title("楽天トラベル 空室カレンダー（2か月表示）")

# --- セッションに基準月を保持 ---
if "baseline_month" not in st.session_state:
    st.session_state["baseline_month"] = dt.date.today().replace(day=1)

# --- 月移動ボタン ---
left_col, center_col, right_col = st.columns([1, 6, 1])
with left_col:
    if st.button("← 前月"):
        st.session_state["baseline_month"] -= relativedelta(months=1)
with right_col:
    if st.button("→ 翌月"):
        st.session_state["baseline_month"] += relativedelta(months=1)

# --- 祝日（例: 2025年4〜5月） ---
HOLIDAYS = {
    dt.date(2025, 4, 29), dt.date(2025, 5, 3),
    dt.date(2025, 5, 4), dt.date(2025, 5, 5),
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
        "smallClassCode": "shi",
        "detailClassCode": "D"
    }
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json().get("pagingInfo", {}).get("recordCount", 0)
    except:
        pass
    return 0

# --- カレンダー描画関数 ---
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar()
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
                bg = "#fff"
                if current < today:
                    bg = "#ddd"
                elif current in HOLIDAYS or current.weekday() == 6:
                    bg = "#ffecec"
                elif current.weekday() == 5:
                    bg = "#e0f7ff"
                count = fetch_vacancy_count(current)
                count_html = f"<div>{count}件</div>" if count > 0 else ""
                html += (
                    f'<td style="border:1px solid #aaa;padding:8px;background:{bg};">'
                    f'<div><strong>{day}</strong></div>{count_html}</td>'
                )
        html += '</tr>'
    html += '</tbody></table>'
    return html

# --- メイン表示（2か月） ---
month1 = st.session_state["baseline_month"]
month2 = (month1 + relativedelta(months=1)).replace(day=1)

col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)
with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)
