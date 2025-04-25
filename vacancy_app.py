import streamlit as st
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd
import os
import json
import pytz
import jpholiday

# --- ページ設定 ---
st.set_page_config(
    page_title="ミナミエリア 空室＆平均価格カレンダー",
    layout="wide"
)

st.title("ミナミエリア 空室＆平均価格カレンダー")

APP_ID = st.secrets["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"
EVENT_FILE = "event_data.json"

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

# --- データ読み書き ---
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

cache_data = load_json(CACHE_FILE)
event_data = load_json(EVENT_FILE)

# --- ナビゲーション ---
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

# --- 需要シンボル ---
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
                record = cache_data.get(iso, {"vacancy": 0, "avg_price": 0.0})
                count_html = f'<div>{record["vacancy"]}件</div>'
                price_html = f'<div>￥{int(record["avg_price"]):,}</div>'

                icon = get_demand_icon(record["vacancy"], record["avg_price"]) if current >= today else ""
                icon_html = f'<div style="position:absolute;top:2px;right:4px;font-size:14px;">{icon}</div>'

                event_html = ""
                if iso in event_data:
                    for idx, ev in enumerate(event_data[iso]):
                        event_html += f'<div style="font-size: 12px; white-space: nowrap;">{ev["icon"]} {ev["name"]}</div>'
                    event_html = f'<div style="margin-top: 4px;">{event_html}</div>'

                html += (
                    f'<td style="border:1px solid #aaa;padding:8px;background:{bg};position:relative;">'
                    f'{icon_html}'
                    f'<div><strong>{day}</strong></div>'
                    f'{count_html}{price_html}{event_html}'
                    '</td>'
                )
        html += '</tr>'
    html += '</tbody></table>'
    html += '</div>'
    return html

# --- 表示 ---
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)
with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)

# --- イベント入力 ---
st.markdown("---")
st.subheader("📅 イベント情報の追加・更新")
input_date = st.date_input("日付を選択")
venue = st.selectbox("会場を選択", ["🔴 京セラドーム", "🔵 ヤンマースタジアム", "⚫ その他会場"])
event_name = st.text_input("イベント名を入力")
if st.button("追加"):
    iso_date = input_date.isoformat()
    entry = {"icon": venue.split()[0], "name": event_name}
    event_data.setdefault(iso_date, []).append(entry)
    save_json(EVENT_FILE, event_data)
    st.success(f"{iso_date} にイベントを追加しました")

# --- イベント削除・編集 ---
st.subheader("🗑 登録済みイベントの削除")
if st.checkbox("イベント削除モード"):
    deletable = [
        (d, i, f"{d} : {v[i]['icon']} {v[i]['name']}")
        for d, v in event_data.items() for i in range(len(v))
    ]
    if deletable:
        _, _, col_del = st.columns([1, 1, 2])
        with col_del:
            choice = st.selectbox("削除したいイベントを選択", deletable, format_func=lambda x: x[2])
            if st.button("削除"):
                d, i, _ = choice
                del event_data[d][i]
                if not event_data[d]:
                    del event_data[d]
                save_json(EVENT_FILE, event_data)
                st.success("イベントを削除しました")
    else:
        st.info("現在削除可能なイベントはありません。")

# --- 注釈 ---
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
- 🔴：京セラドーム  
- 🔵：ヤンマースタジアム  
- ⚫：その他会場
""")
