import streamlit as st
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pytz

# --- ページ設定 ---
st.set_page_config(
    page_title="空室カレンダー（平均価格表示）",
    layout="wide"
)

# --- シークレット情報取得 ---
APP_ID = st.secrets["RAKUTEN_APP_ID"]

# --- 祝日情報取得 ---
import jpholiday

# --- 最終更新時刻 ---
JST = pytz.timezone('Asia/Tokyo')
st.markdown(f"#### 最終更新時刻：{dt.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')}")

# --- タイトル ---
st.title("楽天トラベル 空室カレンダー（平均価格表示付き）")

# --- VacantHotelSearch APIから空室数と平均価格を取得 ---
def fetch_vacancy_and_average_price(checkin_date: dt.date):
    page = 1
    total_price = 0
    total_count = 0
    max_pages = 5  # ページ制限（1ページ30件）

    while page <= max_pages:
        params = {
            "applicationId": APP_ID,
            "format": "json",
            "checkinDate": checkin_date.strftime("%Y-%m-%d"),
            "checkoutDate": (checkin_date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            "adultNum": 2,
            "largeClassCode": "japan",
            "middleClassCode": "osaka",
            "smallClassCode": "shi",
            "detailClassCode": "D",
            "page": page
        }

        url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
        res = requests.get(url, params=params)
        if res.status_code != 200:
            break
        data = res.json()

        hotels = data.get("hotels", [])
        for hotel in hotels:
            try:
                price = hotel["hotelBasicInfo"]["hotelMinCharge"]
                total_price += price
                total_count += 1
            except Exception:
                continue

        if len(hotels) < 30:
            break
        page += 1

    avg_price = total_price // total_count if total_count > 0 else 0
    return total_count, avg_price

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
                elif jpholiday.is_holiday(current) or current.weekday() == 6:
                    bg = '#ffecec'
                elif current.weekday() == 5:
                    bg = '#e0f7ff'
                else:
                    bg = '#fff'

                count, avg_price = fetch_vacancy_and_average_price(current)
                count_html = f'<div>{count} 件</div>' if count > 0 else ''
                price_html = f'<div>平均 ¥{avg_price:,}</div>' if avg_price > 0 else ''
                html += (
                    f'<td style="border:1px solid #aaa;padding:8px;background:{bg};">'
                    f'<div><strong>{day}</strong></div>'
                    f'{count_html}{price_html}'
                    '</td>'
                )
        html += '</tr>'
    html += '</tbody></table>'
    return html

# --- 月移動用インターフェース ---
today = dt.date.today()
if 'baseline' not in st.session_state:
    st.session_state.baseline = today.replace(day=1)

col_btn1, col_btn2 = st.columns([1, 1])
with col_btn1:
    if st.button("← 前月"):
        st.session_state.baseline -= relativedelta(months=1)
with col_btn2:
    if st.button("→ 翌月"):
        st.session_state.baseline += relativedelta(months=1)

month1 = st.session_state.baseline
month2 = (month1 + relativedelta(months=1)).replace(day=1)

col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)
with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)
