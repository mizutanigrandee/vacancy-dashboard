import streamlit as st
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd
import os
import pytz
import json
import jpholiday

st.set_page_config(page_title="ミナミエリア 空室＆平均価格カレンダー", layout="wide")
st.title("ミナミエリア 空室＆平均価格カレンダー")

APP_ID = st.secrets["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"
EVENT_EXCEL = "event_data.xlsx"

def generate_holidays(months=6):
    today = dt.date.today()
    holidays = set()
    for i in range(months * 31):
        d = today + dt.timedelta(days=i)
        if jpholiday.is_holiday(d):
            holidays.add(d)
    return holidays

HOLIDAYS = generate_holidays()

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_event_data_from_excel(filepath=EVENT_EXCEL):
    if not os.path.exists(filepath):
        return {}
    df = pd.read_excel(filepath)
    df = df.dropna(subset=["date", "icon", "name"])
    event_dict = {}
    for _, row in df.iterrows():
        date = pd.to_datetime(row["date"]).date().isoformat()
        entry = {"icon": row["icon"], "name": row["name"]}
        event_dict.setdefault(date, []).append(entry)
    return event_dict

cache_data = load_json(CACHE_FILE)
event_data = load_event_data_from_excel()

# ナビゲーション
today = dt.date.today()
if "month_offset" not in st.session_state:
    st.session_state.month_offset = 0

nav1, nav2, nav3 = st.columns([2, 2, 2])
with nav1:
    if st.button("◀ 前月"):
        st.session_state.month_offset -= 1
with nav2:
    if st.button("🗓 当月"):
        st.session_state.month_offset = 0
with nav3:
    if st.button("▶ 次月"):
        st.session_state.month_offset += 1

base_month = today.replace(day=1) + relativedelta(months=st.session_state.month_offset)
month1 = base_month
month2 = base_month + relativedelta(months=1)

def get_demand_icon(vacancy, price):
    if vacancy <= 70 or price >= 50000: return "🔥5"
    if vacancy <= 100 or price >= 40000: return "🔥4"
    if vacancy <= 150 or price >= 35000: return "🔥3"
    if vacancy <= 200 or price >= 30000: return "🔥2"
    if vacancy <= 250 or price >= 25000: return "🔥1"
    return ""

def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(month_date.year, month_date.month)
    today = dt.date.today()

    html = '<div class="calendar-wrapper">'
    html += '<table style="border-collapse:collapse;width:100%;table-layout:fixed;text-align:center;">'
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
                iso = current.isoformat()
                prev_iso = (current - dt.timedelta(days=1)).isoformat()
                bg = '#fff'
                if current < today:
                    bg = '#ddd'
                elif current in HOLIDAYS or current.weekday() == 6:
                    bg = '#ffecec'
                elif current.weekday() == 5:
                    bg = '#e0f7ff'

                # データ取得
                record = cache_data.get(iso, {"vacancy": 0, "avg_price": 0.0})
                prev = cache_data.get(prev_iso, {"vacancy": 0, "avg_price": 0.0})

                # 前日比（在庫差）
                diff_v = record["vacancy"] - prev["vacancy"]
                diff_str = f'{diff_v:+d}' if prev["vacancy"] > 0 else ""
                diff_color = "#d00" if diff_v < 0 else "#06c"
                diff_html = f'<div style="font-size:10px;color:{diff_color};">{"▲" if diff_v < 0 else "▼"}{abs(diff_v)}</div>' if diff_str else ""

                # 前日比（価格変化）
                price_dir = ""
                if prev["avg_price"] > 0:
                    if record["avg_price"] > prev["avg_price"]:
                        price_dir = '<span style="color:#d00;font-size:10px;">↑</span>'
                    elif record["avg_price"] < prev["avg_price"]:
                        price_dir = '<span style="color:#06c;font-size:10px;">↓</span>'

                # データ描画
                count_html = f'<div style="font-size:18px;font-weight:bold;">{record["vacancy"]}件</div>'
                price_html = f'<div style="font-size:10px;">￥{int(record["avg_price"]):,}{price_dir}</div>'
                icon = get_demand_icon(record["vacancy"], record["avg_price"]) if current >= today else ""
                icon_html = f'<div style="position:absolute;top:2px;right:4px;font-size:14px;">{icon}</div>'

                # イベント
                event_html = ""
                if iso in event_data:
                    lines = [f'{ev["icon"]} {ev["name"]}' for ev in event_data[iso]]
                    joined = "<br>".join(lines)
                    event_html = f'<div style="font-size: 14px; margin-top: 4px;">{joined}</div>'

                html += (
                    f'<td style="border:1px solid #aaa;padding:8px;background:{bg};position:relative;vertical-align:top;">'
                    f'{icon_html}'
                    f'<div><strong>{day}</strong></div>'
                    f'{count_html}{diff_html}{price_html}{event_html}'
                    '</td>'
                )
        html += '</tr>'
    html += '</tbody></table></div>'
    return html


col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)
with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)

now_jst = dt.datetime.now(pytz.timezone('Asia/Tokyo'))
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
- 🔴：京セラドーム  
- 🔵：ヤンマースタジアム  
- ★：その他会場
""")
