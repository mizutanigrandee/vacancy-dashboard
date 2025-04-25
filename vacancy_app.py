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
    page_title="ミナミエリア 空室＆平均価格カレンダー",
    layout="wide"
)

st.title("ミナミエリア 空室＆平均価格カレンダー")

APP_ID = st.secrets["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"

# --- 祝日生成 ---
import jpholiday
def generate_holidays(months: int = 6) -> set:
    today = dt.date.today()
    future = today + relativedelta(months=months)
    holidays = set()
    d = today
    while d <= future:
        if jpholiday.is_holiday(d):
            holidays.add(d)
        d += dt.timedelta(days=1)
    return holidays
HOLIDAYS = generate_holidays()

# --- キャッシュ読込 ---
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

cache_data = load_cache()

def get_demand_icon(vacancy, price):
    level = 0
    if (vacancy <= 70 or price >= 50000):
        level = 5
    elif (vacancy <= 100 or price >= 40000):
        level = 4
    elif (vacancy <= 150 or price >= 35000):
        level = 3
    elif (vacancy <= 200 or price >= 30000):
        level = 2
    elif (vacancy <= 250 or price >= 25000):
        level = 1
    return f"🔥{level}" if level > 0 else ""

# --- スタイル追加（モバイル対応） ---
st.markdown("""
<style>
table {
    width: 100%;
    table-layout: fixed;
    word-wrap: break-word;
}
td {
    font-size: 14px;
}
th {
    font-size: 15px;
}
td div {
    line-height: 1.2;
}
@media screen and (min-width: 769px) {
    td div:nth-child(2), td div:nth-child(3) {
        font-size: 16px;
        font-weight: bold;
    }
}
@media screen and (max-width: 768px) {
    td {
        font-size: 11px;
    }
    th {
        font-size: 12px;
    }
    td div {
        line-height: 1.2;
    }
}
</style>
""", unsafe_allow_html=True)

# --- カレンダー描画 ---
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(month_date.year, month_date.month)
    today = dt.date.today()

    html = '<div class="calendar-wrapper">'
    html += '<table style="border-collapse:collapse;width:100%;text-align:center;">'
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
                record = cache_data.get(iso, {})
                vac = record.get("vacancy", 0)
                pre_vac = record.get("previous_vacancy")
                price = record.get("avg_price", 0)
                pre_price = record.get("previous_avg_price")

                # 差分表示
                vac_diff = vac - pre_vac if pre_vac is not None else None
                vac_diff_html = f'<span style="color:blue;">＋{vac_diff}</span>' if vac_diff and vac_diff > 0 else \
                                 f'<span style="color:red;">{vac_diff}</span>' if vac_diff and vac_diff < 0 else ""

                price_diff_html = ""
                if pre_price is not None:
                    if price > pre_price:
                        price_diff_html = '<span style="color:red;font-size:13px;"> ↑</span>'
                    elif price < pre_price:
                        price_diff_html = '<span style="color:blue;font-size:13px;"> ↓</span>'

                count_html = f'<div>{vac}件 {vac_diff_html}</div>'
                price_html = f'<div>￥{int(price):,}{price_diff_html}</div>'

                icon_html = ""
                if current >= today:
                    icon = get_demand_icon(vac, price)
                    icon_html = (
    f'<div style="position: absolute; top: 4px; right: 6px; font-size: 16px;">{icon}</div>'
)


                html += (
    f'<td style="border:1px solid #aaa;padding:8px;background:{bg};position:relative;">'

                    f'<div><strong>{day}</strong></div>'
                    f'{count_html}{price_html}{icon_html}'
                    '</td>'
                )
        html += '</tr>'
    html += '</tbody></table>'
    html += '</div>'
    return html

# --- UI制御 ---
today = dt.date.today()
if "refresh" not in st.session_state:
    st.session_state.refresh = False
if "month_offset" not in st.session_state:
    st.session_state.month_offset = 0

# 🔁 ナビゲーションボタン（中央に当月）
nav1, nav2, nav3 = st.columns([2, 2, 2])
with nav1:
    if st.button("◀ 前月", key="prev"):
        st.session_state.month_offset -= 1
with nav2:
    if st.button("📅 当月", key="today"):
        st.session_state.month_offset = 0
with nav3:
    if st.button("▶ 次月", key="next"):
        st.session_state.month_offset += 1

# 🔁 表示対象月の計算
base_month = today.replace(day=1) + relativedelta(months=st.session_state.month_offset)
month1 = base_month
month2 = base_month + relativedelta(months=1)


col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)
with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)

# --- 更新時刻と注釈 ---
jst = pytz.timezone('Asia/Tokyo')
now_jst = dt.datetime.now(jst)
st.caption(f"最終更新時刻：{now_jst.strftime('%Y-%m-%d %H:%M:%S')}")

st.markdown("""
**《注釈》**  
- 在庫数、平均価格は『なんば・心斎橋・天王寺・阿倍野・長居』エリアから抽出しています  
- 表示される「平均価格」は、楽天トラベル上位90施設の平均最低価格です  
- 炎マーク（需要シンボル）は以下のルールで表示されます：  
  - 🔥1：残室数 ≤250 または 平均価格 ≥25,000円  
  - 🔥2：残室数 ≤200 または 平均価格 ≥30,000円  
  - 🔥3：残室数 ≤150 または 平均価格 ≥35,000円  
  - 🔥4：残室数 ≤100 または 平均価格 ≥40,000円  
  - 🔥5：残室数 ≤70 または 平均価格 ≥50,000円
""")
